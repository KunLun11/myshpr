"""Storage backends for project files (ADR-09).

Local disk is the default in development. S3-compatible storage is used in
production; ``aioboto3`` is imported lazily so the dev install stays light.
Objects are never public: downloads always go through an authorised API
endpoint, or a short-lived presigned URL for S3.
"""

import asyncio
import shutil
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from app.core.config import Settings, get_settings


class StorageError(RuntimeError):
    pass


class StorageBackend(ABC):
    @abstractmethod
    async def put(self, key: str, source: Path) -> None: ...

    @abstractmethod
    def open(self, key: str) -> AsyncIterator[bytes]: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def presigned_url(self, key: str, *, expires_in: int = 300) -> str | None: ...

    @abstractmethod
    def locate(self, key: str) -> Path | None:
        """Return a local path when the backend stores files on disk."""


class LocalStorage(StorageBackend):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if path != self.root and self.root not in path.parents:
            raise StorageError("Некорректный ключ хранилища")
        return path

    async def put(self, key: str, source: Path) -> None:
        destination = self._path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        def _move() -> None:
            # Same filesystem: os.replace is atomic; fall back to copy.
            try:
                source.replace(destination)
            except OSError:
                shutil.copyfile(source, destination)
                source.unlink(missing_ok=True)

        await asyncio.to_thread(_move)

    def open(self, key: str) -> AsyncIterator[bytes]:
        path = self._path(key)

        async def iterator() -> AsyncIterator[bytes]:
            handle = await asyncio.to_thread(path.open, "rb")
            try:
                while True:
                    chunk = await asyncio.to_thread(handle.read, 64 * 1024)
                    if not chunk:
                        break
                    yield chunk
            finally:
                await asyncio.to_thread(handle.close)

        return iterator()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        await asyncio.to_thread(path.unlink, True)

    async def presigned_url(self, key: str, *, expires_in: int = 300) -> str | None:
        return None

    def locate(self, key: str) -> Path | None:
        path = self._path(key)
        return path if path.exists() else None


class S3Storage(StorageBackend):
    """S3-compatible backend (MinIO, Selectel, AWS)."""

    def __init__(self, settings: Settings) -> None:
        if not (settings.S3_BUCKET and settings.S3_ENDPOINT):
            raise StorageError("S3 storage requires S3_ENDPOINT and S3_BUCKET")
        self.bucket = settings.S3_BUCKET
        self.endpoint = settings.S3_ENDPOINT
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.region = settings.S3_REGION or "us-east-1"

    def _client_kwargs(self) -> dict:
        return {
            "service_name": "s3",
            "endpoint_url": self.endpoint,
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "region_name": self.region,
        }

    def _session(self):
        try:
            import aioboto3  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise StorageError(
                "S3 storage requires aioboto3. Install the backend with `s3` extras."
            ) from exc
        return aioboto3.Session()

    async def put(self, key: str, source: Path) -> None:
        async with self._session().client(**self._client_kwargs()) as client:
            await client.upload_file(str(source), self.bucket, key)
        await asyncio.to_thread(source.unlink, True)

    def open(self, key: str) -> AsyncIterator[bytes]:
        async def iterator() -> AsyncIterator[bytes]:
            async with self._session().client(**self._client_kwargs()) as client:
                response = await client.get_object(Bucket=self.bucket, Key=key)
                body = response["Body"]
                try:
                    while True:
                        chunk = await body.read(64 * 1024)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    await body.close()

        return iterator()

    async def delete(self, key: str) -> None:
        async with self._session().client(**self._client_kwargs()) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

    async def presigned_url(self, key: str, *, expires_in: int = 300) -> str | None:
        async with self._session().client(**self._client_kwargs()) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    def locate(self, key: str) -> Path | None:
        return None


@lru_cache
def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage(settings)
    return LocalStorage(settings.MEDIA_ROOT)

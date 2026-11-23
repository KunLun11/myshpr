"""Project file upload, listing, download and soft delete (ADR-09)."""

import asyncio
import hashlib
import os
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, ConflictError, NotFoundError, ValidationError
from app.models import ProjectFile, User
from app.models.enums import FileKind, FileStatus, UserRole
from app.repositories import files as files_repo
from app.repositories import projects as projects_repo
from app.schemas.file import ProjectFileOut
from app.services import project_access
from app.services.storage import get_storage

CHUNK_SIZE = 1024 * 1024
MAX_NAME_LENGTH = 255

MIME_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".zip": "application/zip",
}


def _clean_name(filename: str | None) -> str:
    name = Path(filename or "file").name
    name = "".join(ch for ch in name if ch.isprintable() and ch not in "\x00")
    return name.strip()[:MAX_NAME_LENGTH] or "file"


def _signature_ok(path: Path, extension: str) -> bool:
    try:
        with path.open("rb") as handle:
            head = handle.read(8)
    except OSError:  # pragma: no cover - disk failure
        return False

    if extension == ".pdf":
        return head.startswith(b"%PDF-")
    if extension == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return head.startswith(b"\xff\xd8\xff")
    if extension in {".zip", ".docx", ".pptx"}:
        if not head.startswith(b"PK\x03\x04"):
            return False
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile:
            return False
        if extension == ".docx":
            return "word/document.xml" in names
        if extension == ".pptx":
            return any(name.startswith("ppt/slides/") for name in names)
        return True
    return False


async def _stream_to_temp(upload: UploadFile, *, max_bytes: int) -> tuple[Path, int, str]:
    settings = get_settings()
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(dir=settings.MEDIA_ROOT, prefix=".upload-")
    path = Path(raw_path)
    digest = hashlib.sha256()
    size = 0

    try:
        with os.fdopen(descriptor, "wb") as handle:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise AppError(
                        "FILE_TOO_LARGE",
                        f"Файл больше {max_bytes // (1024 * 1024)} МБ.",
                        status_code=413,
                    )
                digest.update(chunk)
                handle.write(chunk)
    except Exception:
        await asyncio.to_thread(path.unlink, True)
        raise

    if size == 0:
        await asyncio.to_thread(path.unlink, True)
        raise ValidationError("Файл пустой", "EMPTY_FILE")
    return path, size, digest.hexdigest()


def _validate_upload_meta(upload: UploadFile, original_name: str) -> tuple[str, str]:
    settings = get_settings()
    extension = Path(original_name).suffix.lower()
    if extension not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            "Этот тип файла не поддерживается. Разрешены PDF, DOCX, PPTX, PNG, JPEG и ZIP.",
            "FILE_TYPE_NOT_ALLOWED",
        )

    declared = (upload.content_type or "").lower()
    if (
        declared
        and declared != "application/octet-stream"
        and declared not in settings.ALLOWED_UPLOAD_MIME
    ):
        raise ValidationError("Недопустимый MIME-тип файла.", "FILE_MIME_NOT_ALLOWED")

    return extension, MIME_BY_EXTENSION[extension]


def serialize_file(file: ProjectFile) -> ProjectFileOut:
    return ProjectFileOut(
        id=file.id,
        project_id=file.project_id,
        kind=file.kind,
        original_name=file.original_name,
        mime_type=file.mime_type,
        size_bytes=file.size_bytes,
        status=file.status,
        created_at=file.created_at,
        download_url=f"/files/{file.id}/download",
    )


async def list_student_files(session: AsyncSession, student: User) -> list[ProjectFileOut]:
    context = await project_access.load_student_project(session, student)
    rows = await files_repo.list_for_project(session, context.project.id)
    return [serialize_file(row) for row in rows]


async def list_staff_files(
    session: AsyncSession, user: User, project_id: uuid.UUID
) -> list[ProjectFileOut]:
    await project_access.load_staff_project(session, user, project_id)
    rows = await files_repo.list_for_project(session, project_id)
    return [serialize_file(row) for row in rows]


async def upload_file(
    session: AsyncSession,
    student: User,
    upload: UploadFile,
    *,
    kind: FileKind = FileKind.FINAL_WORK,
) -> ProjectFileOut:
    settings = get_settings()
    context = await project_access.load_student_project(session, student)
    project = context.project

    active_count = await files_repo.count_active(session, project.id)
    if active_count >= settings.MAX_FILES_PER_PROJECT:
        raise ValidationError(
            f"К проекту можно приложить не больше {settings.MAX_FILES_PER_PROJECT} файлов.",
            "FILE_LIMIT_REACHED",
        )

    original_name = _clean_name(upload.filename)
    extension, mime_type = _validate_upload_meta(upload, original_name)

    tmp_path, size, checksum = await _stream_to_temp(upload, max_bytes=settings.MAX_UPLOAD_BYTES)

    try:
        if not _signature_ok(tmp_path, extension):
            raise ValidationError(
                "Содержимое файла не совпадает с расширением.", "FILE_SIGNATURE_INVALID"
            )

        existing = await files_repo.find_by_checksum(
            session, project_id=project.id, checksum=checksum
        )
        if existing is not None and existing.status is not FileStatus.DELETED:
            raise ConflictError("Файл с таким содержимым уже загружен в проект.", "DUPLICATE_FILE")

        storage_key = f"projects/{project.id}/{uuid.uuid4().hex}{extension}"
        storage = get_storage()
        await storage.put(storage_key, tmp_path)

        if existing is not None:
            old_key = existing.storage_key
            file = await files_repo.revive(
                session,
                existing,
                uploaded_by=student.id,
                kind=kind,
                original_name=original_name,
                storage_key=storage_key,
                mime_type=mime_type,
                size_bytes=size,
            )
            await storage.delete(old_key)
        else:
            try:
                file = await files_repo.create(
                    session,
                    project_id=project.id,
                    uploaded_by=student.id,
                    kind=kind,
                    original_name=original_name,
                    storage_key=storage_key,
                    mime_type=mime_type,
                    size_bytes=size,
                    checksum_sha256=checksum,
                )
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError(
                    "Файл с таким содержимым уже загружен в проект.", "DUPLICATE_FILE"
                ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    project.last_activity_at = datetime.now(UTC)
    await projects_repo.add_event(
        session,
        project_id=project.id,
        event_type="file_uploaded",
        actor_id=student.id,
        payload={"file_id": str(file.id), "name": original_name},
    )
    await session.commit()
    return serialize_file(file)


async def get_download_target(
    session: AsyncSession, user: User, file_id: uuid.UUID
) -> tuple[ProjectFile, Path | None, str | None]:
    """Return the file, a local path (if any) and a presigned URL (if any)."""
    file = await files_repo.get(session, file_id)
    if file is None or file.status is not FileStatus.AVAILABLE or file.deleted_at is not None:
        raise NotFoundError("Файл не найден", "FILE_NOT_FOUND")

    project = await projects_repo.get_by_id(session, file.project_id)
    if project is None:  # pragma: no cover - FK guarantees it
        raise NotFoundError("Проект не найден", "PROJECT_NOT_FOUND")

    if user.role is UserRole.STUDENT:
        project_access.ensure_student_owns(project, user)
    else:
        await project_access.load_staff_project(session, user, project.id)

    storage = get_storage()
    return (
        file,
        storage.locate(file.storage_key),
        await storage.presigned_url(file.storage_key),
    )


async def open_file_stream(file: ProjectFile):
    return get_storage().open(file.storage_key)


def content_disposition(filename: str) -> str:
    fallback = filename.encode("ascii", "ignore").decode("ascii") or "file"
    fallback = fallback.replace('"', "_")
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


async def delete_file(session: AsyncSession, student: User, file_id: uuid.UUID) -> None:
    context = await project_access.load_student_project(session, student)
    file = await files_repo.get(session, file_id)
    if (
        file is None
        or file.project_id != context.project.id
        or file.status is FileStatus.DELETED
        or file.deleted_at is not None
    ):
        raise NotFoundError("Файл не найден", "FILE_NOT_FOUND")

    await files_repo.mark_deleted(session, file.id)
    await projects_repo.add_event(
        session,
        project_id=context.project.id,
        event_type="file_deleted",
        actor_id=student.id,
        payload={"file_id": str(file.id)},
    )
    await session.commit()

"""Project file queries."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectFile
from app.models.enums import FileStatus


async def list_for_project(
    session: AsyncSession, project_id: uuid.UUID, *, include_deleted: bool = False
) -> list[ProjectFile]:
    stmt = select(ProjectFile).where(ProjectFile.project_id == project_id)
    if not include_deleted:
        stmt = stmt.where(
            ProjectFile.status != FileStatus.DELETED, ProjectFile.deleted_at.is_(None)
        )
    stmt = stmt.order_by(ProjectFile.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_active(session: AsyncSession, project_id: uuid.UUID) -> int:
    result = await session.scalar(
        select(func.count(ProjectFile.id)).where(
            ProjectFile.project_id == project_id,
            ProjectFile.status != FileStatus.DELETED,
            ProjectFile.deleted_at.is_(None),
        )
    )
    return int(result or 0)


async def get(session: AsyncSession, file_id: uuid.UUID) -> ProjectFile | None:
    return await session.get(ProjectFile, file_id)


async def find_by_checksum(
    session: AsyncSession, *, project_id: uuid.UUID, checksum: str
) -> ProjectFile | None:
    result = await session.execute(
        select(ProjectFile).where(
            ProjectFile.project_id == project_id,
            ProjectFile.checksum_sha256 == checksum,
        )
    )
    return result.scalars().first()


async def create(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    kind,
    original_name: str,
    storage_key: str,
    mime_type: str,
    size_bytes: int,
    checksum_sha256: str,
) -> ProjectFile:
    file = ProjectFile(
        project_id=project_id,
        uploaded_by=uploaded_by,
        kind=kind,
        original_name=original_name,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
        checksum_sha256=checksum_sha256,
        status=FileStatus.AVAILABLE,
        scanned_at=datetime.now(UTC),
    )
    session.add(file)
    await session.flush()
    return file


async def revive(
    session: AsyncSession,
    file: ProjectFile,
    *,
    uploaded_by: uuid.UUID,
    kind,
    original_name: str,
    storage_key: str,
    mime_type: str,
    size_bytes: int,
) -> ProjectFile:
    """Reuse a soft-deleted row when the same bytes are uploaded again."""
    file.uploaded_by = uploaded_by
    file.kind = kind
    file.original_name = original_name
    file.storage_key = storage_key
    file.mime_type = mime_type
    file.size_bytes = size_bytes
    file.status = FileStatus.AVAILABLE
    file.scanned_at = datetime.now(UTC)
    file.deleted_at = None
    await session.flush()
    return file


async def mark_deleted(session: AsyncSession, file_id: uuid.UUID) -> bool:
    result = await session.execute(
        update(ProjectFile)
        .where(ProjectFile.id == file_id, ProjectFile.status != FileStatus.DELETED)
        .values(status=FileStatus.DELETED, deleted_at=datetime.now(UTC))
    )
    return bool(result.rowcount)

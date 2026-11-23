"""Teacher comment queries."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectComment, User
from app.models.enums import CommentVisibility


async def list_for_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    *,
    visibility: CommentVisibility | None = None,
) -> list[tuple[ProjectComment, str | None]]:
    stmt = (
        select(ProjectComment, User.full_name)
        .outerjoin(User, User.id == ProjectComment.author_id)
        .where(
            ProjectComment.project_id == project_id,
            ProjectComment.deleted_at.is_(None),
        )
        .order_by(ProjectComment.created_at.asc())
    )
    if visibility is not None:
        stmt = stmt.where(ProjectComment.visibility == visibility)
    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def get(session: AsyncSession, comment_id: uuid.UUID) -> ProjectComment | None:
    return await session.get(ProjectComment, comment_id)


async def get_with_author(
    session: AsyncSession, comment_id: uuid.UUID
) -> tuple[ProjectComment, str | None] | None:
    result = await session.execute(
        select(ProjectComment, User.full_name)
        .outerjoin(User, User.id == ProjectComment.author_id)
        .where(ProjectComment.id == comment_id)
    )
    row = result.first()
    return (row[0], row[1]) if row is not None else None


async def create(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    author_id: uuid.UUID,
    body: str,
    visibility: CommentVisibility,
    stage=None,
) -> ProjectComment:
    comment = ProjectComment(
        project_id=project_id,
        author_id=author_id,
        body=body,
        visibility=visibility,
        stage=stage,
    )
    session.add(comment)
    await session.flush()
    return comment


async def update_fields(session: AsyncSession, comment_id: uuid.UUID, *, values: dict) -> bool:
    result = await session.execute(
        update(ProjectComment)
        .where(ProjectComment.id == comment_id, ProjectComment.deleted_at.is_(None))
        .values(**values)
    )
    return bool(result.rowcount)


async def soft_delete(session: AsyncSession, comment_id: uuid.UUID) -> bool:
    result = await session.execute(
        update(ProjectComment)
        .where(ProjectComment.id == comment_id, ProjectComment.deleted_at.is_(None))
        .values(deleted_at=datetime.now(UTC))
    )
    return bool(result.rowcount)


async def count_for_project(session: AsyncSession, project_id: uuid.UUID) -> int:
    result = await session.scalar(
        select(func.count(ProjectComment.id)).where(
            ProjectComment.project_id == project_id, ProjectComment.deleted_at.is_(None)
        )
    )
    return int(result or 0)

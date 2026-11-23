"""Control-point (checkpoint) queries."""

import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Checkpoint


async def get_by_id(session: AsyncSession, checkpoint_id: uuid.UUID) -> Checkpoint | None:
    return await session.get(Checkpoint, checkpoint_id)


async def list_for_school(
    session: AsyncSession,
    *,
    school_id: uuid.UUID | None,
    academic_year_id: uuid.UUID | None = None,
) -> list[Checkpoint]:
    """Admin view: only rows owned by the requested scope."""
    stmt = select(Checkpoint).where(Checkpoint.school_id == school_id)
    if academic_year_id is not None:
        stmt = stmt.where(Checkpoint.academic_year_id == academic_year_id)
    stmt = stmt.order_by(Checkpoint.academic_year_id, Checkpoint.sort_order, Checkpoint.due_at)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_active_for_year(
    session: AsyncSession,
    *,
    academic_year_id: uuid.UUID,
    school_id: uuid.UUID | None,
) -> list[Checkpoint]:
    """Active global and school checkpoints; a school row wins over a global one."""
    stmt = (
        select(Checkpoint)
        .where(
            Checkpoint.academic_year_id == academic_year_id,
            Checkpoint.is_active.is_(True),
            or_(
                Checkpoint.school_id == school_id,
                Checkpoint.school_id.is_(None),
            ),
        )
        .order_by(Checkpoint.due_at, Checkpoint.sort_order)
    )
    result = await session.execute(stmt)

    by_code: dict[str, Checkpoint] = {}
    for checkpoint in result.scalars().all():
        existing = by_code.get(checkpoint.code)
        if existing is None or checkpoint.school_id is not None:
            by_code[checkpoint.code] = checkpoint
    return sorted(by_code.values(), key=lambda item: (item.due_at, item.sort_order))


async def code_exists(
    session: AsyncSession,
    *,
    school_id: uuid.UUID | None,
    academic_year_id: uuid.UUID,
    code: str,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    stmt = select(Checkpoint.id).where(
        Checkpoint.school_id == school_id,
        Checkpoint.academic_year_id == academic_year_id,
        Checkpoint.code == code,
    )
    if exclude_id is not None:
        stmt = stmt.where(Checkpoint.id != exclude_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create(session: AsyncSession, **values) -> Checkpoint:
    checkpoint = Checkpoint(**values)
    session.add(checkpoint)
    await session.flush()
    return checkpoint


async def update_fields(session: AsyncSession, checkpoint_id: uuid.UUID, *, values: dict) -> bool:
    result = await session.execute(
        update(Checkpoint).where(Checkpoint.id == checkpoint_id).values(**values)
    )
    return bool(result.rowcount)

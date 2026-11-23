"""Checklist template and per-project state queries."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChecklistItem, ProjectChecklistState
from app.models.enums import ChecklistState


async def list_active_items(
    session: AsyncSession, *, academic_year_id: uuid.UUID, school_id: uuid.UUID | None
) -> list[ChecklistItem]:
    """School items override global items with the same code."""
    stmt = (
        select(ChecklistItem)
        .where(
            ChecklistItem.academic_year_id == academic_year_id,
            ChecklistItem.is_active.is_(True),
            (ChecklistItem.school_id == school_id) | (ChecklistItem.school_id.is_(None)),
        )
        .order_by(ChecklistItem.sort_order, ChecklistItem.title)
    )
    result = await session.execute(stmt)
    items = list(result.scalars().all())

    by_code: dict[str, ChecklistItem] = {}
    for item in items:
        # School-scoped rows come from the same query; let them win by code.
        if item.code not in by_code or item.school_id is not None:
            by_code[item.code] = item
    return sorted(by_code.values(), key=lambda item: (item.sort_order, item.title))


async def ensure_states(
    session: AsyncSession, *, project_id: uuid.UUID, item_ids: list[uuid.UUID]
) -> None:
    if not item_ids:
        return
    now = datetime.now(UTC)
    stmt = (
        insert(ProjectChecklistState)
        .values(
            [
                {
                    "project_id": project_id,
                    "checklist_item_id": item_id,
                    "status": ChecklistState.PENDING,
                    "updated_at": now,
                }
                for item_id in item_ids
            ]
        )
        .on_conflict_do_nothing(constraint="uq_project_checklist_states")
    )
    await session.execute(stmt)


async def list_states_with_items(
    session: AsyncSession, project_id: uuid.UUID
) -> list[tuple[ProjectChecklistState, ChecklistItem]]:
    result = await session.execute(
        select(ProjectChecklistState, ChecklistItem)
        .join(ChecklistItem, ChecklistItem.id == ProjectChecklistState.checklist_item_id)
        .where(
            ProjectChecklistState.project_id == project_id,
            ChecklistItem.is_active.is_(True),
        )
        .order_by(ChecklistItem.sort_order, ChecklistItem.title)
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_state(
    session: AsyncSession, state_id: uuid.UUID
) -> tuple[ProjectChecklistState, ChecklistItem] | None:
    result = await session.execute(
        select(ProjectChecklistState, ChecklistItem)
        .join(ChecklistItem, ChecklistItem.id == ProjectChecklistState.checklist_item_id)
        .where(ProjectChecklistState.id == state_id)
    )
    row = result.first()
    return (row[0], row[1]) if row is not None else None


async def get_state_for_item(
    session: AsyncSession, *, project_id: uuid.UUID, item_id: uuid.UUID
) -> tuple[ProjectChecklistState, ChecklistItem] | None:
    result = await session.execute(
        select(ProjectChecklistState, ChecklistItem)
        .join(ChecklistItem, ChecklistItem.id == ProjectChecklistState.checklist_item_id)
        .where(
            ProjectChecklistState.project_id == project_id,
            ProjectChecklistState.checklist_item_id == item_id,
        )
    )
    row = result.first()
    return (row[0], row[1]) if row is not None else None


async def update_state(session: AsyncSession, state_id: uuid.UUID, *, values: dict) -> bool:
    result = await session.execute(
        update(ProjectChecklistState).where(ProjectChecklistState.id == state_id).values(**values)
    )
    return bool(result.rowcount)


async def get_item(session: AsyncSession, item_id: uuid.UUID) -> ChecklistItem | None:
    return await session.get(ChecklistItem, item_id)


async def list_items_for_school(
    session: AsyncSession,
    *,
    school_id: uuid.UUID | None,
    academic_year_id: uuid.UUID | None = None,
) -> list[ChecklistItem]:
    stmt = select(ChecklistItem).where(ChecklistItem.school_id == school_id)
    if academic_year_id is not None:
        stmt = stmt.where(ChecklistItem.academic_year_id == academic_year_id)
    stmt = stmt.order_by(ChecklistItem.academic_year_id, ChecklistItem.sort_order)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_item(session: AsyncSession, **values) -> ChecklistItem:
    item = ChecklistItem(**values)
    session.add(item)
    await session.flush()
    return item


async def update_item(session: AsyncSession, item_id: uuid.UUID, *, values: dict) -> bool:
    result = await session.execute(
        update(ChecklistItem).where(ChecklistItem.id == item_id).values(**values)
    )
    return bool(result.rowcount)

"""Audit-log queries."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User


@dataclass(slots=True)
class AuditRow:
    entry: AuditLog
    actor_name: str | None


async def create(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    school_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    payload: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        school_id=school_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )
    session.add(entry)
    await session.flush()
    return entry


async def list_entries(
    session: AsyncSession,
    *,
    school_id: uuid.UUID | None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditRow]:
    stmt = (
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if school_id is not None:
        stmt = stmt.where(AuditLog.school_id == school_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    result = await session.execute(stmt)
    return [AuditRow(entry=row[0], actor_name=row[1]) for row in result.all()]

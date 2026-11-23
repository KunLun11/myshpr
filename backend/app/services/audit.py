"""Audit-log writing and reading (stage 6)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.enums import UserRole
from app.repositories import audit as audit_repo
from app.schemas.audit import AuditEntryOut

_UNSET = object()


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


async def record(
    session: AsyncSession,
    actor: User,
    action: str,
    *,
    entity_type: str,
    entity_id: uuid.UUID | str | None = None,
    payload: dict | None = None,
    school_id: uuid.UUID | None | object = _UNSET,
) -> None:
    """Persist one admin action.

    The caller's school is used by default; pass ``school_id=None`` explicitly
    for platform-wide changes (for example global reference data).
    """
    if school_id is _UNSET:
        target_school: uuid.UUID | None = actor.school_id
    else:
        target_school = school_id if isinstance(school_id, uuid.UUID) else None

    await audit_repo.create(
        session,
        actor_id=actor.id,
        school_id=target_school,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        payload=_jsonable(payload) if payload else None,
    )
    await session.commit()


async def list_entries(
    session: AsyncSession,
    user: User,
    *,
    school_id: uuid.UUID | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEntryOut]:
    target_school = school_id
    if user.role is not UserRole.SUPER_ADMIN:
        target_school = user.school_id

    rows = await audit_repo.list_entries(
        session,
        school_id=target_school,
        action=action,
        limit=limit,
        offset=offset,
    )
    return [
        AuditEntryOut(
            id=row.entry.id,
            created_at=row.entry.created_at,
            actor_id=row.entry.actor_id,
            actor_name=row.actor_name,
            school_id=row.entry.school_id,
            action=row.entry.action,
            entity_type=row.entry.entity_type,
            entity_id=row.entry.entity_id,
            payload=row.entry.payload,
        )
        for row in rows
    ]

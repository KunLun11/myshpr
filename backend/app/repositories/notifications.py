"""Notification queries: in-app notifications and reminder idempotency."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification
from app.models.enums import NotificationChannel, NotificationStatus, NotificationType


async def create_in_app(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    body: str,
    dedupe_key: str,
    project_id: uuid.UUID | None = None,
    checkpoint_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> bool:
    """Insert an in-app notification; the dedupe key makes it idempotent.

    Returns ``True`` when a new row was created, ``False`` when the key
    already existed (the daily reminder job relies on this).
    """
    now = datetime.now(UTC)
    stmt = (
        insert(Notification)
        .values(
            user_id=user_id,
            project_id=project_id,
            checkpoint_id=checkpoint_id,
            type=type,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.SENT,
            title=title,
            body=body,
            payload=payload,
            dedupe_key=dedupe_key,
            scheduled_at=now,
            sent_at=now,
        )
        .on_conflict_do_nothing(index_elements=["dedupe_key"])
    )
    result = await session.execute(stmt)
    return bool(result.rowcount)


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def count_for_user(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.scalar(
        select(func.count(Notification.id)).where(Notification.user_id == user_id)
    )
    return int(result or 0)


async def unread_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
    )
    return int(result or 0)


async def get_for_user(
    session: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
) -> Notification | None:
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    return result.scalars().first()


async def mark_read(session: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await session.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    return bool(result.rowcount)

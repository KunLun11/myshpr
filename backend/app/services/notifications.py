"""In-app notifications for the current user."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Notification, User
from app.repositories import notifications as notifications_repo
from app.schemas.notification import NotificationListOut, NotificationOut


def serialize(notification: Notification) -> NotificationOut:
    return NotificationOut(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        body=notification.body,
        project_id=notification.project_id,
        checkpoint_id=notification.checkpoint_id,
        payload=notification.payload,
        created_at=notification.created_at,
        sent_at=notification.sent_at,
        read_at=notification.read_at,
        is_read=notification.read_at is not None,
    )


async def list_my(
    session: AsyncSession,
    user: User,
    *,
    limit: int = 50,
    offset: int = 0,
) -> NotificationListOut:
    rows = await notifications_repo.list_for_user(session, user.id, limit=limit, offset=offset)
    return NotificationListOut(
        items=[serialize(row) for row in rows],
        unread_count=await notifications_repo.unread_count(session, user.id),
        total=await notifications_repo.count_for_user(session, user.id),
    )


async def mark_read(
    session: AsyncSession, user: User, notification_id: uuid.UUID
) -> NotificationOut:
    notification = await notifications_repo.get_for_user(session, notification_id, user.id)
    if notification is None:
        raise NotFoundError("Уведомление не найдено", "NOTIFICATION_NOT_FOUND")
    if notification.read_at is None:
        await notifications_repo.mark_read(session, notification_id, user.id)
        await session.commit()
        await session.refresh(notification)
    return serialize(notification)

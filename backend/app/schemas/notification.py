"""In-app notification schemas (stage 5)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    body: str
    project_id: UUID | None = None
    checkpoint_id: UUID | None = None
    payload: dict | None = None
    created_at: datetime
    sent_at: datetime | None = None
    read_at: datetime | None = None
    is_read: bool = False


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int
    total: int

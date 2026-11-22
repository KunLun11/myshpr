"""Engagement: checkpoints and notifications."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, true
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    CHECKPOINT_AUDIENCE_ENUM,
    NOTIFICATION_CHANNEL_ENUM,
    NOTIFICATION_STATUS_ENUM,
    NOTIFICATION_TYPE_ENUM,
    PROJECT_STATUS_ENUM,
    CheckpointAudience,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    ProjectStatus,
)


class Checkpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "academic_year_id",
            "code",
            name="uq_checkpoints_school_year_code",
            postgresql_nulls_not_distinct=True,
        ),
    )

    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    required_status: Mapped[ProjectStatus] = mapped_column(PROJECT_STATUS_ENUM, nullable=False)
    audience: Mapped[CheckpointAudience] = mapped_column(
        CHECKPOINT_AUDIENCE_ENUM,
        nullable=False,
        default=CheckpointAudience.STUDENT,
        server_default="'student'",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at"),
        Index("ix_notifications_status_scheduled", "status", "scheduled_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    checkpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("checkpoints.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[NotificationType] = mapped_column(NOTIFICATION_TYPE_ENUM, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(NOTIFICATION_CHANNEL_ENUM, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        NOTIFICATION_STATUS_ENUM,
        nullable=False,
        default=NotificationStatus.PENDING,
        server_default="'pending'",
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

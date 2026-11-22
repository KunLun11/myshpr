"""Work artifacts: teacher comments."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    COMMENT_VISIBILITY_ENUM,
    PROJECT_STATUS_ENUM,
    CommentVisibility,
    ProjectStatus,
)


class ProjectComment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_comments"
    __table_args__ = (
        Index("ix_project_comments_project_created", "project_id", "created_at"),
        Index("ix_project_comments_author", "author_id"),
        CheckConstraint("char_length(body) BETWEEN 1 AND 5000", name="body"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[CommentVisibility] = mapped_column(
        COMMENT_VISIBILITY_ENUM,
        nullable=False,
        default=CommentVisibility.STUDENT_VISIBLE,
        server_default="'student_visible'",
    )
    stage: Mapped[ProjectStatus | None] = mapped_column(PROJECT_STATUS_ENUM, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

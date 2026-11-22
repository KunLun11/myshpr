"""Checklists: template items and per-project states."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    CHECKLIST_STATE_ENUM,
    PROJECT_STATUS_ENUM,
    ChecklistState,
    ProjectStatus,
)


class ChecklistItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "checklist_items"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "academic_year_id",
            "code",
            name="uq_checklist_items_school_year_code",
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "ix_checklist_items_year_stage",
            "academic_year_id",
            "stage",
            "sort_order",
            postgresql_where=text("is_active"),
        ),
    )

    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[ProjectStatus] = mapped_column(PROJECT_STATUS_ENUM, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())


class ProjectChecklistState(UUIDPrimaryKeyMixin, UpdatedAtMixin, Base):
    __tablename__ = "project_checklist_states"
    __table_args__ = (
        UniqueConstraint("project_id", "checklist_item_id", name="uq_project_checklist_states"),
        Index("ix_project_checklist_states_project", "project_id", "status"),
        Index("ix_project_checklist_states_item", "checklist_item_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    checklist_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("checklist_items.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ChecklistState] = mapped_column(
        CHECKLIST_STATE_ENUM,
        nullable=False,
        default=ChecklistState.PENDING,
        server_default="'pending'",
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    marked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

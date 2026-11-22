"""Core process: projects and their event log."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PROJECT_STATUS_ENUM, ProjectStatus


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year_id", name="uq_projects_student_year"),
        Index(
            "idx_projects_dashboard",
            "academic_year_id",
            "class_id",
            "status",
            postgresql_where=text("archived_at IS NULL"),
        ),
        Index("ix_projects_last_activity", "last_activity_at"),
        Index("ix_projects_student_id", "student_id"),
        Index("ix_projects_academic_year_id", "academic_year_id"),
        Index("ix_projects_class_id", "class_id"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False
    )
    status: Mapped[ProjectStatus] = mapped_column(
        PROJECT_STATUS_ENUM,
        nullable=False,
        default=ProjectStatus.IDEA,
        server_default=text("'idea'"),
    )
    interest_area_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interest_areas.id", ondelete="SET NULL"), nullable=True
    )
    research_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )
    product_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_brief: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    topic_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    product_defined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectEvent(CreatedAtMixin, Base):
    __tablename__ = "project_events"
    __table_args__ = (
        Index("ix_project_events_project_created", "project_id", "created_at"),
        Index("ix_project_events_type_created", "event_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

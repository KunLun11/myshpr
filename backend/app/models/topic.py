"""Topics: submissions and the approved-topic registry."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    TOPIC_STATUS_ENUM,
    TOPIC_SUBMISSION_STATUS_ENUM,
    TopicStatus,
    TopicSubmissionStatus,
)


class TopicSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "topic_submissions"
    __table_args__ = (
        Index(
            "uq_topic_submissions_active",
            "project_id",
            unique=True,
            postgresql_where=text("status IN ('draft', 'submitted')"),
        ),
        Index("ix_topic_submissions_project_created", "project_id", "created_at"),
        Index("ix_topic_submissions_review", "school_id", "academic_year_id", "status"),
        Index(
            "ix_topic_submissions_title_trgm",
            "normalized_title",
            postgresql_using="gin",
            postgresql_ops={"normalized_title": "gin_trgm_ops"},
        ),
        CheckConstraint(
            "duplicate_score IS NULL OR (duplicate_score >= 0 AND duplicate_score <= 1)",
            name="duplicate_score",
        ),
        CheckConstraint(
            "broadness_score IS NULL OR (broadness_score >= 0 AND broadness_score <= 100)",
            name="broadness_score",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    author_student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    interest_area_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interest_areas.id", ondelete="SET NULL"), nullable=True
    )
    research_question: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TopicSubmissionStatus] = mapped_column(
        TOPIC_SUBMISSION_STATUS_ENUM,
        nullable=False,
        default=TopicSubmissionStatus.DRAFT,
        server_default=text("'draft'"),
    )
    duplicate_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    duplicate_of_topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    broadness_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    broadness_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Topic(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("school_id", "normalized_title", name="uq_topics_school_title"),
        Index(
            "ix_topics_title_trgm",
            "normalized_title",
            postgresql_using="gin",
            postgresql_ops={"normalized_title": "gin_trgm_ops"},
        ),
        Index("ix_topics_school_year_status", "school_id", "academic_year_id", "status"),
    )

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    research_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )
    author_student_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    source_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topic_submissions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
        unique=True,
    )
    status: Mapped[TopicStatus] = mapped_column(
        TOPIC_STATUS_ENUM,
        nullable=False,
        default=TopicStatus.ACTIVE,
        server_default=text("'active'"),
    )
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

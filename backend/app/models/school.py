"""Organization and identity: schools, academic years, classes, invites."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class School(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="Europe/Moscow")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())

    academic_years: Mapped[list["AcademicYear"]] = relationship(back_populates="school")
    classes: Mapped[list["SchoolClass"]] = relationship(back_populates="school")


class AcademicYear(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "academic_years"
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_academic_years_school_name"),
        Index(
            "uq_academic_years_school_current",
            "school_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())

    school: Mapped[School] = relationship(back_populates="academic_years")
    classes: Mapped[list["SchoolClass"]] = relationship(back_populates="academic_year")


class SchoolClass(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "academic_year_id",
            "grade",
            "label",
            name="uq_classes_school_year_grade_label",
        ),
        CheckConstraint("grade BETWEEN 9 AND 11", name="grade"),
        Index("ix_classes_curator_id", "curator_id"),
    )

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    grade: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    curator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    school: Mapped[School] = relationship(back_populates="classes")
    academic_year: Mapped[AcademicYear] = relationship(back_populates="classes")


class ClassInvite(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "class_invites"
    __table_args__ = (
        CheckConstraint(
            "uses_count >= 0 AND (max_uses IS NULL OR uses_count <= max_uses)", name="uses"
        ),
    )

    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

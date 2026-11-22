"""Work artifacts: project files."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import FILE_KIND_ENUM, FILE_STATUS_ENUM, FileKind, FileStatus

MAX_UPLOAD_BYTES = 26_214_400  # 25 MiB


class ProjectFile(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "project_files"
    __table_args__ = (
        UniqueConstraint("project_id", "checksum_sha256", name="uq_project_files_project_checksum"),
        Index("ix_project_files_project_created", "project_id", "created_at"),
        Index("ix_project_files_status", "status"),
        CheckConstraint(f"size_bytes > 0 AND size_bytes <= {MAX_UPLOAD_BYTES}", name="size"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[FileKind] = mapped_column(
        FILE_KIND_ENUM,
        nullable=False,
        default=FileKind.FINAL_WORK,
        server_default="'final_work'",
    )
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[FileStatus] = mapped_column(
        FILE_STATUS_ENUM,
        nullable=False,
        default=FileStatus.UPLOADED,
        server_default="'uploaded'",
    )
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

"""Project file schemas (stage 4)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import FileKind, FileStatus


class ProjectFileOut(BaseModel):
    id: UUID
    project_id: UUID
    kind: FileKind
    original_name: str
    mime_type: str
    size_bytes: int
    status: FileStatus
    created_at: datetime
    download_url: str

"""Control-point (checkpoint) schemas (stage 5)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import CheckpointAudience, ProjectStatus


class NextCheckpointOut(BaseModel):
    """The next unresolved control point for a student."""

    id: UUID
    code: str
    title: str
    due_at: datetime
    days_left: int
    required_status: ProjectStatus
    overdue: bool


class CheckpointCreateRequest(BaseModel):
    academic_year_id: UUID
    code: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    due_at: datetime
    required_status: ProjectStatus
    audience: CheckpointAudience = CheckpointAudience.STUDENT
    sort_order: int = 100
    is_active: bool = True


class CheckpointUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    required_status: ProjectStatus | None = None
    audience: CheckpointAudience | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CheckpointOut(BaseModel):
    id: UUID
    school_id: UUID | None = None
    academic_year_id: UUID
    code: str
    title: str
    description: str | None = None
    due_at: datetime
    required_status: ProjectStatus
    audience: CheckpointAudience
    is_active: bool
    sort_order: int

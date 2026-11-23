"""Checklist template and per-project state schemas (stage 4)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ChecklistState, ProjectStatus


class ChecklistItemStateOut(BaseModel):
    id: UUID
    checklist_item_id: UUID
    code: str
    title: str
    description: str | None = None
    stage: ProjectStatus
    is_required: bool
    due_at: datetime | None = None
    status: ChecklistState
    overdue: bool = False
    marked_at: datetime | None = None
    verified_at: datetime | None = None
    comment: str | None = None


class ChecklistStageOut(BaseModel):
    stage: ProjectStatus
    title: str
    items: list[ChecklistItemStateOut]
    done_count: int
    total_count: int
    required_done: int
    required_total: int


class ChecklistProgressOut(BaseModel):
    done: int
    required: int
    percent: int


class ChecklistOut(BaseModel):
    project_id: UUID
    stages: list[ChecklistStageOut]
    progress: ChecklistProgressOut
    overdue_count: int


class ChecklistStateUpdateRequest(BaseModel):
    """What a student may do: start or finish an item."""

    status: ChecklistState = Field(
        description="pending, in_progress or done. verified/skipped belong to staff."
    )


class ChecklistVerifyRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)


class AdminChecklistItemCreateRequest(BaseModel):
    academic_year_id: UUID
    stage: ProjectStatus
    code: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = 100
    is_required: bool = True
    due_at: datetime | None = None
    is_active: bool = True


class AdminChecklistItemUpdateRequest(BaseModel):
    stage: ProjectStatus | None = None
    code: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = None
    is_required: bool | None = None
    due_at: datetime | None = None
    is_active: bool | None = None


class AdminChecklistItemOut(BaseModel):
    id: UUID
    school_id: UUID | None = None
    academic_year_id: UUID
    stage: ProjectStatus
    code: str
    title: str
    description: str | None = None
    sort_order: int
    is_required: bool
    due_at: datetime | None = None
    is_active: bool

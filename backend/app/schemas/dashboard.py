"""Teacher dashboard read models (stage 5)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.checkpoint import NextCheckpointOut

TrafficLight = Literal["green", "yellow", "red"]


class StatusReasonOut(BaseModel):
    code: str
    label: str
    severity: TrafficLight


class DashboardStudentOut(BaseModel):
    student_id: UUID
    student_full_name: str
    project_id: UUID | None = None
    status: str
    color: TrafficLight
    reasons: list[StatusReasonOut] = Field(default_factory=list)

    last_activity_at: datetime | None = None
    inactive_days: int | None = None
    next_checkpoint: NextCheckpointOut | None = None

    checklist_done: int = 0
    checklist_total: int = 0
    checklist_overdue: int = 0
    has_final_file: bool = False
    files_count: int = 0

    last_comment_at: datetime | None = None
    last_comment_excerpt: str | None = None
    topic_title: str | None = None


class DashboardSummaryOut(BaseModel):
    total: int = 0
    green: int = 0
    yellow: int = 0
    red: int = 0


class ClassDashboardOut(BaseModel):
    class_id: UUID
    class_label: str
    class_grade: int
    academic_year_name: str | None = None
    generated_at: datetime
    summary: DashboardSummaryOut
    students: list[DashboardStudentOut]

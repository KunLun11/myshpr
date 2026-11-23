"""Student project and topic-draft schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.checkpoint import NextCheckpointOut


class InterestAreaBrief(BaseModel):
    id: UUID
    slug: str
    name: str


class CheckMessage(BaseModel):
    field: str
    message: str


class TopicDraftOut(BaseModel):
    id: UUID
    status: str
    title: str
    normalized_title: str
    research_question: str
    duplicate_score: float | None = None
    broadness_score: int | None = None
    broadness_reasons: list[str] = Field(default_factory=list)
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    updated_at: datetime


class ProjectOut(BaseModel):
    id: UUID
    status: str
    class_id: UUID
    class_label: str
    class_grade: int
    academic_year_id: UUID
    academic_year_name: str | None = None
    interest_area: InterestAreaBrief | None = None
    research_question: str | None = None
    topic_approved_at: datetime | None = None
    product_defined_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    topic: TopicDraftOut | None = None
    next_checkpoint: NextCheckpointOut | None = None


class ProjectPatchRequest(BaseModel):
    """Partial draft update.

    Fields that are omitted are left untouched; sending ``null`` clears an
    optional field (for example, the chosen interest area).
    """

    interest_area_id: UUID | None = None
    research_question: str | None = Field(default=None, max_length=500)
    topic_title: str | None = Field(default=None, max_length=300)


class ProjectPatchResponse(BaseModel):
    project: ProjectOut
    warnings: list[CheckMessage] = Field(default_factory=list)


class TeacherProjectOut(BaseModel):
    """Compact project card for staff lists and the project workspace."""

    id: UUID
    status: str
    student_full_name: str
    class_label: str
    class_grade: int
    academic_year_name: str | None = None
    topic_title: str | None = None
    research_question: str | None = None
    topic_status: str | None = None
    product_category_id: UUID | None = None
    product_category_name: str | None = None
    product_description: str | None = None
    product_brief: dict | None = None
    product_defined_at: datetime | None = None
    last_activity_at: datetime
    files_count: int = 0
    comments_count: int = 0

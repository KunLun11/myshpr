"""Topic check, submission and teacher review schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.projects import CheckMessage

CheckLevel = Literal["ok", "warn", "block"]


class TopicCheckRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    research_question: str | None = Field(default=None, max_length=500)


class DuplicateMatchOut(BaseModel):
    source: Literal["registry", "pending"]
    id: UUID
    title: str
    score: float


class DuplicateOut(BaseModel):
    level: CheckLevel
    exact: bool
    best_score: float
    matches: list[DuplicateMatchOut] = Field(default_factory=list)


class BroadnessOut(BaseModel):
    score: int
    level: CheckLevel
    reasons: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class TopicCheckOut(BaseModel):
    title: str
    normalized_title: str
    errors: list[CheckMessage] = Field(default_factory=list)
    warnings: list[CheckMessage] = Field(default_factory=list)
    duplicate: DuplicateOut
    broadness: BroadnessOut
    can_submit: bool


class TopicSubmitRequest(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    research_question: str | None = Field(default=None, max_length=500)


class SubmissionOut(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    title: str
    research_question: str
    student_full_name: str
    class_label: str
    interest_area_name: str | None = None
    submitted_at: datetime
    duplicate_score: float | None = None
    duplicate_level: CheckLevel
    duplicate_of_title: str | None = None
    broadness_score: int | None = None
    broadness_level: CheckLevel
    broadness_reasons: list[str] = Field(default_factory=list)
    review_comment: str | None = None
    reviewed_at: datetime | None = None


class SubmissionDecisionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class SubmissionRejectRequest(BaseModel):
    comment: str = Field(min_length=3, max_length=2000)


class RegistryTopicOut(BaseModel):
    id: UUID
    title: str
    research_question: str | None = None
    author_full_name: str | None = None
    interest_area_name: str | None = None
    academic_year_name: str | None = None
    approved_at: datetime

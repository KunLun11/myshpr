"""Teacher comment schemas (stage 4)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import CommentVisibility, ProjectStatus

COMMENT_BODY_MIN = 1
COMMENT_BODY_MAX = 5000


class CommentCreateRequest(BaseModel):
    body: str = Field(min_length=COMMENT_BODY_MIN, max_length=COMMENT_BODY_MAX)
    visibility: CommentVisibility = CommentVisibility.STUDENT_VISIBLE
    stage: ProjectStatus | None = None


class CommentUpdateRequest(BaseModel):
    body: str | None = Field(default=None, min_length=COMMENT_BODY_MIN, max_length=COMMENT_BODY_MAX)
    visibility: CommentVisibility | None = None
    stage: ProjectStatus | None = None


class CommentOut(BaseModel):
    id: UUID
    project_id: UUID
    body: str
    visibility: CommentVisibility
    stage: ProjectStatus | None = None
    author_full_name: str | None = None
    created_at: datetime
    updated_at: datetime
    can_edit: bool = False

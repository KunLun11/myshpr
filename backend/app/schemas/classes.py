"""Classes, students and invite schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ClassOut(BaseModel):
    id: UUID
    grade: int
    label: str
    academic_year_id: UUID
    academic_year_name: str | None = None
    curator_id: UUID | None = None
    students_count: int = 0


class ClassCreateRequest(BaseModel):
    grade: int = Field(ge=9, le=11)
    label: str = Field(min_length=1, max_length=20)
    academic_year_id: UUID | None = None
    curator_id: UUID | None = None


class StudentOut(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    class_id: UUID


class InviteCreateRequest(BaseModel):
    max_uses: int | None = Field(default=None, ge=1, le=1000)
    expires_in_days: int = Field(default=14, ge=1, le=90)


class InviteOut(BaseModel):
    id: UUID
    code: str
    expires_at: datetime
    max_uses: int | None = None
    uses_count: int
    register_url: str


# --- Stage 6: admin student list and CSV import -----------------------------


class AdminStudentOut(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    class_id: UUID
    class_label: str
    class_grade: int
    academic_year_name: str | None = None


class ImportedStudentOut(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    temp_password: str


class ImportSkipOut(BaseModel):
    row: int
    email: str | None = None
    reason: str


class StudentImportResult(BaseModel):
    created: list[ImportedStudentOut]
    skipped: list[ImportSkipOut]
    created_count: int
    skipped_count: int

"""Auth API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole


def _check_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Пароль не должен быть длиннее 72 байт")
    return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class RegisterStudentRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=200)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return _check_password_bytes(value)

    @field_validator("full_name", "invite_code")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return _check_password_bytes(value)


class SchoolBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class ClassBrief(BaseModel):
    id: UUID
    grade: int
    label: str
    academic_year_name: str | None = None


class MeOut(BaseModel):
    """Current user plus school/class context for the UI."""

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    school: SchoolBrief | None = None
    class_info: ClassBrief | None = Field(default=None, alias="class")
    must_change_password: bool = False

    model_config = ConfigDict(populate_by_name=True)

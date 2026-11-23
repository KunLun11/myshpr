"""Admin schemas for schools and academic years (stage 6)."""

from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


class SchoolOut(BaseModel):
    id: UUID
    name: str
    region: str | None = None
    city: str | None = None
    timezone: str
    is_active: bool
    created_at: datetime


class SchoolCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    region: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=200)
    timezone: str = Field(default="Europe/Moscow", max_length=100)
    is_active: bool = True

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Неизвестный часовой пояс") from exc
        return value


class SchoolUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    region: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=200)
    timezone: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Неизвестный часовой пояс") from exc
        return value


class AcademicYearOut(BaseModel):
    id: UUID
    school_id: UUID
    name: str
    starts_on: date
    ends_on: date
    is_current: bool


class AcademicYearCreateRequest(BaseModel):
    school_id: UUID | None = None
    name: str = Field(min_length=1, max_length=100)
    starts_on: date
    ends_on: date
    is_current: bool = False

    @model_validator(mode="after")
    def _dates_ordered(self) -> "AcademicYearCreateRequest":
        if self.ends_on <= self.starts_on:
            raise ValueError("Дата окончания должна быть позже даты начала")
        return self


class AcademicYearUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    starts_on: date | None = None
    ends_on: date | None = None
    is_current: bool | None = None

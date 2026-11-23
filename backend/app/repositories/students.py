"""Student listings and import helpers for the admin area."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicYear, SchoolClass, StudentProfile, User


@dataclass(slots=True)
class StudentRow:
    user_id: uuid.UUID
    full_name: str
    email: str
    is_active: bool
    created_at: datetime
    class_id: uuid.UUID
    class_label: str
    class_grade: int
    academic_year_name: str | None
    school_id: uuid.UUID


async def list_students(
    session: AsyncSession,
    *,
    school_id: uuid.UUID | None = None,
    class_id: uuid.UUID | None = None,
    query: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[StudentRow]:
    stmt = (
        select(
            User.id,
            User.full_name,
            User.email,
            User.is_active,
            User.created_at,
            SchoolClass.id,
            SchoolClass.label,
            SchoolClass.grade,
            AcademicYear.name,
            SchoolClass.school_id,
        )
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .join(SchoolClass, SchoolClass.id == StudentProfile.class_id)
        .join(AcademicYear, AcademicYear.id == SchoolClass.academic_year_id)
        .where(User.deleted_at.is_(None))
        .order_by(SchoolClass.grade, SchoolClass.label, User.full_name)
        .limit(limit)
        .offset(offset)
    )
    if school_id is not None:
        stmt = stmt.where(SchoolClass.school_id == school_id)
    if class_id is not None:
        stmt = stmt.where(SchoolClass.id == class_id)
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))

    result = await session.execute(stmt)
    return [
        StudentRow(
            user_id=row[0],
            full_name=row[1],
            email=row[2],
            is_active=row[3],
            created_at=row[4],
            class_id=row[5],
            class_label=row[6],
            class_grade=row[7],
            academic_year_name=row[8],
            school_id=row[9],
        )
        for row in result.all()
    ]


async def existing_emails(session: AsyncSession, emails: list[str]) -> set[str]:
    if not emails:
        return set()
    normalized = {email.strip().lower() for email in emails if email.strip()}
    if not normalized:
        return set()
    result = await session.execute(
        select(func.lower(User.email)).where(func.lower(User.email).in_(normalized))
    )
    return {row[0] for row in result.all()}

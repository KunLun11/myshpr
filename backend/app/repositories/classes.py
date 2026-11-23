"""Class, student and invite queries."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicYear, ClassInvite, SchoolClass, StudentProfile, User


@dataclass(slots=True)
class ClassRow:
    school_class: SchoolClass
    academic_year_name: str | None
    students_count: int


async def get_by_id(session: AsyncSession, class_id: uuid.UUID) -> SchoolClass | None:
    return await session.get(SchoolClass, class_id)


async def get_student_profile(session: AsyncSession, user_id: uuid.UUID) -> StudentProfile | None:
    return await session.get(StudentProfile, user_id)


async def get_current_year(session: AsyncSession, school_id: uuid.UUID) -> AcademicYear | None:
    result = await session.execute(
        select(AcademicYear).where(
            AcademicYear.school_id == school_id, AcademicYear.is_current.is_(True)
        )
    )
    return result.scalars().first()


async def get_invite_by_code(
    session: AsyncSession, code: str, *, for_update: bool = False
) -> ClassInvite | None:
    """Look up an invite case-insensitively; optionally lock the row."""
    stmt = select(ClassInvite).where(func.upper(ClassInvite.code) == code.strip().upper())
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_invite_by_id(session: AsyncSession, invite_id: uuid.UUID) -> ClassInvite | None:
    return await session.get(ClassInvite, invite_id)


async def code_exists(session: AsyncSession, code: str) -> bool:
    result = await session.execute(select(ClassInvite.id).where(ClassInvite.code == code))
    return result.scalar_one_or_none() is not None


def _class_rows_stmt():
    students_count = func.count(StudentProfile.user_id)
    return (
        select(SchoolClass, AcademicYear.name, students_count)
        .join(AcademicYear, AcademicYear.id == SchoolClass.academic_year_id)
        .outerjoin(StudentProfile, StudentProfile.class_id == SchoolClass.id)
        .group_by(SchoolClass.id, AcademicYear.name)
        .order_by(AcademicYear.name.desc(), SchoolClass.grade, SchoolClass.label)
    )


def _to_rows(result) -> list[ClassRow]:
    return [ClassRow(row[0], row[1], row[2]) for row in result.all()]


async def list_teacher_classes(session: AsyncSession, teacher_id: uuid.UUID) -> list[ClassRow]:
    result = await session.execute(_class_rows_stmt().where(SchoolClass.curator_id == teacher_id))
    return _to_rows(result)


async def list_school_classes(session: AsyncSession, school_id: uuid.UUID | None) -> list[ClassRow]:
    stmt = _class_rows_stmt()
    if school_id is not None:
        stmt = stmt.where(SchoolClass.school_id == school_id)
    return _to_rows(await session.execute(stmt))


async def get_class_row(session: AsyncSession, class_id: uuid.UUID) -> ClassRow | None:
    result = await session.execute(_class_rows_stmt().where(SchoolClass.id == class_id))
    row = result.first()
    return ClassRow(row[0], row[1], row[2]) if row else None


async def count_students(session: AsyncSession, class_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count(StudentProfile.user_id)).where(StudentProfile.class_id == class_id)
    )
    return int(result.scalar_one())


async def list_class_students(
    session: AsyncSession, class_id: uuid.UUID
) -> list[tuple[uuid.UUID, str, str, uuid.UUID]]:
    result = await session.execute(
        select(User.id, User.full_name, User.email, StudentProfile.class_id)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .where(StudentProfile.class_id == class_id, User.deleted_at.is_(None))
        .order_by(User.full_name)
    )
    return [(row[0], row[1], row[2], row[3]) for row in result.all()]


# --- Stage 5: reminder job lookups -----------------------------------------


async def list_current_years(session: AsyncSession) -> list[AcademicYear]:
    result = await session.execute(
        select(AcademicYear).where(AcademicYear.is_current.is_(True)).order_by(AcademicYear.name)
    )
    return list(result.scalars().all())


async def list_classes_for_year(
    session: AsyncSession, academic_year_id: uuid.UUID
) -> list[SchoolClass]:
    result = await session.execute(
        select(SchoolClass)
        .where(SchoolClass.academic_year_id == academic_year_id)
        .order_by(SchoolClass.grade, SchoolClass.label)
    )
    return list(result.scalars().all())

"""Small async factories for building test rows."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicYear, Project, School, SchoolClass, User
from app.models.enums import UserRole


def _uid() -> str:
    return uuid.uuid4().hex[:8]


async def create_school(session: AsyncSession, name: str | None = None) -> School:
    school = School(name=name or f"School {_uid()}")
    session.add(school)
    await session.flush()
    return school


async def create_year(
    session: AsyncSession, school: School, name: str | None = None
) -> AcademicYear:
    year = AcademicYear(
        school_id=school.id,
        name=name or f"2026/{_uid()}",
        starts_on=date(2026, 9, 1),
        ends_on=date(2027, 5, 31),
    )
    session.add(year)
    await session.flush()
    return year


async def create_user(
    session: AsyncSession, school: School, role: UserRole = UserRole.STUDENT
) -> User:
    user = User(
        school_id=school.id,
        role=role,
        email=f"{_uid()}@example.com",
        password_hash="x",
        full_name="Test User",
    )
    session.add(user)
    await session.flush()
    return user


async def create_class(session: AsyncSession, school: School, year: AcademicYear) -> SchoolClass:
    klass = SchoolClass(
        school_id=school.id,
        academic_year_id=year.id,
        grade=9,
        label=f"9{_uid()[:2]}",
    )
    session.add(klass)
    await session.flush()
    return klass


async def create_project(
    session: AsyncSession, student: User, year: AcademicYear, klass: SchoolClass, **kwargs
) -> Project:
    project = Project(
        student_id=student.id,
        academic_year_id=year.id,
        class_id=klass.id,
        **kwargs,
    )
    session.add(project)
    await session.flush()
    return project

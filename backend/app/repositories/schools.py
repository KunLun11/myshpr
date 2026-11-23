"""School and academic-year queries for the admin area."""

import uuid
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicYear, School


async def list_schools(
    session: AsyncSession, *, school_id: uuid.UUID | None = None
) -> list[School]:
    stmt = select(School).order_by(School.name)
    if school_id is not None:
        stmt = stmt.where(School.id == school_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_school(session: AsyncSession, school_id: uuid.UUID) -> School | None:
    return await session.get(School, school_id)


async def create_school(
    session: AsyncSession,
    *,
    name: str,
    region: str | None,
    city: str | None,
    timezone: str,
    is_active: bool,
) -> School:
    school = School(
        name=name,
        region=region,
        city=city,
        timezone=timezone,
        is_active=is_active,
    )
    session.add(school)
    await session.flush()
    return school


async def update_school(session: AsyncSession, school: School, *, values: dict) -> None:
    for field, value in values.items():
        setattr(school, field, value)
    await session.flush()


async def list_years(
    session: AsyncSession, *, school_id: uuid.UUID | None = None
) -> list[AcademicYear]:
    stmt = select(AcademicYear).order_by(AcademicYear.starts_on.desc(), AcademicYear.name.desc())
    if school_id is not None:
        stmt = stmt.where(AcademicYear.school_id == school_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_year(session: AsyncSession, year_id: uuid.UUID) -> AcademicYear | None:
    return await session.get(AcademicYear, year_id)


async def create_year(
    session: AsyncSession,
    *,
    school_id: uuid.UUID,
    name: str,
    starts_on: date,
    ends_on: date,
    is_current: bool,
) -> AcademicYear:
    year = AcademicYear(
        school_id=school_id,
        name=name,
        starts_on=starts_on,
        ends_on=ends_on,
        is_current=is_current,
    )
    session.add(year)
    await session.flush()
    return year


async def update_year(session: AsyncSession, year: AcademicYear, *, values: dict) -> None:
    for field, value in values.items():
        setattr(year, field, value)
    await session.flush()


async def clear_current(session: AsyncSession, *, school_id: uuid.UUID, keep_id: uuid.UUID) -> None:
    await session.execute(
        update(AcademicYear)
        .where(
            AcademicYear.school_id == school_id,
            AcademicYear.id != keep_id,
            AcademicYear.is_current.is_(True),
        )
        .values(is_current=False)
    )

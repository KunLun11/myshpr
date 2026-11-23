"""School and academic-year business rules for the admin area (stage 6)."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models import AcademicYear, School, User
from app.models.enums import UserRole
from app.repositories import schools as schools_repo
from app.schemas.admin_org import (
    AcademicYearCreateRequest,
    AcademicYearOut,
    AcademicYearUpdateRequest,
    SchoolCreateRequest,
    SchoolOut,
    SchoolUpdateRequest,
)


def serialize_school(school: School) -> SchoolOut:
    return SchoolOut(
        id=school.id,
        name=school.name,
        region=school.region,
        city=school.city,
        timezone=school.timezone,
        is_active=school.is_active,
        created_at=school.created_at,
    )


def serialize_year(year: AcademicYear) -> AcademicYearOut:
    return AcademicYearOut(
        id=year.id,
        school_id=year.school_id,
        name=year.name,
        starts_on=year.starts_on,
        ends_on=year.ends_on,
        is_current=year.is_current,
    )


def _require_super_admin(user: User) -> None:
    if user.role is not UserRole.SUPER_ADMIN:
        raise ForbiddenError("Управлять школами может только суперадмин", "SUPER_ADMIN_REQUIRED")


def _target_school(user: User, school_id: uuid.UUID | None) -> uuid.UUID:
    if user.role is UserRole.SUPER_ADMIN:
        if school_id is None:
            raise ValidationError("Не указана школа", "SCHOOL_REQUIRED")
        return school_id
    if user.school_id is None:
        raise ForbiddenError("Пользователь не привязан к школе", "SCHOOL_ACCESS_DENIED")
    if school_id is not None and school_id != user.school_id:
        raise ForbiddenError("Нет доступа к этой школе", "SCHOOL_ACCESS_DENIED")
    return user.school_id


async def list_schools(session: AsyncSession, user: User) -> list[SchoolOut]:
    if user.role is UserRole.SUPER_ADMIN:
        rows = await schools_repo.list_schools(session)
    elif user.school_id is not None:
        rows = await schools_repo.list_schools(session, school_id=user.school_id)
    else:
        rows = []
    return [serialize_school(row) for row in rows]


async def create_school(
    session: AsyncSession, user: User, payload: SchoolCreateRequest
) -> SchoolOut:
    _require_super_admin(user)
    school = await schools_repo.create_school(
        session,
        name=payload.name.strip(),
        region=(payload.region or "").strip() or None,
        city=(payload.city or "").strip() or None,
        timezone=payload.timezone,
        is_active=payload.is_active,
    )
    await session.commit()
    await session.refresh(school)
    return serialize_school(school)


async def update_school(
    session: AsyncSession, user: User, school_id: uuid.UUID, payload: SchoolUpdateRequest
) -> SchoolOut:
    _require_super_admin(user)
    school = await schools_repo.get_school(session, school_id)
    if school is None:
        raise NotFoundError("Школа не найдена", "SCHOOL_NOT_FOUND")

    values = payload.model_dump(exclude_unset=True)
    for field in ("name", "region", "city"):
        if field in values and values[field] is not None:
            cleaned = values[field].strip()
            if field == "name" and not cleaned:
                raise ValidationError("Название школы не может быть пустым", "VALIDATION_ERROR")
            values[field] = cleaned or None

    if values:
        await schools_repo.update_school(session, school, values=values)
        await session.commit()
        await session.refresh(school)
    return serialize_school(school)


async def list_years(
    session: AsyncSession, user: User, *, school_id: uuid.UUID | None = None
) -> list[AcademicYearOut]:
    target = user.school_id if user.role is not UserRole.SUPER_ADMIN else school_id
    if user.role is not UserRole.SUPER_ADMIN and school_id is not None:
        _target_school(user, school_id)
    rows = await schools_repo.list_years(session, school_id=target)
    return [serialize_year(row) for row in rows]


async def create_year(
    session: AsyncSession, user: User, payload: AcademicYearCreateRequest
) -> AcademicYearOut:
    target = _target_school(user, payload.school_id)
    school = await schools_repo.get_school(session, target)
    if school is None:
        raise NotFoundError("Школа не найдена", "SCHOOL_NOT_FOUND")

    try:
        year = await schools_repo.create_year(
            session,
            school_id=target,
            name=payload.name.strip(),
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            is_current=False,
        )
        if payload.is_current:
            await schools_repo.clear_current(session, school_id=target, keep_id=year.id)
            year.is_current = True
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Учебный год с таким названием уже есть", "ACADEMIC_YEAR_DUPLICATE"
        ) from exc

    await session.refresh(year)
    return serialize_year(year)


async def update_year(
    session: AsyncSession,
    user: User,
    year_id: uuid.UUID,
    payload: AcademicYearUpdateRequest,
) -> AcademicYearOut:
    year = await schools_repo.get_year(session, year_id)
    if year is None:
        raise NotFoundError("Учебный год не найден", "ACADEMIC_YEAR_NOT_FOUND")
    if user.role is not UserRole.SUPER_ADMIN and year.school_id != user.school_id:
        raise ForbiddenError("Год не из вашей школы", "SCHOOL_ACCESS_DENIED")

    values = payload.model_dump(exclude_unset=True)
    starts_on = values.get("starts_on", year.starts_on)
    ends_on = values.get("ends_on", year.ends_on)
    if ends_on <= starts_on:
        raise ValidationError(
            "Дата окончания должна быть позже даты начала", "ACADEMIC_YEAR_DATES_INVALID"
        )
    if "name" in values and values["name"] is not None:
        values["name"] = values["name"].strip()

    make_current = values.pop("is_current", None)
    try:
        if values:
            await schools_repo.update_year(session, year, values=values)
        if make_current is True:
            await schools_repo.clear_current(session, school_id=year.school_id, keep_id=year.id)
            year.is_current = True
        elif make_current is False and year.is_current:
            year.is_current = False
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Учебный год с таким названием уже есть", "ACADEMIC_YEAR_DUPLICATE"
        ) from exc

    await session.refresh(year)
    return serialize_year(year)

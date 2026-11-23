"""Control points (checkpoints): admin CRUD and the student's next deadline."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models import AcademicYear, Checkpoint, Project, User
from app.models.enums import UserRole, status_rank
from app.repositories import checkpoints as checkpoints_repo
from app.schemas.checkpoint import (
    CheckpointCreateRequest,
    CheckpointOut,
    CheckpointUpdateRequest,
    NextCheckpointOut,
)


def serialize(checkpoint: Checkpoint) -> CheckpointOut:
    return CheckpointOut(
        id=checkpoint.id,
        school_id=checkpoint.school_id,
        academic_year_id=checkpoint.academic_year_id,
        code=checkpoint.code,
        title=checkpoint.title,
        description=checkpoint.description,
        due_at=checkpoint.due_at,
        required_status=checkpoint.required_status,
        audience=checkpoint.audience,
        is_active=checkpoint.is_active,
        sort_order=checkpoint.sort_order,
    )


def to_next(checkpoint: Checkpoint, *, now: datetime) -> NextCheckpointOut:
    days_left = (checkpoint.due_at.date() - now.date()).days
    return NextCheckpointOut(
        id=checkpoint.id,
        code=checkpoint.code,
        title=checkpoint.title,
        due_at=checkpoint.due_at,
        days_left=days_left,
        required_status=checkpoint.required_status,
        overdue=checkpoint.due_at < now,
    )


async def _load_year(session: AsyncSession, year_id: uuid.UUID) -> AcademicYear:
    year = await session.get(AcademicYear, year_id)
    if year is None:
        raise ValidationError("Учебный год не найден", "ACADEMIC_YEAR_NOT_FOUND")
    return year


def _check_year_scope(user: User, year: AcademicYear) -> None:
    if user.role is UserRole.SUPER_ADMIN:
        return
    if user.school_id is None or year.school_id != user.school_id:
        raise ForbiddenError("Год не из вашей школы", "SCHOOL_ACCESS_DENIED")


def _check_due_at(year: AcademicYear, due_at: datetime) -> None:
    day = due_at.date()
    if day < year.starts_on or day > year.ends_on:
        raise ValidationError(
            "Дата контрольной точки должна быть внутри учебного года",
            "CHECKPOINT_DATE_OUT_OF_YEAR",
        )


async def list_admin(
    session: AsyncSession,
    user: User,
    *,
    academic_year_id: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
) -> list[CheckpointOut]:
    target_school = school_id if user.role is UserRole.SUPER_ADMIN else user.school_id
    rows = await checkpoints_repo.list_for_school(
        session, school_id=target_school, academic_year_id=academic_year_id
    )
    return [serialize(row) for row in rows]


async def create(
    session: AsyncSession, user: User, payload: CheckpointCreateRequest
) -> CheckpointOut:
    year = await _load_year(session, payload.academic_year_id)
    _check_year_scope(user, year)
    _check_due_at(year, payload.due_at)

    school_id = None if user.role is UserRole.SUPER_ADMIN else year.school_id
    code = payload.code.strip()
    if await checkpoints_repo.code_exists(
        session,
        school_id=school_id,
        academic_year_id=year.id,
        code=code,
    ):
        raise ConflictError("Точка с таким кодом уже есть в этом году", "CHECKPOINT_DUPLICATE")

    try:
        checkpoint = await checkpoints_repo.create(
            session,
            school_id=school_id,
            academic_year_id=year.id,
            code=code,
            title=payload.title.strip(),
            description=(payload.description or "").strip() or None,
            due_at=payload.due_at,
            required_status=payload.required_status,
            audience=payload.audience,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Точка с таким кодом уже есть в этом году", "CHECKPOINT_DUPLICATE"
        ) from exc
    return serialize(checkpoint)


async def update(
    session: AsyncSession,
    user: User,
    checkpoint_id: uuid.UUID,
    payload: CheckpointUpdateRequest,
) -> CheckpointOut:
    checkpoint = await checkpoints_repo.get_by_id(session, checkpoint_id)
    if checkpoint is None:
        raise NotFoundError("Контрольная точка не найдена", "CHECKPOINT_NOT_FOUND")

    year = await _load_year(session, checkpoint.academic_year_id)
    _check_year_scope(user, year)

    values = payload.model_dump(exclude_unset=True)
    if "due_at" in values and values["due_at"] is not None:
        _check_due_at(year, values["due_at"])
    if "code" in values and values["code"] is not None:
        values["code"] = values["code"].strip()
        if await checkpoints_repo.code_exists(
            session,
            school_id=checkpoint.school_id,
            academic_year_id=checkpoint.academic_year_id,
            code=values["code"],
            exclude_id=checkpoint.id,
        ):
            raise ConflictError("Точка с таким кодом уже есть в этом году", "CHECKPOINT_DUPLICATE")
    if "title" in values and values["title"] is not None:
        values["title"] = values["title"].strip()
    if "description" in values and values["description"] is not None:
        values["description"] = values["description"].strip() or None

    if values:
        await checkpoints_repo.update_fields(session, checkpoint.id, values=values)
        await session.commit()
        await session.refresh(checkpoint)
    return serialize(checkpoint)


async def active_for_project(
    session: AsyncSession, project: Project, *, school_id: uuid.UUID
) -> list[Checkpoint]:
    return await checkpoints_repo.list_active_for_year(
        session,
        academic_year_id=project.academic_year_id,
        school_id=school_id,
    )


async def next_for_project(
    session: AsyncSession,
    project: Project,
    *,
    school_id: uuid.UUID,
    now: datetime | None = None,
) -> NextCheckpointOut | None:
    now = now or datetime.now(UTC)
    rank = status_rank(project.status)
    checkpoints = await active_for_project(session, project, school_id=school_id)
    unmet = sorted(
        (
            checkpoint
            for checkpoint in checkpoints
            if status_rank(checkpoint.required_status) > rank
        ),
        key=lambda checkpoint: checkpoint.due_at,
    )
    if not unmet:
        return None
    return to_next(unmet[0], now=now)

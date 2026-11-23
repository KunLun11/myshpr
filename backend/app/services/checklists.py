"""Stage checklists: template CRUD, student progress and teacher verification."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models import AcademicYear, ChecklistItem, Project, User
from app.models.enums import ChecklistState, ProjectStatus, UserRole
from app.repositories import checklists as checklists_repo
from app.repositories import projects as projects_repo
from app.schemas.checklist import (
    AdminChecklistItemCreateRequest,
    AdminChecklistItemOut,
    AdminChecklistItemUpdateRequest,
    ChecklistItemStateOut,
    ChecklistOut,
    ChecklistProgressOut,
    ChecklistStageOut,
)
from app.services import project_access

STAGE_LABELS: dict[ProjectStatus, str] = {
    ProjectStatus.TOPIC_DRAFT: "Черновик темы",
    ProjectStatus.TOPIC_SUBMITTED: "Тема на проверке",
    ProjectStatus.TOPIC_APPROVED: "Тема утверждена",
    ProjectStatus.PRODUCT_DRAFT: "Выбор продукта",
    ProjectStatus.PRODUCT_DEFINED: "Продукт определён",
    ProjectStatus.IN_PROGRESS: "Работа над проектом",
    ProjectStatus.READY_FOR_DEFENSE: "Подготовка к защите",
    ProjectStatus.DEFENDED: "Защита",
}

STUDENT_ALLOWED_STATUSES = {
    ChecklistState.PENDING,
    ChecklistState.IN_PROGRESS,
    ChecklistState.DONE,
}
LOCKED_STATUSES = {ChecklistState.VERIFIED, ChecklistState.SKIPPED}
DONE_STATUSES = {ChecklistState.DONE, ChecklistState.VERIFIED}


def _is_overdue(item: ChecklistItem, state: ChecklistState, now: datetime) -> bool:
    return (
        item.is_required
        and item.due_at is not None
        and item.due_at < now
        and state not in DONE_STATUSES
    )


def _item_out(item: ChecklistItem, state, *, now: datetime) -> ChecklistItemStateOut:
    return ChecklistItemStateOut(
        id=state.id,
        checklist_item_id=item.id,
        code=item.code,
        title=item.title,
        description=item.description,
        stage=item.stage,
        is_required=item.is_required,
        due_at=item.due_at,
        status=state.status,
        overdue=_is_overdue(item, state.status, now),
        marked_at=state.marked_at,
        verified_at=state.verified_at,
        comment=state.comment,
    )


def _build_checklist(project_id: uuid.UUID, rows: list[tuple], *, now: datetime) -> ChecklistOut:
    grouped: dict[ProjectStatus, list[ChecklistItemStateOut]] = {}
    for state, item in rows:
        grouped.setdefault(item.stage, []).append(_item_out(item, state, now=now))

    stages: list[ChecklistStageOut] = []
    overdue_count = 0
    required_done_total = 0
    required_total = 0
    done_total = 0

    for stage in sorted(grouped, key=lambda value: list(ProjectStatus).index(value)):
        items = sorted(grouped[stage], key=lambda value: value.title)
        done_count = sum(1 for item in items if item.status in DONE_STATUSES)
        required_items = [item for item in items if item.is_required]
        stage_required_done = sum(1 for item in required_items if item.status in DONE_STATUSES)
        done_total += done_count
        required_done_total += stage_required_done
        required_total += len(required_items)
        overdue_count += sum(1 for item in items if item.overdue)
        stages.append(
            ChecklistStageOut(
                stage=stage,
                title=STAGE_LABELS.get(stage, stage.value),
                items=items,
                done_count=done_count,
                total_count=len(items),
                required_done=stage_required_done,
                required_total=len(required_items),
            )
        )

    percent = 0
    if required_total:
        percent = round(required_done_total / required_total * 100)
    elif done_total:
        percent = 100

    return ChecklistOut(
        project_id=project_id,
        stages=stages,
        progress=ChecklistProgressOut(
            done=required_done_total, required=required_total, percent=percent
        ),
        overdue_count=overdue_count,
    )


async def _ensure_states(
    session: AsyncSession,
    *,
    project: Project,
    school_id: uuid.UUID,
) -> list[tuple]:
    items = await checklists_repo.list_active_items(
        session, academic_year_id=project.academic_year_id, school_id=school_id
    )
    await checklists_repo.ensure_states(
        session, project_id=project.id, item_ids=[item.id for item in items]
    )
    await session.flush()
    return await checklists_repo.list_states_with_items(session, project.id)


async def get_student_checklist(session: AsyncSession, student: User) -> ChecklistOut:
    context = await project_access.load_student_project(session, student)
    rows = await _ensure_states(
        session,
        project=context.project,
        school_id=context.school_class.school_id,
    )
    return _build_checklist(context.project.id, rows, now=datetime.now(UTC))


async def get_staff_checklist(
    session: AsyncSession, user: User, project_id: uuid.UUID
) -> ChecklistOut:
    row = await project_access.load_staff_project(session, user, project_id)
    rows = await _ensure_states(session, project=row.project, school_id=row.school_id)
    return _build_checklist(project_id, rows, now=datetime.now(UTC))


async def update_student_item(
    session: AsyncSession, student: User, item_id: uuid.UUID, status: ChecklistState
) -> ChecklistItemStateOut:
    if status not in STUDENT_ALLOWED_STATUSES:
        raise ForbiddenError(
            "Ученик может только начать или отметить пункт выполненным.",
            "CHECKLIST_STATUS_FORBIDDEN",
        )

    context = await project_access.load_student_project(session, student)
    rows = await _ensure_states(
        session,
        project=context.project,
        school_id=context.school_class.school_id,
    )
    match = next((pair for pair in rows if pair[1].id == item_id), None)
    if match is None:
        raise NotFoundError("Пункт чек-листа не найден", "CHECKLIST_ITEM_NOT_FOUND")
    state, item = match
    if state.status in LOCKED_STATUSES:
        raise ConflictError(
            "Пункт уже подтверждён учителем и не меняется.", "CHECKLIST_ITEM_LOCKED"
        )

    now = datetime.now(UTC)
    state.status = status
    state.marked_by = student.id if status is not ChecklistState.PENDING else None
    state.marked_at = now if status is not ChecklistState.PENDING else None

    context.project.last_activity_at = now
    await projects_repo.add_event(
        session,
        project_id=context.project.id,
        event_type="checklist_item_changed",
        actor_id=student.id,
        payload={"item_id": str(item.id), "status": status.value},
    )
    await session.commit()
    return _item_out(item, state, now=now)


async def _transition_state(
    session: AsyncSession,
    user: User,
    state_id: uuid.UUID,
    *,
    status: ChecklistState,
    comment: str | None = None,
) -> ChecklistItemStateOut:
    pair = await checklists_repo.get_state(session, state_id)
    if pair is None:
        raise NotFoundError("Пункт чек-листа не найден", "CHECKLIST_STATE_NOT_FOUND")
    state, item = pair
    await project_access.load_staff_project(session, user, state.project_id)

    now = datetime.now(UTC)
    state.status = status
    state.verified_by = user.id
    state.verified_at = now
    if comment is not None:
        state.comment = comment.strip() or None
    event_type = "checklist_verified" if status is ChecklistState.VERIFIED else "checklist_skipped"
    await projects_repo.add_event(
        session,
        project_id=state.project_id,
        event_type=event_type,
        actor_id=user.id,
        payload={"state_id": str(state.id), "status": status.value},
    )
    await session.commit()
    return _item_out(item, state, now=now)


async def verify_state(
    session: AsyncSession, user: User, state_id: uuid.UUID, *, comment: str | None
) -> ChecklistItemStateOut:
    return await _transition_state(
        session, user, state_id, status=ChecklistState.VERIFIED, comment=comment
    )


async def skip_state(
    session: AsyncSession, user: User, state_id: uuid.UUID, *, comment: str | None
) -> ChecklistItemStateOut:
    return await _transition_state(
        session, user, state_id, status=ChecklistState.SKIPPED, comment=comment
    )


def _admin_item_out(item: ChecklistItem) -> AdminChecklistItemOut:
    return AdminChecklistItemOut(
        id=item.id,
        school_id=item.school_id,
        academic_year_id=item.academic_year_id,
        stage=item.stage,
        code=item.code,
        title=item.title,
        description=item.description,
        sort_order=item.sort_order,
        is_required=item.is_required,
        due_at=item.due_at,
        is_active=item.is_active,
    )


async def list_admin_items(
    session: AsyncSession,
    user: User,
    *,
    academic_year_id: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
) -> list[AdminChecklistItemOut]:
    target_school = school_id if user.role is UserRole.SUPER_ADMIN else user.school_id
    rows = await checklists_repo.list_items_for_school(
        session, school_id=target_school, academic_year_id=academic_year_id
    )
    return [_admin_item_out(row) for row in rows]


async def create_admin_item(
    session: AsyncSession, user: User, payload: AdminChecklistItemCreateRequest
) -> AdminChecklistItemOut:
    year = await session.get(AcademicYear, payload.academic_year_id)
    if year is None:
        raise ValidationError("Учебный год не найден", "ACADEMIC_YEAR_NOT_FOUND")

    school_id = None if user.role is UserRole.SUPER_ADMIN else user.school_id
    if school_id is not None and year.school_id != school_id:
        raise ForbiddenError("Год не из вашей школы", "SCHOOL_ACCESS_DENIED")

    try:
        item = await checklists_repo.create_item(
            session,
            school_id=school_id,
            academic_year_id=payload.academic_year_id,
            stage=payload.stage,
            code=payload.code.strip(),
            title=payload.title.strip(),
            description=(payload.description or "").strip() or None,
            sort_order=payload.sort_order,
            is_required=payload.is_required,
            due_at=payload.due_at,
            is_active=payload.is_active,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Пункт с таким кодом уже есть в этом учебном году.",
            "CHECKLIST_ITEM_DUPLICATE",
        ) from exc
    return _admin_item_out(item)


async def _load_admin_item(session: AsyncSession, user: User, item_id: uuid.UUID) -> ChecklistItem:
    item = await checklists_repo.get_item(session, item_id)
    if item is None:
        raise NotFoundError("Пункт чек-листа не найден", "CHECKLIST_ITEM_NOT_FOUND")
    if user.role is not UserRole.SUPER_ADMIN and item.school_id != user.school_id:
        raise ForbiddenError("Пункт не из вашей школы", "SCHOOL_ACCESS_DENIED")
    return item


async def update_admin_item(
    session: AsyncSession,
    user: User,
    item_id: uuid.UUID,
    payload: AdminChecklistItemUpdateRequest,
) -> AdminChecklistItemOut:
    item = await _load_admin_item(session, user, item_id)
    fields = payload.model_fields_set
    values: dict = {}
    for field in ("stage", "code", "title", "description", "sort_order", "is_required", "due_at"):
        if field in fields:
            values[field] = getattr(payload, field)
    if "is_active" in fields:
        values["is_active"] = payload.is_active
    if "code" in values and values["code"]:
        values["code"] = values["code"].strip()
    if "title" in values and values["title"]:
        values["title"] = values["title"].strip()

    if values:
        try:
            await checklists_repo.update_item(session, item.id, values=values)
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ConflictError(
                "Пункт с таким кодом уже есть в этом учебном году.",
                "CHECKLIST_ITEM_DUPLICATE",
            ) from exc
    else:
        await session.commit()
    refreshed = await checklists_repo.get_item(session, item.id)
    if refreshed is None:  # pragma: no cover
        raise NotFoundError("Пункт чек-листа не найден", "CHECKLIST_ITEM_NOT_FOUND")
    return _admin_item_out(refreshed)


async def deactivate_admin_item(session: AsyncSession, user: User, item_id: uuid.UUID) -> None:
    item = await _load_admin_item(session, user, item_id)
    await checklists_repo.update_item(session, item.id, values={"is_active": False})
    await session.commit()

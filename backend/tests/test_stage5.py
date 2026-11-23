"""Stage 5 integration tests: dashboard, checkpoints, notifications, reminders."""

import uuid
from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Checkpoint, Notification, Project, ProjectChecklistState
from app.models.enums import (
    ChecklistState,
    NotificationType,
    ProjectStatus,
    UserRole,
)
from app.repositories import notifications as notifications_repo
from app.services import status as status_service
from app.services.reminders import run_daily_reminders
from tests.factories import (
    create_checklist_item,
    create_checkpoint,
    create_class,
    create_project,
    create_school,
    create_student,
    create_user,
    create_year,
)


async def _setup(session: AsyncSession):
    school = await create_school(session)
    year = await create_year(session, school, is_current=True)
    teacher = await create_user(
        session, school, UserRole.TEACHER, password="password123", full_name="Учитель Один"
    )
    other_teacher = await create_user(
        session, school, UserRole.TEACHER, password="password123", full_name="Учитель Два"
    )
    admin = await create_user(
        session, school, UserRole.SCHOOL_ADMIN, password="password123", full_name="Админ"
    )
    klass = await create_class(session, school, year, label="9А", curator_id=teacher.id)
    student = await create_student(
        session, school, klass, password="password123", full_name="Анна Смирнова"
    )
    student_two = await create_student(
        session, school, klass, password="password123", full_name="Иван Петров"
    )
    project = await create_project(
        session,
        student,
        year,
        klass,
        status=ProjectStatus.IDEA,
        last_activity_at=datetime.now(UTC) - timedelta(days=20),
    )
    project_two = await create_project(
        session,
        student_two,
        year,
        klass,
        status=ProjectStatus.TOPIC_APPROVED,
        last_activity_at=datetime.now(UTC) - timedelta(days=1),
    )
    return (
        school,
        year,
        teacher,
        other_teacher,
        admin,
        klass,
        student,
        student_two,
        project,
        project_two,
    )


async def _login(client: AsyncClient, email: str) -> None:
    client.cookies.clear()
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200, response.text


def _project(status: ProjectStatus, *, inactive_days: float | None = 0) -> Project:
    now = datetime.now(UTC)
    project = Project(
        student_id=uuid.uuid4(),
        academic_year_id=uuid.uuid4(),
        class_id=uuid.uuid4(),
        status=status,
        last_activity_at=now - timedelta(days=inactive_days or 0),
    )
    return project


def _checkpoint(
    *,
    due_in_days: int,
    required_status: ProjectStatus = ProjectStatus.TOPIC_APPROVED,
    title: str = "Точка",
) -> Checkpoint:
    return Checkpoint(
        school_id=None,
        academic_year_id=uuid.uuid4(),
        code=f"cp-{due_in_days}-{title}",
        title=title,
        due_at=datetime.now(UTC) + timedelta(days=due_in_days),
        required_status=required_status,
        is_active=True,
        sort_order=10,
    )


def _context(*, checkpoints=None, inactive_days=None, **overrides) -> status_service.StatusContext:
    data = {
        "now": datetime.now(UTC),
        "year_starts_on": date(2026, 9, 1),
        "checkpoints": checkpoints or [],
        "inactive_days": inactive_days,
        "checklist_overdue": 0,
        "checklist_stalled": False,
        "has_final_file": True,
        "review_waiting_since": None,
    }
    data.update(overrides)
    return status_service.StatusContext(**data)


def _codes(result: status_service.StatusResult) -> set[str]:
    return {reason.code for reason in result.reasons}


def test_status_no_project_and_year_start() -> None:
    started = status_service.evaluate(None, _context())
    assert started.color is status_service.TrafficLight.RED
    assert _codes(started) == {"NO_PROJECT"}

    future = status_service.evaluate(None, _context(year_starts_on=date(2027, 9, 1)))
    assert future.color is status_service.TrafficLight.GREEN
    assert _codes(future) == {"YEAR_NOT_STARTED"}


def test_status_inactivity_boundaries() -> None:
    project = _project(ProjectStatus.IN_PROGRESS)
    seven = status_service.evaluate(project, _context(inactive_days=7))
    assert seven.color is status_service.TrafficLight.YELLOW
    assert "NO_ACTIVITY_7D" in _codes(seven)

    fourteen = status_service.evaluate(project, _context(inactive_days=14))
    assert fourteen.color is status_service.TrafficLight.RED
    assert "NO_ACTIVITY_14D" in _codes(fourteen)

    fresh = status_service.evaluate(project, _context(inactive_days=1))
    assert fresh.color is status_service.TrafficLight.GREEN
    assert _codes(fresh) == {"ON_TRACK"}


def test_status_checkpoints_and_checklist() -> None:
    project = _project(ProjectStatus.TOPIC_DRAFT)
    soon = status_service.evaluate(project, _context(checkpoints=[_checkpoint(due_in_days=5)]))
    assert soon.color is status_service.TrafficLight.YELLOW
    assert "CHECKPOINT_SOON" in _codes(soon)

    overdue = status_service.evaluate(project, _context(checkpoints=[_checkpoint(due_in_days=-1)]))
    assert overdue.color is status_service.TrafficLight.RED
    assert "CHECKPOINT_OVERDUE" in _codes(overdue)

    checklist = status_service.evaluate(project, _context(checklist_overdue=2))
    assert checklist.color is status_service.TrafficLight.RED
    assert "CHECKLIST_OVERDUE" in _codes(checklist)

    stalled = status_service.evaluate(project, _context(checklist_stalled=True))
    assert stalled.color is status_service.TrafficLight.YELLOW
    assert "CHECKLIST_STALLED" in _codes(stalled)


def test_status_final_file_and_review_waiting() -> None:
    project = _project(ProjectStatus.IN_PROGRESS)
    ready = _checkpoint(
        due_in_days=10,
        required_status=ProjectStatus.READY_FOR_DEFENSE,
        title="Готовность к защите",
    )
    result = status_service.evaluate(project, _context(checkpoints=[ready], has_final_file=False))
    assert result.color is status_service.TrafficLight.YELLOW
    assert "NO_FINAL_FILE" in _codes(result)

    submitted = _project(ProjectStatus.TOPIC_SUBMITTED)
    waiting = status_service.evaluate(
        submitted,
        _context(review_waiting_since=datetime.now(UTC) - timedelta(days=8)),
    )
    assert waiting.color is status_service.TrafficLight.YELLOW
    assert "REVIEW_WAITING" in _codes(waiting)


async def test_dashboard_summary_sorting_and_filters(session, client) -> None:
    _, _, teacher, _, _, klass, _, _, _, _ = await _setup(session)
    await _login(client, teacher.email)
    response = await client.get(f"/api/v1/teacher/classes/{klass.id}/dashboard")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["summary"]["total"] == 2
    assert body["summary"]["red"] >= 1
    assert body["students"][0]["color"] == "red"

    filtered = await client.get(
        f"/api/v1/teacher/classes/{klass.id}/dashboard", params={"color": "red"}
    )
    assert filtered.status_code == 200
    assert all(item["color"] == "red" for item in filtered.json()["students"])

    searched = await client.get(
        f"/api/v1/teacher/classes/{klass.id}/dashboard", params={"q": "Иван"}
    )
    assert [item["student_full_name"] for item in searched.json()["students"]] == ["Иван Петров"]


async def test_dashboard_denies_foreign_teacher(session, client) -> None:
    _, _, _, other_teacher, _, klass, _, _, _, _ = await _setup(session)
    await _login(client, other_teacher.email)
    response = await client.get(f"/api/v1/teacher/classes/{klass.id}/dashboard")
    assert response.status_code == 403
    assert response.json()["code"] == "CLASS_ACCESS_DENIED"


async def test_checkpoint_crud_validation_and_student_next_point(session, client) -> None:
    school, year, _, _, admin, _, student, _, project, _ = await _setup(session)
    await _login(client, admin.email)

    payload = {
        "academic_year_id": str(year.id),
        "code": "midway",
        "title": "Промежуточная проверка",
        "due_at": datetime(2027, 3, 1, 9, tzinfo=UTC).isoformat(),
        "required_status": ProjectStatus.TOPIC_APPROVED.value,
    }
    created = await client.post("/api/v1/admin/checkpoints", json=payload)
    assert created.status_code == 201, created.text
    checkpoint_id = created.json()["id"]

    duplicate = await client.post("/api/v1/admin/checkpoints", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "CHECKPOINT_DUPLICATE"

    outside = await client.post(
        "/api/v1/admin/checkpoints",
        json={**payload, "code": "outside", "due_at": datetime(2028, 3, 1, tzinfo=UTC).isoformat()},
    )
    assert outside.status_code == 422
    assert outside.json()["code"] == "CHECKPOINT_DATE_OUT_OF_YEAR"

    updated = await client.patch(
        f"/api/v1/admin/checkpoints/{checkpoint_id}", json={"is_active": False}
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["is_active"] is False

    await create_checkpoint(
        session,
        year,
        school_id=school.id,
        code="nearest",
        title="Ближайшая",
        due_at=datetime.now(UTC) + timedelta(days=12),
        required_status=ProjectStatus.TOPIC_APPROVED,
    )
    await session.flush()

    await _login(client, student.email)
    project_response = await client.get("/api/v1/me/project")
    assert project_response.status_code == 200, project_response.text
    assert project_response.json()["next_checkpoint"]["title"] == "Ближайшая"


async def test_notifications_list_and_mark_read(session, client) -> None:
    _, _, _, _, _, _, student, other_student, project, _ = await _setup(session)
    await notifications_repo.create_in_app(
        session,
        user_id=student.id,
        type=NotificationType.INACTIVITY,
        title="Пора вернуться",
        body="Тестовое уведомление",
        dedupe_key="test:notify:1",
        project_id=project.id,
    )
    foreign = await notifications_repo.create_in_app(
        session,
        user_id=other_student.id,
        type=NotificationType.INACTIVITY,
        title="Чужое",
        body="Не показывать",
        dedupe_key="test:notify:foreign",
    )
    assert foreign is True

    await _login(client, student.email)
    listing = await client.get("/api/v1/me/notifications")
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["unread_count"] == 1
    assert [item["title"] for item in body["items"]] == ["Пора вернуться"]

    notification_id = body["items"][0]["id"]
    marked = await client.post(f"/api/v1/me/notifications/{notification_id}/read")
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    listing = await client.get("/api/v1/me/notifications")
    assert listing.json()["unread_count"] == 0

    foreign_id = (
        await session.execute(
            select(Notification.id).where(Notification.user_id == other_student.id)
        )
    ).scalar_one()
    denied = await client.post(f"/api/v1/me/notifications/{foreign_id}/read")
    assert denied.status_code == 404


async def test_reminders_are_idempotent(session) -> None:
    school, year, teacher, _, _, klass, student, _, project, _ = await _setup(session)
    now = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
    project.last_activity_at = now - timedelta(days=20)
    checkpoint = await create_checkpoint(
        session,
        year,
        school_id=school.id,
        code="soon",
        title="Скоро",
        due_at=now + timedelta(days=3),
        required_status=ProjectStatus.TOPIC_APPROVED,
    )
    item = await create_checklist_item(
        session,
        year,
        code="deadline",
        title="Сдать черновик",
        due_at=now + timedelta(days=2),
    )
    session.add(
        ProjectChecklistState(
            project_id=project.id,
            checklist_item_id=item.id,
            status=ChecklistState.PENDING,
        )
    )
    await session.flush()

    first = await run_daily_reminders(session, now=now)
    assert first.created > 0

    student_notifications = (
        (await session.execute(select(Notification).where(Notification.user_id == student.id)))
        .scalars()
        .all()
    )
    types = {notification.type for notification in student_notifications}
    assert NotificationType.INACTIVITY in types
    assert NotificationType.CHECKPOINT_DUE in types
    assert NotificationType.CHECKLIST_DUE in types
    assert any(
        notification.checkpoint_id == checkpoint.id for notification in student_notifications
    )

    teacher_notifications = (
        (await session.execute(select(Notification).where(Notification.user_id == teacher.id)))
        .scalars()
        .all()
    )
    assert any(
        notification.type is NotificationType.TEACHER_DIGEST
        for notification in teacher_notifications
    )

    before = (await session.execute(select(func.count(Notification.id)))).scalar_one()
    second = await run_daily_reminders(session, now=now)
    assert second.created == 0
    after = (await session.execute(select(func.count(Notification.id)))).scalar_one()
    assert after == before

"""Integration tests for the student topic wizard and teacher review."""

import uuid

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ProjectEvent, Topic, TopicSubmission
from app.models.enums import ProjectStatus, TopicSubmissionStatus, UserRole
from app.services.topic_check import normalize_title
from tests.factories import (
    create_class,
    create_interest_area,
    create_school,
    create_student,
    create_topic,
    create_user,
    create_year,
)

GOOD_TITLE = "Сравнение качества воды в реке Москве за 2024 год"
GOOD_QUESTION = "Как качество воды в реке Москве меняется за последний год?"
BROAD_TITLE = "Влияние и роль развития"
BROAD_QUESTION = "Как влияет интернет на людей?"


async def _setup(session: AsyncSession):
    school = await create_school(session)
    year = await create_year(session, school, is_current=True)
    teacher = await create_user(
        session, school, UserRole.TEACHER, password="password123", full_name="Учитель Один"
    )
    klass = await create_class(session, school, year, label="9А", curator_id=teacher.id)
    student = await create_student(
        session, school, klass, password="password123", full_name="Анна Смирнова"
    )
    area = await create_interest_area(session, name="Экология")
    return school, year, teacher, klass, student, area


async def _login(client: AsyncClient, email: str) -> None:
    client.cookies.clear()
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200, response.text


async def _create_project(client: AsyncClient, area_id: uuid.UUID) -> None:
    response = await client.patch(
        "/api/v1/me/project",
        json={"interest_area_id": str(area_id), "research_question": GOOD_QUESTION},
    )
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# Project draft
# ---------------------------------------------------------------------------


async def test_project_is_created_lazily_and_only_once(session, client) -> None:
    _, _, _, _, student, area = await _setup(session)
    await _login(client, student.email)

    response = await client.get("/api/v1/me/project")
    assert response.status_code == 200
    assert response.json() is None

    response = await client.patch("/api/v1/me/project", json={"interest_area_id": str(area.id)})
    assert response.status_code == 200, response.text
    body = response.json()["project"]
    assert body["status"] == ProjectStatus.TOPIC_DRAFT.value
    assert body["interest_area"]["id"] == str(area.id)

    response = await client.patch(
        "/api/v1/me/project",
        json={"research_question": GOOD_QUESTION, "topic_title": GOOD_TITLE},
    )
    assert response.status_code == 200, response.text
    project = response.json()["project"]
    assert project["research_question"] == GOOD_QUESTION
    assert project["topic"]["title"] == GOOD_TITLE
    assert project["topic"]["normalized_title"] == normalize_title(GOOD_TITLE)

    count = await session.scalar(
        select(func.count(Project.id)).where(Project.student_id == student.id)
    )
    assert count == 1

    events = (
        await session.execute(select(ProjectEvent).where(ProjectEvent.project_id == project["id"]))
    ).scalars()
    event_types = {event.event_type for event in events}
    assert "project_created" in event_types
    assert "topic_draft_saved" not in event_types  # drafts are not separate events


async def test_patch_with_unknown_interest_area_is_rejected(session, client) -> None:
    _, _, _, _, student, _ = await _setup(session)
    await _login(client, student.email)

    response = await client.patch(
        "/api/v1/me/project", json={"interest_area_id": str(uuid.uuid4())}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INTEREST_AREA"


async def test_check_returns_errors_and_warnings_without_saving(session, client) -> None:
    _, _, _, _, student, area = await _setup(session)
    await _login(client, student.email)
    await _create_project(client, area.id)

    response = await client.post(
        "/api/v1/me/project/topic/check",
        json={"title": GOOD_TITLE, "research_question": GOOD_QUESTION},
    )
    assert response.status_code == 200, response.text
    check = response.json()
    assert check["can_submit"] is True
    assert check["errors"] == []
    assert check["duplicate"]["level"] == "ok"
    assert check["broadness"]["level"] == "ok"

    response = await client.post(
        "/api/v1/me/project/topic/check",
        json={"title": BROAD_TITLE, "research_question": BROAD_QUESTION},
    )
    assert response.status_code == 200, response.text
    check = response.json()
    assert check["can_submit"] is False
    assert check["broadness"]["level"] == "block"
    assert check["errors"]

    stored = await session.scalar(
        select(func.count(TopicSubmission.id)).where(
            TopicSubmission.author_student_id == student.id
        )
    )
    assert stored == 0


async def test_duplicate_check_finds_registry_and_pending(session, client) -> None:
    school, year, _, _, student, area = await _setup(session)
    await create_topic(
        session,
        school,
        year,
        title=GOOD_TITLE,
        normalized_title=normalize_title(GOOD_TITLE),
    )
    await _login(client, student.email)
    await _create_project(client, area.id)

    response = await client.post(
        "/api/v1/me/project/topic/check",
        json={"title": GOOD_TITLE, "research_question": GOOD_QUESTION},
    )
    assert response.status_code == 200, response.text
    duplicate = response.json()["duplicate"]
    assert duplicate["level"] == "block"
    assert duplicate["exact"] is True
    assert duplicate["matches"][0]["source"] == "registry"


# ---------------------------------------------------------------------------
# Submit and review
# ---------------------------------------------------------------------------


async def test_full_topic_cycle_submit_approve_and_registry(session, client) -> None:
    _, year, teacher, _, student, area = await _setup(session)
    await _login(client, student.email)
    await _create_project(client, area.id)

    response = await client.post(
        "/api/v1/me/project/topic/submit",
        json={"title": GOOD_TITLE, "research_question": GOOD_QUESTION},
    )
    assert response.status_code == 200, response.text
    project = response.json()
    assert project["status"] == ProjectStatus.TOPIC_SUBMITTED.value
    assert project["topic"]["status"] == TopicSubmissionStatus.SUBMITTED.value

    await _login(client, teacher.email)
    response = await client.get("/api/v1/teacher/submissions")
    assert response.status_code == 200, response.text
    queue = response.json()
    assert len(queue) == 1
    assert queue[0]["title"] == GOOD_TITLE
    assert queue[0]["student_full_name"] == "Анна Смирнова"

    response = await client.post(f"/api/v1/teacher/submissions/{queue[0]['id']}/approve", json={})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == TopicSubmissionStatus.APPROVED.value

    await _login(client, student.email)
    response = await client.get("/api/v1/me/project")
    project = response.json()
    assert project["status"] == ProjectStatus.TOPIC_APPROVED.value
    assert project["topic"]["status"] == TopicSubmissionStatus.APPROVED.value
    assert project["topic_approved_at"] is not None

    topic = await session.scalar(
        select(Topic).where(Topic.academic_year_id == year.id, Topic.title == GOOD_TITLE)
    )
    assert topic is not None
    assert topic.normalized_title == normalize_title(GOOD_TITLE)

    await _login(client, teacher.email)
    response = await client.get("/api/v1/teacher/topics")
    assert response.status_code == 200, response.text
    assert [item["title"] for item in response.json()] == [GOOD_TITLE]


async def test_submit_rejects_duplicate_title(session, client) -> None:
    school, year, _, _, student, area = await _setup(session)
    await create_topic(
        session,
        school,
        year,
        title=GOOD_TITLE,
        normalized_title=normalize_title(GOOD_TITLE),
    )
    await _login(client, student.email)
    await _create_project(client, area.id)

    response = await client.post(
        "/api/v1/me/project/topic/submit",
        json={"title": GOOD_TITLE, "research_question": GOOD_QUESTION},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "TOPIC_DUPLICATE"


async def test_submit_rejects_broad_topic(session, client) -> None:
    _, _, _, _, student, area = await _setup(session)
    await _login(client, student.email)
    await _create_project(client, area.id)

    response = await client.post(
        "/api/v1/me/project/topic/submit",
        json={"title": BROAD_TITLE, "research_question": GOOD_QUESTION},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "TOPIC_TOO_BROAD"


async def test_reject_returns_student_to_editing_and_allows_resubmit(session, client) -> None:
    _, _, teacher, _, student, area = await _setup(session)
    await _login(client, student.email)
    await _create_project(client, area.id)

    response = await client.post(
        "/api/v1/me/project/topic/submit",
        json={"title": GOOD_TITLE, "research_question": GOOD_QUESTION},
    )
    assert response.status_code == 200, response.text

    await _login(client, teacher.email)
    queue = (await client.get("/api/v1/teacher/submissions")).json()
    response = await client.post(
        f"/api/v1/teacher/submissions/{queue[0]['id']}/reject",
        json={"comment": "Уточните, какой участок реки вы исследуете."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == TopicSubmissionStatus.REJECTED.value

    await _login(client, student.email)
    project = (await client.get("/api/v1/me/project")).json()
    assert project["status"] == ProjectStatus.TOPIC_DRAFT.value
    assert "участок реки" in project["topic"]["review_comment"]

    response = await client.patch(
        "/api/v1/me/project",
        json={"topic_title": "Сравнение качества воды в реке Москве у Южного порта за 2024 год"},
    )
    assert response.status_code == 200, response.text

    response = await client.post(
        "/api/v1/me/project/topic/submit",
        json={},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == ProjectStatus.TOPIC_SUBMITTED.value


async def test_approve_requires_comment_for_warnings(session, client) -> None:
    _, _, teacher, _, student, area = await _setup(session)
    await _login(client, student.email)
    await _create_project(client, area.id)

    warn_title = "Влияние шума на здоровье школьников в Москве"
    response = await client.post(
        "/api/v1/me/project/topic/submit",
        json={"title": warn_title, "research_question": GOOD_QUESTION},
    )
    assert response.status_code == 200, response.text

    await _login(client, teacher.email)
    queue = (await client.get("/api/v1/teacher/submissions")).json()
    assert queue[0]["broadness_level"] == "warn"

    response = await client.post(f"/api/v1/teacher/submissions/{queue[0]['id']}/approve", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "REVIEW_COMMENT_REQUIRED"

    response = await client.post(
        f"/api/v1/teacher/submissions/{queue[0]['id']}/approve",
        json={"comment": "Тема сужена по месту и группе, можно утверждать."},
    )
    assert response.status_code == 200, response.text


async def test_teacher_cannot_review_other_class_submission(session, client) -> None:
    school, year, teacher, _, student, area = await _setup(session)
    other_teacher = await create_user(
        session, school, UserRole.TEACHER, password="password123", full_name="Другой учитель"
    )
    other_class = await create_class(session, school, year, label="9Б", curator_id=other_teacher.id)
    other_student = await create_student(
        session, school, other_class, password="password123", full_name="Другой ученик"
    )
    other_area = await create_interest_area(session, name="Техника")

    await _login(client, other_student.email)
    await _create_project(client, other_area.id)
    response = await client.post(
        "/api/v1/me/project/topic/submit",
        json={"title": GOOD_TITLE, "research_question": GOOD_QUESTION},
    )
    assert response.status_code == 200, response.text

    await _login(client, other_teacher.email)
    other_queue = (await client.get("/api/v1/teacher/submissions")).json()
    assert len(other_queue) == 1

    # The original teacher curates another class and must not see or review it.
    await _login(client, teacher.email)
    own_queue = (await client.get("/api/v1/teacher/submissions")).json()
    assert own_queue == []

    response = await client.post(
        f"/api/v1/teacher/submissions/{other_queue[0]['id']}/approve", json={}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "SUBMISSION_ACCESS_DENIED"

    # Keep the fixture student referenced so the setup is explicit.
    assert student.id != other_student.id


async def test_student_cannot_use_teacher_queue(session, client) -> None:
    _, _, _, _, student, _ = await _setup(session)
    await _login(client, student.email)

    response = await client.get("/api/v1/teacher/submissions")
    assert response.status_code == 403
    assert response.json()["code"] == "ROLE_FORBIDDEN"

"""Stage 4 integration tests: product, files, comments and checklists."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, ProjectChecklistState, ProjectEvent
from app.models.enums import (
    ChecklistState,
    NotificationType,
    ProjectStatus,
    UserRole,
)
from app.services import files as files_service
from app.services.product_guide import get_product_state
from tests.factories import (
    create_checklist_item,
    create_class,
    create_interest_area,
    create_product_category,
    create_project,
    create_school,
    create_student,
    create_user,
    create_year,
)

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
LONG_DESCRIPTION = (
    "Я создам действующую модель фильтрации воды, соберу данные об эффективности "
    "очистки и покажу на защите, как модель отвечает на исследовательский вопрос."
)


async def _setup(session: AsyncSession, *, approved: bool = True):
    school = await create_school(session)
    year = await create_year(session, school, is_current=True)
    teacher = await create_user(
        session, school, UserRole.TEACHER, password="password123", full_name="Учитель Один"
    )
    klass = await create_class(session, school, year, label="9А", curator_id=teacher.id)
    student = await create_student(
        session, school, klass, password="password123", full_name="Анна Смирнова"
    )
    other_student = await create_student(
        session, school, klass, password="password123", full_name="Иван Петров"
    )
    area = await create_interest_area(session, name="Экология")
    category = await create_product_category(session)
    project = await create_project(
        session,
        student,
        year,
        klass,
        status=ProjectStatus.TOPIC_APPROVED if approved else ProjectStatus.TOPIC_DRAFT,
        topic_approved_at=datetime.now(UTC) if approved else None,
        interest_area_id=area.id,
        research_question="Как качество воды меняется за год?",
    )
    return school, year, teacher, klass, student, other_student, area, category, project


async def _login(client: AsyncClient, email: str) -> None:
    client.cookies.clear()
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200, response.text


async def test_product_categories_hide_inactive_and_return_guidance(session, client) -> None:
    _, _, _, _, student, _, _, active, _ = await _setup(session)
    await create_product_category(session, name="Отключённая", is_active=False)
    await _login(client, student.email)

    response = await client.get("/api/v1/reference/product-categories")
    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["name"] for item in body] == [active.name]
    assert body[0]["guidance"]["examples"] == ["Пример продукта"]
    assert body[0]["guidance"]["must_have"] == ["Методика"]


async def test_product_requires_approved_topic_and_updates_status(session, client) -> None:
    _, _, _, _, student, _, _, category, project = await _setup(session, approved=False)
    await _login(client, student.email)

    payload = {
        "product_category_id": str(category.id),
        "product_description": LONG_DESCRIPTION,
        "defense_plan": "Покажу модель и результаты измерений",
        "audience": "Ученики и учителя школы",
    }
    response = await client.patch("/api/v1/me/project/product", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "TOPIC_NOT_APPROVED"

    project.status = ProjectStatus.TOPIC_APPROVED
    project.topic_approved_at = datetime.now(UTC)
    await session.flush()

    response = await client.patch("/api/v1/me/project/product", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == ProjectStatus.PRODUCT_DEFINED.value
    assert body["category"]["id"] == str(category.id)
    assert body["brief"]["defense_plan"].startswith("Покажу")
    assert body["product_defined_at"] is not None

    await session.refresh(project)
    assert project.status is ProjectStatus.PRODUCT_DEFINED
    assert project.product_defined_at is not None
    events = (
        (
            await session.execute(
                select(ProjectEvent).where(
                    ProjectEvent.project_id == project.id,
                    ProjectEvent.event_type == "product_defined",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1

    short = {**payload, "product_description": "Слишком коротко"}
    response = await client.patch("/api/v1/me/project/product", json=short)
    assert response.status_code == 422
    assert response.json()["code"] == "PRODUCT_DESCRIPTION_INVALID"


async def test_product_state_serialization(session) -> None:
    _, _, _, _, student, _, _, category, project = await _setup(session)
    project.product_category_id = category.id
    project.product_description = LONG_DESCRIPTION
    project.product_brief = {"audience": "Школа"}
    await session.flush()

    state = await get_product_state(session, student)
    assert state.category is not None
    assert state.category.id == category.id
    assert state.brief is not None
    assert state.brief.audience == "Школа"


async def test_file_upload_download_delete_and_access(session, client) -> None:
    _, _, teacher, _, student, other_student, _, _, project = await _setup(session)
    await _login(client, student.email)

    response = await client.post(
        "/api/v1/me/project/files",
        files={"file": ("Моя работа.pdf", PDF_BYTES, "application/pdf")},
        data={"kind": "final_work"},
    )
    assert response.status_code == 201, response.text
    uploaded = response.json()
    assert uploaded["original_name"] == "Моя работа.pdf"
    assert uploaded["mime_type"] == "application/pdf"
    assert uploaded["status"] == "available"

    listing = await client.get("/api/v1/me/project/files")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    download = await client.get(f"/api/v1{uploaded['download_url']}")
    assert download.status_code == 200
    assert download.content == PDF_BYTES
    assert "attachment" in download.headers["content-disposition"]

    await _login(client, other_student.email)
    denied = await client.get(f"/api/v1{uploaded['download_url']}")
    assert denied.status_code == 403

    await _login(client, teacher.email)
    allowed = await client.get(f"/api/v1{uploaded['download_url']}")
    assert allowed.status_code == 200

    await _login(client, student.email)
    deleted = await client.delete(f"/api/v1/me/project/files/{uploaded['id']}")
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/me/project/files")).json() == []
    assert (await client.get(f"/api/v1{uploaded['download_url']}")).status_code == 404

    events = (
        (await session.execute(select(ProjectEvent).where(ProjectEvent.project_id == project.id)))
        .scalars()
        .all()
    )
    assert {"file_uploaded", "file_deleted"} <= {event.event_type for event in events}


async def test_file_rejects_wrong_type_signature_and_duplicate(session, client) -> None:
    _, _, _, _, student, _, _, _, _ = await _setup(session)
    await _login(client, student.email)

    wrong_type = await client.post(
        "/api/v1/me/project/files",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert wrong_type.status_code == 422
    assert wrong_type.json()["code"] == "FILE_TYPE_NOT_ALLOWED"

    wrong_signature = await client.post(
        "/api/v1/me/project/files",
        files={"file": ("image.png", b"not a png", "image/png")},
    )
    assert wrong_signature.status_code == 422
    assert wrong_signature.json()["code"] == "FILE_SIGNATURE_INVALID"

    first = await client.post(
        "/api/v1/me/project/files",
        files={"file": ("work.pdf", PDF_BYTES, "application/pdf")},
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/me/project/files",
        files={"file": ("copy.pdf", PDF_BYTES, "application/pdf")},
    )
    assert second.status_code == 409
    assert second.json()["code"] == "DUPLICATE_FILE"


async def test_file_size_limit(session, client, monkeypatch) -> None:
    _, _, _, _, student, _, _, _, _ = await _setup(session)
    await _login(client, student.email)

    settings = files_service.get_settings()
    tiny = settings.model_copy(update={"MAX_UPLOAD_BYTES": 8})
    monkeypatch.setattr(files_service, "get_settings", lambda: tiny)

    response = await client.post(
        "/api/v1/me/project/files",
        files={"file": ("work.pdf", PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "FILE_TOO_LARGE"


async def test_comments_visibility_notification_and_scoping(session, client) -> None:
    school, year, teacher, klass, student, _, _, _, project = await _setup(session)
    foreign_teacher = await create_user(
        session, school, UserRole.TEACHER, password="password123", full_name="Чужой учитель"
    )
    await session.flush()

    await _login(client, teacher.email)
    public = await client.post(
        f"/api/v1/teacher/projects/{project.id}/comments",
        json={"body": "Проверьте список источников", "visibility": "student_visible"},
    )
    assert public.status_code == 201, public.text

    private = await client.post(
        f"/api/v1/teacher/projects/{project.id}/comments",
        json={"body": "Внутренняя заметка", "visibility": "teachers_only"},
    )
    assert private.status_code == 201, private.text

    await _login(client, student.email)
    student_view = await client.get("/api/v1/me/project/comments")
    assert student_view.status_code == 200
    bodies = [item["body"] for item in student_view.json()]
    assert bodies == ["Проверьте список источников"]

    notifications = (
        (
            await session.execute(
                select(Notification).where(
                    Notification.user_id == student.id,
                    Notification.type == NotificationType.NEW_COMMENT,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(notifications) == 1

    await _login(client, foreign_teacher.email)
    denied = await client.post(
        f"/api/v1/teacher/projects/{project.id}/comments",
        json={"body": "Не мой класс", "visibility": "student_visible"},
    )
    assert denied.status_code == 403


async def test_checklist_lazy_states_progress_and_verification(session, client) -> None:
    school, year, teacher, _, student, _, _, _, project = await _setup(session)
    overdue_item = await create_checklist_item(
        session,
        year,
        title="Собрать источники",
        code="collect_sources",
        due_at=datetime.now(UTC) - timedelta(days=1),
    )
    second_item = await create_checklist_item(
        session, year, title="Провести исследование", code="do_research"
    )

    await _login(client, student.email)
    first = await client.get("/api/v1/me/project/checklist")
    assert first.status_code == 200, first.text
    checklist = first.json()
    assert checklist["progress"]["done"] == 0
    assert checklist["progress"]["required"] == 2
    assert checklist["overdue_count"] == 1
    assert len(checklist["stages"][0]["items"]) == 2

    count = await session.scalar(
        select(func.count(ProjectChecklistState.id)).where(
            ProjectChecklistState.project_id == project.id
        )
    )
    assert count == 2

    # Re-reading is idempotent.
    await client.get("/api/v1/me/project/checklist")
    count = await session.scalar(
        select(func.count(ProjectChecklistState.id)).where(
            ProjectChecklistState.project_id == project.id
        )
    )
    assert count == 2

    response = await client.patch(
        f"/api/v1/me/project/checklist/{overdue_item.id}", json={"status": "done"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == ChecklistState.DONE.value

    forbidden = await client.patch(
        f"/api/v1/me/project/checklist/{second_item.id}", json={"status": "verified"}
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "CHECKLIST_STATUS_FORBIDDEN"

    await _login(client, teacher.email)
    staff = await client.get(f"/api/v1/teacher/projects/{project.id}/checklist")
    assert staff.status_code == 200
    states = {item["code"]: item for stage in staff.json()["stages"] for item in stage["items"]}
    verified = await client.post(
        f"/api/v1/teacher/checklist-states/{states['collect_sources']['id']}/verify",
        json={"comment": "Источники достаточно"},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == ChecklistState.VERIFIED.value

    await _login(client, student.email)
    final = await client.get("/api/v1/me/project/checklist")
    assert final.json()["progress"]["percent"] == 50


async def test_full_work_flow_upload_checklist_and_comment(session, client) -> None:
    _, year, teacher, _, student, _, _, _, project = await _setup(session)
    item = await create_checklist_item(
        session, year, title="Загрузить итоговый файл", code="upload_final"
    )

    await _login(client, student.email)
    uploaded = await client.post(
        "/api/v1/me/project/files",
        files={"file": ("final.pdf", PDF_BYTES, "application/pdf")},
        data={"kind": "final_work"},
    )
    assert uploaded.status_code == 201, uploaded.text

    checklist = (await client.get("/api/v1/me/project/checklist")).json()
    state = next(
        entry
        for stage in checklist["stages"]
        for entry in stage["items"]
        if entry["checklist_item_id"] == str(item.id)
    )
    marked = await client.patch(f"/api/v1/me/project/checklist/{item.id}", json={"status": "done"})
    assert marked.status_code == 200
    assert marked.json()["id"] == state["id"]

    await _login(client, teacher.email)
    files = await client.get(f"/api/v1/teacher/projects/{project.id}/files")
    assert [entry["original_name"] for entry in files.json()] == ["final.pdf"]
    comment = await client.post(
        f"/api/v1/teacher/projects/{project.id}/comments",
        json={"body": "Файл принят, проверьте оформление", "visibility": "student_visible"},
    )
    assert comment.status_code == 201, comment.text

    await _login(client, student.email)
    comments = (await client.get("/api/v1/me/project/comments")).json()
    assert comments[-1]["body"] == "Файл принят, проверьте оформление"
    final = (await client.get("/api/v1/me/project/checklist")).json()
    assert final["progress"]["percent"] == 100


async def test_admin_checklist_template_crud(session, client) -> None:
    school, year, _, _, _, _, _, _, _ = await _setup(session)
    admin = await create_user(
        session, school, UserRole.SCHOOL_ADMIN, password="password123", full_name="Админ"
    )
    await _login(client, admin.email)

    created = await client.post(
        "/api/v1/admin/checklist-items",
        json={
            "academic_year_id": str(year.id),
            "stage": "in_progress",
            "code": "make_plan",
            "title": "Составить план работы",
            "sort_order": 5,
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    assert created.json()["school_id"] == str(school.id)

    listing = await client.get(f"/api/v1/admin/checklist-items?academic_year_id={year.id}")
    assert listing.status_code == 200
    assert [item["code"] for item in listing.json()] == ["make_plan"]

    updated = await client.patch(
        f"/api/v1/admin/checklist-items/{item_id}", json={"title": "План работы"}
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "План работы"

    deleted = await client.delete(f"/api/v1/admin/checklist-items/{item_id}")
    assert deleted.status_code == 204
    listing = await client.get(f"/api/v1/admin/checklist-items?academic_year_id={year.id}")
    assert listing.json()[0]["is_active"] is False

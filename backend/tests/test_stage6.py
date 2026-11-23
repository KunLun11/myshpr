"""Stage 6 admin tests: schools, years, reference data, import, audit, CSRF."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import allowed_origin_set, is_request_allowed, normalize_origin
from app.models import AuditLog, User
from app.models.enums import UserRole
from tests.factories import create_class, create_school, create_user, create_year


async def _setup(session: AsyncSession):
    school = await create_school(session, name="Школа Первая")
    other_school = await create_school(session, name="Школа Вторая")
    year = await create_year(session, school, name="2026/2027", is_current=True)
    super_admin = await create_user(
        session,
        school,
        UserRole.SUPER_ADMIN,
        password="password123",
        full_name="Суперадмин",
    )
    admin = await create_user(
        session,
        school,
        UserRole.SCHOOL_ADMIN,
        password="password123",
        full_name="Админ Первой",
    )
    other_admin = await create_user(
        session,
        other_school,
        UserRole.SCHOOL_ADMIN,
        password="password123",
        full_name="Админ Второй",
    )
    klass = await create_class(session, school, year, label="9А")
    return school, other_school, year, super_admin, admin, other_admin, klass


async def _login(client: AsyncClient, email: str) -> None:
    client.cookies.clear()
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200, response.text


async def test_schools_require_super_admin(session: AsyncSession, client: AsyncClient) -> None:
    _, _, _, super_admin, admin, _, _ = await _setup(session)

    await _login(client, admin.email)
    response = await client.get("/api/v1/admin/schools")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert names == ["Школа Первая"]

    response = await client.post("/api/v1/admin/schools", json={"name": "Новая школа"})
    assert response.status_code == 403
    assert response.json()["code"] == "ROLE_FORBIDDEN"

    await _login(client, super_admin.email)
    response = await client.post(
        "/api/v1/admin/schools",
        json={"name": "Новая школа", "city": "Москва", "timezone": "Europe/Moscow"},
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["city"] == "Москва"

    response = await client.patch(
        f"/api/v1/admin/schools/{created['id']}", json={"region": "Москва"}
    )
    assert response.status_code == 200
    assert response.json()["region"] == "Москва"

    # The original school is still visible for the school admin.
    await _login(client, admin.email)
    response = await client.get("/api/v1/admin/schools")
    assert [item["name"] for item in response.json()] == ["Школа Первая"]


async def test_super_admin_can_create_class_for_explicit_school(
    session: AsyncSession, client: AsyncClient
) -> None:
    school, _, _, super_admin, _, _, _ = await _setup(session)
    await _login(client, super_admin.email)

    response = await client.post(
        f"/api/v1/admin/classes?school_id={school.id}",
        json={"grade": 9, "label": "В"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["label"] == "В"


async def test_academic_year_current_switch_and_scope(
    session: AsyncSession, client: AsyncClient
) -> None:
    _, _, _, super_admin, admin, other_admin, _ = await _setup(session)

    await _login(client, admin.email)
    response = await client.post(
        "/api/v1/admin/academic-years",
        json={
            "name": "2027/2028",
            "starts_on": "2027-09-01",
            "ends_on": "2028-05-31",
            "is_current": True,
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["school_id"]
    assert created["is_current"] is True

    response = await client.get("/api/v1/admin/academic-years")
    assert response.status_code == 200
    by_name = {item["name"]: item for item in response.json()}
    assert by_name["2027/2028"]["is_current"] is True
    assert by_name["2026/2027"]["is_current"] is False

    await _login(client, other_admin.email)
    response = await client.patch(
        f"/api/v1/admin/academic-years/{created['id']}", json={"name": "Взлом"}
    )
    assert response.status_code == 403

    # Super admin creates a year for an explicit school.
    await _login(client, super_admin.email)
    response = await client.post(
        "/api/v1/admin/academic-years",
        json={
            "school_id": created["school_id"],
            "name": "2028/2029",
            "starts_on": "2028-09-01",
            "ends_on": "2029-05-31",
        },
    )
    assert response.status_code == 201, response.text


async def test_reference_admin_permissions_and_cache(
    session: AsyncSession, client: AsyncClient
) -> None:
    _, _, _, super_admin, admin, _, _ = await _setup(session)

    await _login(client, super_admin.email)
    response = await client.post(
        "/api/v1/admin/interest-areas",
        json={"slug": "robotics", "name": "Робототехника", "sort_order": 5},
    )
    assert response.status_code == 201, response.text

    response = await client.post(
        "/api/v1/admin/product-categories",
        json={
            "slug": "robot-model",
            "name": "Модель робота",
            "guidance": {
                "examples": ["Модель манипулятора"],
                "must_have": ["Работающая модель"],
                "common_mistakes": [],
                "defense_tip": "Покажите демонстрацию",
            },
        },
    )
    assert response.status_code == 201, response.text
    category_id = response.json()["id"]

    await _login(client, admin.email)
    response = await client.get("/api/v1/admin/interest-areas")
    assert response.status_code == 200
    assert "robotics" in {item["slug"] for item in response.json()}

    response = await client.post(
        "/api/v1/admin/interest-areas", json={"slug": "forbidden", "name": "Нельзя"}
    )
    assert response.status_code == 403

    # The student-facing reference endpoint uses a 5-minute cache; admin
    # mutations must invalidate it.
    response = await client.get("/api/v1/reference/product-categories")
    assert response.status_code == 200
    assert "robot-model" in {item["slug"] for item in response.json()}

    await _login(client, super_admin.email)
    response = await client.patch(
        f"/api/v1/admin/product-categories/{category_id}",
        json={"name": "Модель робота 2", "is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_student_csv_import(session: AsyncSession, client: AsyncClient) -> None:
    _, _, _, _, admin, other_admin, klass = await _setup(session)
    await _login(client, admin.email)

    csv_body = (
        "full_name,email\n"
        "Анна Смирнова,anna@example.com\n"
        "Иван Петров,ivan@example.com\n"
        "Плохая строка,not-an-email\n"
        "Анна Смирнова,anna@example.com\n"
    )
    response = await client.post(
        f"/api/v1/admin/students/import?class_id={klass.id}",
        files={"file": ("students.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["created_count"] == 2
    assert payload["skipped_count"] == 2
    for student in payload["created"]:
        assert len(student["temp_password"]) >= 8

    response = await client.get(f"/api/v1/admin/students?class_id={klass.id}")
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = await client.get("/api/v1/admin/students", params={"q": "Анна"})
    assert response.status_code == 200
    assert [item["full_name"] for item in response.json()] == ["Анна Смирнова"]

    # Re-import: both valid rows now exist.
    response = await client.post(
        f"/api/v1/admin/students/import?class_id={klass.id}",
        files={"file": ("students.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 201
    assert response.json()["created_count"] == 0
    assert response.json()["skipped_count"] == 4

    response = await session.execute(select(User).where(User.email == "anna@example.com"))
    student = response.scalar_one()
    assert student.must_change_password is True
    assert student.role is UserRole.STUDENT

    await _login(client, other_admin.email)
    response = await client.post(
        f"/api/v1/admin/students/import?class_id={klass.id}",
        files={
            "file": (
                "students.csv",
                "full_name,email\nТест,test@example.com".encode(),
                "text/csv",
            )
        },
    )
    assert response.status_code == 403


async def test_audit_log_records_and_scopes(session: AsyncSession, client: AsyncClient) -> None:
    school, _, _, super_admin, admin, other_admin, _ = await _setup(session)

    await _login(client, admin.email)
    response = await client.post("/api/v1/admin/classes", json={"grade": 10, "label": "Б"})
    assert response.status_code == 201, response.text

    response = await client.get("/api/v1/admin/audit-log")
    assert response.status_code == 200
    actions = [entry["action"] for entry in response.json()]
    assert "class.created" in actions

    await _login(client, other_admin.email)
    response = await client.get("/api/v1/admin/audit-log")
    assert response.status_code == 200
    assert response.json() == []

    await _login(client, super_admin.email)
    response = await client.get("/api/v1/admin/audit-log")
    assert response.status_code == 200
    assert any(entry["action"] == "class.created" for entry in response.json())

    response = await client.get("/api/v1/admin/audit-log", params={"school_id": str(school.id)})
    assert response.status_code == 200
    assert all(entry["school_id"] == str(school.id) for entry in response.json())

    stored = await session.execute(select(AuditLog).where(AuditLog.action == "class.created"))
    assert stored.scalar_one().entity_type == "class"


def test_origin_guard_helpers() -> None:
    assert normalize_origin("http://localhost:3000/") == "http://localhost:3000"
    assert normalize_origin("null") is None

    allowed = allowed_origin_set(["http://localhost:3000"], ["https://admin.example.org"])

    assert is_request_allowed(
        method="GET",
        origin="https://evil.example",
        referer=None,
        fetch_site="cross-site",
        allowed=allowed,
        fail_closed=True,
    )

    assert not is_request_allowed(
        method="POST",
        origin="https://evil.example",
        referer=None,
        fetch_site=None,
        allowed=allowed,
        fail_closed=True,
    )
    assert is_request_allowed(
        method="POST",
        origin="http://localhost:3000",
        referer=None,
        fetch_site="same-origin",
        allowed=allowed,
        fail_closed=True,
    )
    assert not is_request_allowed(
        method="POST",
        origin="http://localhost:3000",
        referer=None,
        fetch_site="cross-site",
        allowed=allowed,
        fail_closed=True,
    )
    # Non-browser requests have no Origin/Referer.
    assert is_request_allowed(
        method="POST",
        origin=None,
        referer=None,
        fetch_site=None,
        allowed=allowed,
        fail_closed=True,
    )
    # Empty allowlist: permissive in dev, fail closed in prod.
    assert is_request_allowed(
        method="POST",
        origin="http://localhost:3000",
        referer=None,
        fetch_site=None,
        allowed=set(),
        fail_closed=False,
    )
    assert not is_request_allowed(
        method="POST",
        origin="http://localhost:3000",
        referer=None,
        fetch_site=None,
        allowed=set(),
        fail_closed=True,
    )

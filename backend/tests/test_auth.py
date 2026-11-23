"""Integration tests for registration, login, refresh rotation and RBAC."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import ACCESS_COOKIE, REFRESH_COOKIE
from app.models import User
from app.models.enums import UserRole
from app.models.user import StudentProfile
from tests.factories import (
    create_class,
    create_invite,
    create_school,
    create_user,
    create_year,
)

REGISTER_PAYLOAD = {
    "invite_code": "ABCD2345",
    "email": "new.student@example.com",
    "password": "password123",
    "full_name": "Новый Ученик",
}


async def _setup_class(
    session: AsyncSession,
    *,
    invite_code: str = "ABCD2345",
    max_uses: int | None = None,
    expires_in_days: int = 14,
    uses_count: int = 0,
    revoked: bool = False,
):
    school = await create_school(session)
    year = await create_year(session, school, is_current=True)
    teacher = await create_user(session, school, UserRole.TEACHER, password="password123")
    school_class = await create_class(session, school, year, label="9А", curator_id=teacher.id)
    invite = await create_invite(
        session,
        school_class,
        code=invite_code,
        max_uses=max_uses,
        expires_in_days=expires_in_days,
        uses_count=uses_count,
        revoked=revoked,
        created_by=teacher.id,
    )
    return school, year, teacher, school_class, invite


async def _login(client: AsyncClient, email: str, password: str = "password123"):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _refresh_with(client: AsyncClient, raw: str):
    client.cookies.clear()
    return await client.post("/api/v1/auth/refresh", headers={"cookie": f"{REFRESH_COOKIE}={raw}"})


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


async def test_register_student_with_invite(session, client) -> None:
    school, _, _, school_class, invite = await _setup_class(session)

    response = await client.post("/api/v1/auth/register/student", json=REGISTER_PAYLOAD)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "student"
    assert body["class"]["label"] == "9А"
    assert body["school"]["id"] == str(school.id)

    cookie_headers = response.headers.get_list("set-cookie")
    assert any(header.startswith(f"{ACCESS_COOKIE}=") for header in cookie_headers)
    assert any(header.startswith(f"{REFRESH_COOKIE}=") for header in cookie_headers)
    assert all("httponly" in header.lower() for header in cookie_headers)

    user = await session.get(User, uuid.UUID(body["id"]))
    assert user is not None
    assert user.password_hash != REGISTER_PAYLOAD["password"]

    profile = await session.get(StudentProfile, user.id)
    assert profile is not None
    assert profile.class_id == school_class.id

    await session.refresh(invite)
    assert invite.uses_count == 1


async def test_register_rejects_expired_invite(session, client) -> None:
    await _setup_class(session, expires_in_days=-1)

    response = await client.post("/api/v1/auth/register/student", json=REGISTER_PAYLOAD)

    assert response.status_code == 422
    assert response.json()["code"] == "INVITE_EXPIRED"


async def test_register_rejects_revoked_invite(session, client) -> None:
    await _setup_class(session, revoked=True)

    response = await client.post("/api/v1/auth/register/student", json=REGISTER_PAYLOAD)

    assert response.status_code == 422
    assert response.json()["code"] == "INVITE_REVOKED"


async def test_register_rejects_exhausted_invite(session, client) -> None:
    await _setup_class(session, max_uses=1, uses_count=1)

    response = await client.post("/api/v1/auth/register/student", json=REGISTER_PAYLOAD)

    assert response.status_code == 422
    assert response.json()["code"] == "INVITE_EXHAUSTED"


async def test_register_rejects_unknown_invite(session, client) -> None:
    response = await client.post(
        "/api/v1/auth/register/student",
        json={**REGISTER_PAYLOAD, "invite_code": "NOPE1234"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVITE_NOT_FOUND"


async def test_register_rejects_duplicate_email(session, client) -> None:
    await _setup_class(session, invite_code="CODE1111", max_uses=5)
    payload = {**REGISTER_PAYLOAD, "invite_code": "CODE1111"}
    first = await client.post("/api/v1/auth/register/student", json=payload)
    assert first.status_code == 201, first.text

    second = await client.post("/api/v1/auth/register/student", json=payload)

    assert second.status_code == 409
    assert second.json()["code"] == "EMAIL_TAKEN"


# ---------------------------------------------------------------------------
# Login / me / logout
# ---------------------------------------------------------------------------


async def test_login_and_me(session, client) -> None:
    school = await create_school(session)
    user = await create_user(
        session,
        school,
        UserRole.TEACHER,
        email="teacher@example.com",
        password="password123",
        full_name="Учитель",
    )

    response = await _login(client, "teacher@example.com")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(user.id)
    assert response.json()["role"] == "teacher"

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "teacher@example.com"


async def test_me_requires_cookie(session, client) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


async def test_login_wrong_password(session, client) -> None:
    school = await create_school(session)
    await create_user(
        session, school, UserRole.TEACHER, email="teacher@example.com", password="password123"
    )

    response = await _login(client, "teacher@example.com", "wrong-password")

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_inactive_user(session, client) -> None:
    school = await create_school(session)
    await create_user(
        session,
        school,
        UserRole.TEACHER,
        email="disabled@example.com",
        password="password123",
        is_active=False,
    )

    response = await _login(client, "disabled@example.com")

    assert response.status_code == 403
    assert response.json()["code"] == "ACCOUNT_DISABLED"


async def test_login_locks_after_five_failures(session, client) -> None:
    school = await create_school(session)
    await create_user(
        session, school, UserRole.TEACHER, email="teacher@example.com", password="password123"
    )

    for _ in range(5):
        failed = await _login(client, "teacher@example.com", "wrong-password")
        assert failed.status_code == 401

    locked = await _login(client, "teacher@example.com")

    assert locked.status_code == 423
    assert locked.json()["code"] == "ACCOUNT_LOCKED"


async def test_logout_revokes_refresh_and_clears_cookies(session, client) -> None:
    school = await create_school(session)
    await create_user(
        session, school, UserRole.TEACHER, email="teacher@example.com", password="password123"
    )
    await _login(client, "teacher@example.com")
    old_refresh = client.cookies.get(REFRESH_COOKIE)
    assert old_refresh

    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert REFRESH_COOKIE not in client.cookies
    assert ACCESS_COOKIE not in client.cookies

    retry = await _refresh_with(client, old_refresh)
    assert retry.status_code == 401


# ---------------------------------------------------------------------------
# Refresh rotation
# ---------------------------------------------------------------------------


async def test_refresh_rotates_and_reuse_revokes_chain(session, client) -> None:
    school = await create_school(session)
    await create_user(
        session, school, UserRole.TEACHER, email="teacher@example.com", password="password123"
    )
    await _login(client, "teacher@example.com")
    first_refresh = client.cookies.get(REFRESH_COOKIE)
    assert first_refresh

    rotated = await client.post("/api/v1/auth/refresh")
    assert rotated.status_code == 200, rotated.text
    second_refresh = client.cookies.get(REFRESH_COOKIE)
    assert second_refresh and second_refresh != first_refresh

    reused = await _refresh_with(client, first_refresh)
    assert reused.status_code == 401
    assert reused.json()["code"] == "REFRESH_TOKEN_REUSED"

    # The whole chain is revoked: the previously valid token no longer works.
    after_chain_revoke = await _refresh_with(client, second_refresh)
    assert after_chain_revoke.status_code == 401


async def test_refresh_without_cookie(session, client) -> None:
    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["code"] == "NO_REFRESH_TOKEN"


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------


async def test_change_password_revokes_previous_tokens(session, client) -> None:
    school = await create_school(session)
    await create_user(
        session, school, UserRole.TEACHER, email="teacher@example.com", password="password123"
    )
    await _login(client, "teacher@example.com")
    old_refresh = client.cookies.get(REFRESH_COOKIE)

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "password123", "new_password": "newpassword123"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["must_change_password"] is False

    old_session = await _refresh_with(client, old_refresh)
    assert old_session.status_code == 401

    relogin = await _login(client, "teacher@example.com", "newpassword123")
    assert relogin.status_code == 200


async def test_change_password_rejects_wrong_current(session, client) -> None:
    school = await create_school(session)
    await create_user(
        session, school, UserRole.TEACHER, email="teacher@example.com", password="password123"
    )
    await _login(client, "teacher@example.com")

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong", "new_password": "newpassword123"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_CURRENT_PASSWORD"


# ---------------------------------------------------------------------------
# RBAC / school scope
# ---------------------------------------------------------------------------


async def test_student_cannot_use_admin_endpoints(session, client) -> None:
    _, _, _, _, invite = await _setup_class(session)
    registered = await client.post("/api/v1/auth/register/student", json=REGISTER_PAYLOAD)
    assert registered.status_code == 201

    response = await client.get("/api/v1/admin/classes")

    assert response.status_code == 403
    assert response.json()["code"] == "ROLE_FORBIDDEN"


async def test_teacher_cannot_invite_to_foreign_school_class(session, client) -> None:
    # School A teacher
    school_a = await create_school(session)
    year_a = await create_year(session, school_a)
    teacher_a = await create_user(
        session, school_a, UserRole.TEACHER, email="teacher.a@example.com", password="password123"
    )
    await create_class(session, school_a, year_a, label="9А", curator_id=teacher_a.id)

    # Class in another school
    school_b = await create_school(session)
    year_b = await create_year(session, school_b)
    class_b = await create_class(session, school_b, year_b, label="9Б")

    await _login(client, "teacher.a@example.com")
    response = await client.post(
        f"/api/v1/admin/classes/{class_b.id}/invites", json={"expires_in_days": 14}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "SCHOOL_ACCESS_DENIED"


async def test_teacher_sees_only_own_classes(session, client) -> None:
    school = await create_school(session)
    year = await create_year(session, school, is_current=True)
    teacher = await create_user(
        session, school, UserRole.TEACHER, email="teacher@example.com", password="password123"
    )
    other_teacher = await create_user(session, school, UserRole.TEACHER)
    own_class = await create_class(session, school, year, label="9А", curator_id=teacher.id)
    await create_class(session, school, year, label="9Б", curator_id=other_teacher.id)

    await _login(client, "teacher@example.com")
    response = await client.get("/api/v1/teacher/classes")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [str(own_class.id)]
    assert body[0]["students_count"] == 0


async def test_admin_creates_class_and_invite(session, client) -> None:
    school = await create_school(session)
    await create_year(session, school, is_current=True)
    admin = await create_user(
        session,
        school,
        UserRole.SCHOOL_ADMIN,
        email="admin@example.com",
        password="password123",
    )
    await _login(client, "admin@example.com")

    created = await client.post("/api/v1/admin/classes", json={"grade": 10, "label": "10Б"})
    assert created.status_code == 201, created.text
    class_id = created.json()["id"]
    assert created.json()["students_count"] == 0
    assert created.json()["academic_year_name"]

    invite = await client.post(
        f"/api/v1/admin/classes/{class_id}/invites",
        json={"max_uses": 5, "expires_in_days": 14},
    )
    assert invite.status_code == 201, invite.text
    assert invite.json()["max_uses"] == 5
    assert invite.json()["register_url"].endswith(invite.json()["code"])

    students = await client.get(f"/api/v1/admin/classes/{class_id}/students")
    assert students.status_code == 200
    assert students.json() == []

    _ = admin


async def test_invite_can_be_revoked(session, client) -> None:
    _, _, teacher, school_class, _ = await _setup_class(session, invite_code="REVOKE12")
    await _login(client, teacher.email)

    created = await client.post(
        f"/api/v1/admin/classes/{school_class.id}/invites", json={"max_uses": 3}
    )
    assert created.status_code == 201, created.text
    code = created.json()["code"]

    revoked = await client.post(f"/api/v1/admin/invites/{created.json()['id']}/revoke")
    assert revoked.status_code == 204

    registration = await client.post(
        "/api/v1/auth/register/student", json={**REGISTER_PAYLOAD, "invite_code": code}
    )
    assert registration.status_code == 422
    assert registration.json()["code"] == "INVITE_REVOKED"


async def test_created_invite_can_be_used_to_register(session, client) -> None:
    school = await create_school(session)
    await create_year(session, school, is_current=True)
    await create_user(
        session,
        school,
        UserRole.SCHOOL_ADMIN,
        email="admin@example.com",
        password="password123",
    )
    await _login(client, "admin@example.com")

    created = await client.post("/api/v1/admin/classes", json={"grade": 9, "label": "9В"})
    class_id = created.json()["id"]
    invite = await client.post(f"/api/v1/admin/classes/{class_id}/invites", json={"max_uses": 2})
    code = invite.json()["code"]

    registration = await client.post(
        "/api/v1/auth/register/student", json={**REGISTER_PAYLOAD, "invite_code": code}
    )

    assert registration.status_code == 201, registration.text
    assert registration.json()["class"]["label"] == "9В"

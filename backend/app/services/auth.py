"""Authentication business logic: registration, login, rotation, RBAC data."""

import ipaddress
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.rate_limit import login_failure_tracker
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import AcademicYear, RefreshToken, School, SchoolClass, User
from app.models.enums import UserRole
from app.models.user import StudentProfile
from app.repositories import classes as classes_repo
from app.repositories import tokens as tokens_repo
from app.repositories import users as users_repo
from app.schemas.auth import ClassBrief, MeOut, SchoolBrief


class TokenPair(NamedTuple):
    access_token: str
    refresh_token: str


def _now() -> datetime:
    return datetime.now(UTC)


def _to_ip(value: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    if not value:
        return None
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _ensure_account_active(user: User) -> None:
    if user.deleted_at is not None:
        raise UnauthorizedError("Аккаунт недоступен", "ACCOUNT_DELETED")
    if user.is_active is False:
        raise ForbiddenError("Аккаунт отключён администратором", "ACCOUNT_DISABLED")


async def register_student(
    session: AsyncSession,
    *,
    invite_code: str,
    email: str,
    password: str,
    full_name: str,
    user_agent: str | None,
    ip: str | None,
) -> User:
    """Create a student account from a valid class invite."""
    invite = await classes_repo.get_invite_by_code(session, invite_code, for_update=True)
    if invite is None:
        raise ValidationError("Код приглашения не найден", "INVITE_NOT_FOUND")

    now = _now()
    if invite.revoked_at is not None:
        raise ValidationError("Код приглашения отозван", "INVITE_REVOKED")
    if invite.expires_at <= now:
        raise ValidationError("Срок действия кода истёк", "INVITE_EXPIRED")
    if invite.max_uses is not None and invite.uses_count >= invite.max_uses:
        raise ValidationError("Код приглашения уже использован", "INVITE_EXHAUSTED")

    if await users_repo.get_by_email(session, email) is not None:
        raise ConflictError("Этот email уже зарегистрирован", "EMAIL_TAKEN")

    school_class = await classes_repo.get_by_id(session, invite.class_id)
    if school_class is None:
        raise NotFoundError("Класс не найден", "CLASS_NOT_FOUND")

    school = await session.get(School, school_class.school_id)
    if school is None or school.is_active is False:
        raise ForbiddenError("Школа недоступна для регистрации", "SCHOOL_INACTIVE")

    user = User(
        school_id=school_class.school_id,
        role=UserRole.STUDENT,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
    )
    session.add(user)
    await session.flush()

    session.add(StudentProfile(user_id=user.id, class_id=school_class.id))
    invite.uses_count += 1

    try:
        await session.commit()
    except IntegrityError as exc:  # concurrent registration with the same email
        await session.rollback()
        raise ConflictError("Этот email уже зарегистрирован", "EMAIL_TAKEN") from exc

    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, *, email: str, password: str) -> User:
    lock_key = email.strip().lower()
    if login_failure_tracker.is_locked(lock_key):
        raise AppError(
            "ACCOUNT_LOCKED",
            "Слишком много неудачных попыток входа. Попробуйте через 15 минут.",
            status_code=423,
        )

    user = await users_repo.get_by_email(session, email)
    if user is None or not verify_password(password, user.password_hash):
        login_failure_tracker.record(lock_key)
        raise UnauthorizedError("Неверный email или пароль", "INVALID_CREDENTIALS")

    login_failure_tracker.reset(lock_key)
    _ensure_account_active(user)
    return user


async def start_session(
    session: AsyncSession,
    user: User,
    *,
    user_agent: str | None,
    ip: str | None,
    touch_login: bool = True,
) -> TokenPair:
    """Issue an access token and persist a new refresh token."""
    now = _now()
    if touch_login:
        user.last_login_at = now

    raw_refresh = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=now + timedelta(days=_refresh_ttl_days()),
            user_agent=user_agent,
            ip=_to_ip(ip),
        )
    )
    await session.commit()

    access = create_access_token(user_id=user.id, role=user.role.value, school_id=user.school_id)
    return TokenPair(access_token=access, refresh_token=raw_refresh)


async def rotate_session(
    session: AsyncSession,
    *,
    raw_refresh: str,
    user_agent: str | None,
    ip: str | None,
) -> tuple[User, TokenPair]:
    """Rotate a refresh token; reuse of a revoked token kills the whole chain."""
    now = _now()
    stored = await tokens_repo.get_by_hash(session, hash_refresh_token(raw_refresh))
    if stored is None:
        raise UnauthorizedError("Сессия не найдена, войдите заново", "INVALID_REFRESH_TOKEN")

    if stored.revoked_at is not None:
        await tokens_repo.revoke_all_for_user(session, stored.user_id, now=now)
        await session.commit()
        raise UnauthorizedError("Сессия недействительна, войдите заново", "REFRESH_TOKEN_REUSED")

    if stored.expires_at <= now:
        raise UnauthorizedError("Сессия истекла, войдите заново", "REFRESH_TOKEN_EXPIRED")

    user = await users_repo.get_by_id(session, stored.user_id)
    if user is None:
        raise UnauthorizedError("Пользователь не найден", "INVALID_REFRESH_TOKEN")
    _ensure_account_active(user)

    stored.revoked_at = now
    raw_refresh_new = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_new),
            expires_at=now + timedelta(days=_refresh_ttl_days()),
            user_agent=user_agent,
            ip=_to_ip(ip),
        )
    )
    await session.commit()

    access = create_access_token(user_id=user.id, role=user.role.value, school_id=user.school_id)
    return user, TokenPair(access_token=access, refresh_token=raw_refresh_new)


async def logout(session: AsyncSession, *, raw_refresh: str | None) -> None:
    """Revoke the presented refresh token. Logout is idempotent and tolerant."""
    if not raw_refresh:
        return
    stored = await tokens_repo.get_by_hash(session, hash_refresh_token(raw_refresh))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = _now()
        await session.commit()


async def change_password(
    session: AsyncSession, *, user: User, current_password: str, new_password: str
) -> User:
    if not verify_password(current_password, user.password_hash):
        raise ValidationError("Текущий пароль указан неверно", "INVALID_CURRENT_PASSWORD")
    if current_password == new_password:
        raise ValidationError("Новый пароль совпадает с текущим", "PASSWORD_UNCHANGED")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await tokens_repo.revoke_all_for_user(session, user.id, now=_now())
    await session.flush()
    return user


async def build_me(session: AsyncSession, user: User) -> MeOut:
    school = await session.get(School, user.school_id) if user.school_id else None
    class_brief: ClassBrief | None = None

    if user.role is UserRole.STUDENT:
        profile = await classes_repo.get_student_profile(session, user.id)
        if profile is not None:
            school_class = await session.get(SchoolClass, profile.class_id)
            if school_class is not None:
                year = await session.get(AcademicYear, school_class.academic_year_id)
                class_brief = ClassBrief(
                    id=school_class.id,
                    grade=school_class.grade,
                    label=school_class.label,
                    academic_year_name=year.name if year else None,
                )

    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        school=SchoolBrief(id=school.id, name=school.name) if school else None,
        class_info=class_brief,
        must_change_password=user.must_change_password,
    )


def _refresh_ttl_days() -> int:
    return get_settings().REFRESH_TOKEN_TTL_DAYS


__all__ = [
    "TokenPair",
    "authenticate",
    "build_me",
    "change_password",
    "logout",
    "register_student",
    "rotate_session",
    "start_session",
]

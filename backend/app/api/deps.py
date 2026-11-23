"""Shared API dependencies: DB session, current user, roles and scoping."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import ACCESS_COOKIE
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import TokenError, decode_access_token
from app.db.session import get_session
from app.models import SchoolClass, User
from app.models.enums import UserRole
from app.repositories import classes as classes_repo
from app.repositories import users as users_repo

logger = get_logger(__name__)

__all__ = [
    "ensure_class_access",
    "ensure_school_access",
    "get_current_user",
    "get_session",
    "require_roles",
]


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    access_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
) -> User:
    """Resolve the user from the httpOnly access-token cookie."""
    if not access_token:
        raise UnauthorizedError("Требуется вход", "NOT_AUTHENTICATED")

    try:
        payload = decode_access_token(access_token)
        user_id = uuid.UUID(str(payload["sub"]))
    except (TokenError, ValueError) as exc:
        raise UnauthorizedError("Сессия истекла, войдите заново", "INVALID_ACCESS_TOKEN") from exc

    user = await users_repo.get_by_id(session, user_id)
    if user is None or user.deleted_at is not None or user.is_active is False:
        raise UnauthorizedError("Пользователь недоступен", "USER_INACTIVE")
    return user


def require_roles(*roles: UserRole) -> Callable[..., object]:
    """Dependency factory: allow the listed roles (and super_admin)."""

    async def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role is UserRole.SUPER_ADMIN:
            return user
        if user.role not in roles:
            logger.warning("access denied: user_id=%s role=%s", user.id, user.role)
            raise ForbiddenError("Недостаточно прав для этого действия", "ROLE_FORBIDDEN")
        return user

    return dependency


def ensure_school_access(user: User, school_id: uuid.UUID | None) -> None:
    """Every school-scoped request must stay inside the user's school."""
    if user.role is UserRole.SUPER_ADMIN:
        return
    if school_id is None or user.school_id is None or user.school_id != school_id:
        logger.warning(
            "school scope denied: user_id=%s role=%s target_school=%s",
            user.id,
            user.role,
            school_id,
        )
        raise ForbiddenError("Нет доступа к этой школе", "SCHOOL_ACCESS_DENIED")


async def ensure_class_access(session: AsyncSession, user: User, school_class: SchoolClass) -> None:
    """Check that the user may work with this class.

    - super_admin: any class;
    - school_admin: any class of their school;
    - teacher: classes they curate;
    - student: their own class.
    """
    ensure_school_access(user, school_class.school_id)

    if user.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN):
        return

    if user.role is UserRole.TEACHER and school_class.curator_id == user.id:
        return

    if user.role is UserRole.STUDENT:
        profile = await classes_repo.get_student_profile(session, user.id)
        if profile is not None and profile.class_id == school_class.id:
            return

    logger.warning(
        "class scope denied: user_id=%s role=%s class_id=%s",
        user.id,
        user.role,
        school_class.id,
    )
    raise ForbiddenError("Нет доступа к этому классу", "CLASS_ACCESS_DENIED")

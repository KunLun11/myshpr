"""Authentication endpoints: register, login, refresh, logout, me."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.core.cookies import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    set_auth_cookies,
)
from app.core.errors import UnauthorizedError
from app.core.rate_limit import enforce_rate_limit, login_limiter, register_limiter
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MeOut,
    RegisterStudentRequest,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_key(request: Request, scope: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{scope}:{host}"


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "/register/student",
    response_model=MeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация ученика по коду класса",
)
async def register_student(
    payload: RegisterStudentRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MeOut:
    await enforce_rate_limit(register_limiter, _client_key(request, "register"))

    user = await auth_service.register_student(
        session,
        invite_code=payload.invite_code,
        email=str(payload.email),
        password=payload.password,
        full_name=payload.full_name,
        user_agent=_user_agent(request),
        ip=_client_ip(request),
    )
    tokens = await auth_service.start_session(
        session,
        user,
        user_agent=_user_agent(request),
        ip=_client_ip(request),
    )
    set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)
    return await auth_service.build_me(session, user)


@router.post("/login", response_model=MeOut, summary="Вход")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MeOut:
    await enforce_rate_limit(login_limiter, _client_key(request, "login"))

    user = await auth_service.authenticate(
        session, email=str(payload.email), password=payload.password
    )
    tokens = await auth_service.start_session(
        session,
        user,
        user_agent=_user_agent(request),
        ip=_client_ip(request),
    )
    set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)
    return await auth_service.build_me(session, user)


@router.post("/refresh", response_model=MeOut, summary="Ротация refresh-токена")
async def refresh_session(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> MeOut:
    if not refresh_token:
        raise UnauthorizedError("Сессия не найдена, войдите заново", "NO_REFRESH_TOKEN")

    user, tokens = await auth_service.rotate_session(
        session,
        raw_refresh=refresh_token,
        user_agent=_user_agent(request),
        ip=_client_ip(request),
    )
    set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)
    return await auth_service.build_me(session, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Выход")
async def logout(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> None:
    await auth_service.logout(session, raw_refresh=refresh_token)
    clear_auth_cookies(response)


@router.get("/me", response_model=MeOut, summary="Текущий пользователь")
async def me(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MeOut:
    return await auth_service.build_me(session, user)


@router.post("/change-password", response_model=MeOut, summary="Смена пароля")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MeOut:
    user = await auth_service.change_password(
        session,
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    # Old sessions are revoked above; issue a fresh pair for this device.
    tokens = await auth_service.start_session(
        session,
        user,
        user_agent=_user_agent(request),
        ip=_client_ip(request),
        touch_login=False,
    )
    set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)
    return await auth_service.build_me(session, user)

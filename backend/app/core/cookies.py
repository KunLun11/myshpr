"""httpOnly cookie helpers for the access/refresh token pair.

Tokens are never returned in JSON bodies: the browser keeps them in
``httpOnly`` cookies, and the frontend calls the API through the same-origin
Next.js proxy (ADR-03).
"""

from fastapi import Response

from app.core.config import get_settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def _cookie_kwargs() -> dict[str, object]:
    return {
        "httponly": True,
        # Secure cookies require HTTPS; local dev runs over plain HTTP.
        "secure": get_settings().ENV == "prod",
        "samesite": "lax",
        "path": "/",
    }


def set_auth_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    kwargs = _cookie_kwargs()
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.ACCESS_TOKEN_TTL_MIN * 60,
        **kwargs,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        **kwargs,
    )


def clear_auth_cookies(response: Response) -> None:
    kwargs = _cookie_kwargs()
    response.delete_cookie(ACCESS_COOKIE, **kwargs)
    response.delete_cookie(REFRESH_COOKIE, **kwargs)

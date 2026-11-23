"""Password hashing, JWT issuing/validation and refresh-token helpers.

Uses ``bcrypt`` directly instead of ``passlib`` to avoid the known
``passlib 1.7.4`` + ``bcrypt>=4.1`` incompatibility (see TASKS.md risk
section). Bcrypt has a 72-byte input limit, so callers must validate
password length.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

MAX_PASSWORD_BYTES = 72
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(Exception):
    """Raised when a JWT is malformed, expired or of the wrong type."""


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError("Password must be at most 72 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=get_settings().BCRYPT_ROUNDS)).decode(
        "utf-8"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        encoded = password.encode("utf-8")
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------


def create_access_token(
    *,
    user_id: uuid.UUID | str,
    role: str,
    school_id: uuid.UUID | str | None,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    lifetime = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_TTL_MIN)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": str(role),
        "school_id": str(school_id) if school_id is not None else None,
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, get_settings().JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
    except JWTError as exc:  # expired, malformed or badly signed
        raise TokenError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise TokenError("Unexpected token type")
    if not payload.get("sub"):
        raise TokenError("Token has no subject")
    return payload


def decode_access_token(token: str) -> dict[str, Any]:
    return decode_token(token, expected_type=ACCESS_TOKEN_TYPE)


# ---------------------------------------------------------------------------
# Refresh tokens (opaque random strings, only the hash is stored)
# ---------------------------------------------------------------------------


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

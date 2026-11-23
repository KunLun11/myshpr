"""Unit tests for password hashing, JWT and refresh-token helpers."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.security import (
    JWT_ALGORITHM,
    TokenError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_and_verify_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong", hashed)


def test_rejects_overlong_password() -> None:
    with pytest.raises(ValueError):
        hash_password("x" * 73)


def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, role="student", school_id=None)

    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "student"
    assert payload["type"] == "access"
    assert payload["jti"]


def test_expired_access_token_rejected() -> None:
    token = create_access_token(
        user_id=uuid.uuid4(),
        role="student",
        school_id=None,
        expires_delta=timedelta(seconds=-5),
    )

    with pytest.raises(TokenError):
        decode_access_token(token)


def test_bad_signature_rejected() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        "another-secret",
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(TokenError):
        decode_access_token(token)


def test_wrong_token_type_rejected() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "refresh",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        get_settings().JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(TokenError):
        decode_access_token(token)


def test_refresh_token_hash_is_stable_and_not_reversible() -> None:
    raw = generate_refresh_token()

    assert hash_refresh_token(raw) == hash_refresh_token(raw)
    assert raw not in hash_refresh_token(raw)
    assert hash_refresh_token(generate_refresh_token()) != hash_refresh_token(raw)

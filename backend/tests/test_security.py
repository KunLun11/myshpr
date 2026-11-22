"""Unit tests for password hashing."""

import pytest

from app.core.security import hash_password, verify_password


def test_hash_and_verify_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong", hashed)


def test_rejects_overlong_password() -> None:
    with pytest.raises(ValueError):
        hash_password("x" * 73)

"""Password hashing and verification.

Uses ``bcrypt`` directly instead of ``passlib`` to avoid the known
``passlib 1.7.4`` + ``bcrypt>=4.1`` incompatibility (see TASKS.md risk
section). Bcrypt has a 72-byte input limit, so callers must validate
password length.
"""

import bcrypt

from app.core.config import get_settings

MAX_PASSWORD_BYTES = 72


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

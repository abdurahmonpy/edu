"""Password hashing and JWT helpers.

Passwords use bcrypt.  bcrypt silently truncates at 72 bytes, so we pre-hash
long inputs with SHA-256 and base64 them (the well-known "bcrypt + sha256"
pattern) which keeps every password usable while staying inside the limit.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
import jwt

from .config import settings
from .utils import utcnow

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
RESET_TOKEN_TYPE = "reset"


# --------------------------------------------------------------------- errors
class TokenError(Exception):
    """Raised when a JWT is missing, malformed, expired or of the wrong type."""


# ------------------------------------------------------------------ passwords
def _prepare(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(_prepare(password), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def password_problems(password: str) -> list[str]:
    """Return a list of human readable validation problems (empty == valid)."""
    problems: list[str] = []
    if len(password) < settings.password_min_length:
        problems.append(
            f"Parol kamida {settings.password_min_length} ta belgidan iborat bo'lishi kerak."
        )
    if len(password.encode("utf-8")) > 4096:
        problems.append("Parol juda uzun.")
    if password.lower() in {"12345678", "password", "qwertyui", "parol123"}:
        problems.append("Bu parol juda oddiy, boshqasini tanlang.")
    return problems


# ----------------------------------------------------------------------- JWT
def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def _decode(token: str, expected_type: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token muddati tugagan.") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("Token yaroqsiz.") from exc

    if expected_type and payload.get("type") != expected_type:
        raise TokenError("Token turi noto'g'ri.")
    return payload


def create_access_token(
    user_id: str,
    *,
    role: str = "student",
    extra: dict[str, Any] | None = None,
) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)``."""
    now = utcnow()
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": ACCESS_TOKEN_TYPE,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": secrets.token_urlsafe(12),
    }
    if extra:
        payload.update(extra)
    return _encode(payload), int(expires_delta.total_seconds())


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """Return ``(token, expires_at)``."""
    now = utcnow()
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "type": REFRESH_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_urlsafe(24),
    }
    return _encode(payload), expires_at


def create_reset_token(user_id: str, ttl_minutes: int = 30) -> tuple[str, datetime]:
    now = utcnow()
    expires_at = now + timedelta(minutes=ttl_minutes)
    payload = {
        "sub": user_id,
        "type": RESET_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_urlsafe(24),
    }
    return _encode(payload), expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    return _decode(token, ACCESS_TOKEN_TYPE)


def decode_refresh_token(token: str) -> dict[str, Any]:
    return _decode(token, REFRESH_TOKEN_TYPE)


def decode_reset_token(token: str) -> dict[str, Any]:
    return _decode(token, RESET_TOKEN_TYPE)


def hash_token(token: str) -> str:
    """Opaque, deterministic hash used to store refresh/reset tokens at rest."""
    return hashlib.sha256((settings.secret_key + token).encode("utf-8")).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)

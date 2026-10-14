"""FastAPI dependencies: authentication, roles and rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_session
from .models import User
from .security import TokenError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_prefix}/auth/token",
    auto_error=False,
    description="Swagger uchun email (username maydonida) va parol orqali JWT olish.",
)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Avtorizatsiya talab qilinadi.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _user_from_token(session: AsyncSession, token: str) -> User:
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await session.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi topilmadi.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hisob bloklangan. Qo'llab-quvvatlash xizmatiga murojaat qiling.",
        )
    return user


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not token:
        raise CREDENTIALS_ERROR
    return await _user_from_token(session, token)


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    if not token:
        return None
    try:
        return await _user_from_token(session, token)
    except HTTPException:
        return None


def require_roles(*roles: str) -> Callable[..., Awaitable[User]]:
    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu amal uchun ruxsat yo'q.",
            )
        return user

    return _dependency


require_admin = require_roles("admin")
require_staff = require_roles("admin", "teacher")


async def user_from_ws(websocket: WebSocket, session: AsyncSession) -> User | None:
    """Authenticate a WebSocket using ``?token=`` or the ``Authorization`` header."""
    token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if not token:
        header = websocket.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
    if not token:
        return None
    try:
        return await _user_from_token(session, token)
    except HTTPException:
        return None


# ===========================================================================
# Rate limiting (in-process sliding window)
# ===========================================================================
_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request, bucket: str) -> str:
    # Uvicorn's proxy-headers middleware resolves forwarded addresses only from
    # configured trusted proxies. Reading X-Forwarded-For here would let any
    # caller rotate the header and bypass per-IP limits.
    ip = request.client.host if request.client else None
    return f"{bucket}:{ip or 'unknown'}"


def _hit(key: str, limit: int, window: int) -> bool:
    """Record a hit; return True when the caller is still under the limit."""
    now = time.monotonic()
    bucket = _buckets[key]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def rate_limit(bucket: str, limit: int | None = None, window: int | None = None):
    """Dependency factory enforcing a per-IP sliding window."""

    async def _dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        key = _client_key(request, bucket)
        if not _hit(key, limit or settings.rate_limit_requests, window or settings.rate_limit_window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Juda ko'p so'rov yuborildi. Birozdan so'ng qayta urinib ko'ring.",
                headers={"Retry-After": str(window or settings.rate_limit_window_seconds)},
            )

    return _dependency


auth_rate_limit = rate_limit(
    "auth",
    settings.auth_rate_limit_requests,
    settings.auth_rate_limit_window_seconds,
)


def reset_rate_limits() -> None:
    """Used by the test-suite."""
    _buckets.clear()

"""Async SQLAlchemy engine / session wiring.

Works against PostgreSQL (asyncpg) in production and SQLite (aiosqlite) as a
zero-config fallback for local development and tests.
"""

from __future__ import annotations

import ssl as ssl_module
from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""


def normalize_database_url(raw: str) -> tuple[str, dict]:
    """Turn a hosted Postgres URL into something asyncpg understands.

    Railway, Heroku and Supabase all hand out ``postgres://`` (or
    ``postgresql://``) URLs, sometimes with libpq-only query parameters such as
    ``sslmode=require``.  asyncpg wants the ``postgresql+asyncpg://`` scheme and
    an ``ssl`` connect argument instead, so we translate here.

    Returns ``(url, connect_args)``.
    """
    url = (raw or "").strip()
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    elif url.startswith("postgresql+psycopg2://"):
        url = "postgresql+asyncpg://" + url[len("postgresql+psycopg2://") :]

    connect_args: dict = {}
    if url.startswith("sqlite"):
        return url, connect_args

    parts = urlsplit(url)
    keep: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower in {"sslmode", "ssl"}:
            if value.lower() in {"require", "verify-ca", "verify-full", "true", "1"}:
                connect_args["ssl"] = (
                    ssl_module.create_default_context()
                    if value.lower() == "verify-full"
                    else True
                )
            elif value.lower() in {"disable", "false", "0"}:
                connect_args["ssl"] = False
        elif key_lower in {"channel_binding", "options"}:
            continue  # libpq-only, asyncpg rejects it
        else:
            keep.append((key, value))

    normalized = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(keep), parts.fragment)
    )
    return normalized, connect_args


DATABASE_URL, CONNECT_ARGS = normalize_database_url(settings.database_url)
IS_SQLITE = DATABASE_URL.startswith("sqlite")


def _engine_kwargs() -> dict:
    kwargs: dict = {
        "echo": settings.db_echo,
        "pool_pre_ping": True,
        "future": True,
    }
    if CONNECT_ARGS:
        kwargs["connect_args"] = CONNECT_ARGS
    if IS_SQLITE:
        # SQLite needs no pooling configuration for a single-process dev server.
        return kwargs
    kwargs.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=1800,
    )
    return kwargs


engine = create_async_engine(DATABASE_URL, **_engine_kwargs())

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_all() -> None:
    from . import models  # noqa: F401  (ensure models are imported/registered)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all() -> None:
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def dispose_engine() -> None:
    await engine.dispose()

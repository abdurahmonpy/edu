"""Health-check endpoints used by Railway and uptime monitors."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from .. import __version__
from ..config import settings
from ..database import IS_SQLITE, SessionLocal, engine
from ..utils import utcnow

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
        "database": "sqlite" if IS_SQLITE else "postgresql",
        "time": utcnow(),
    }


@router.get("/health/ready", summary="Readiness probe (touches the database)")
async def readiness(response: Response) -> dict:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "up"}
    except Exception as exc:  # noqa: BLE001 - report any driver/connection failure
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "down", "error": str(exc)[:200]}


@router.get("/health/db")
async def database_info() -> dict:
    dialect = engine.dialect.name
    pool = {}
    if not IS_SQLITE:
        pool = {
            "size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
        }
    return {"dialect": dialect, "driver": engine.dialect.driver, "pool": pool}

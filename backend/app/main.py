"""FastAPI application entrypoint.

Railway runs a single service that serves both the JSON API (``/api/v1``) and
the static HTML frontend from the repository root, so the pages can call the API
on the same origin without any CORS or base-URL configuration.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import settings
from .database import create_all, dispose_engine
from .routers import (
    admin,
    auth,
    battles,
    chat,
    courses,
    events,
    health,
    leaderboard,
    leads,
    library,
    notifications,
    users,
    vocabulary,
    ws,
)

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("englify")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s v%s (env=%s, db=%s)",
        settings.app_name,
        __version__,
        settings.environment,
        "sqlite" if settings.is_sqlite else "postgres",
    )
    if settings.auto_create_tables:
        await create_all()
        logger.info("Database schema is up to date.")
    if settings.seed_demo_data:
        from .seed import seed_all

        await seed_all()
    yield
    await dispose_engine()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Englify o'quv platformasi uchun REST + WebSocket API. "
        "Auth (JWT), kurslar va progress, lug'at (SRS), chat, janglar, "
        "reyting, tadbirlar va kutubxona."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# --------------------------------------------------------------------- CORS
origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app" if origins == ["*"] else None,
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    import time

    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - started) * 1000:.1f}ms"
    return response


# ---------------------------------------------------------------- exception
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Flatten Pydantic errors into one readable Uzbek-friendly message."""
    messages: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()) if part != "body")
        messages.append(f"{location}: {error.get('msg')}" if location else str(error.get("msg")))
    return JSONResponse(
        status_code=422,
        content={"detail": "Ma'lumotlar noto'g'ri.", "errors": messages},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse | FileResponse:
    """JSON for API routes, the pretty HTML page for browser navigations."""
    accepts_html = "text/html" in request.headers.get("accept", "")
    is_api = request.url.path.startswith(API) or request.url.path.startswith("/api")

    if exc.status_code == 404 and accepts_html and not is_api and settings.serve_frontend:
        page = settings.static_dir / "404.html"
        if page.exists():
            return FileResponse(page, status_code=404)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    detail = "Serverda kutilmagan xatolik yuz berdi."
    if not settings.is_production:
        detail = f"{type(exc).__name__}: {exc}"
    return JSONResponse(status_code=500, content={"detail": detail})


# -------------------------------------------------------------------- routers
API = settings.api_prefix
app.include_router(health.router)  # /health, /health/ready, /health/db
app.include_router(health.router, prefix=API)
app.include_router(auth.router, prefix=API)
app.include_router(admin.router, prefix=API)
app.include_router(users.router, prefix=API)
app.include_router(courses.router, prefix=API)
app.include_router(vocabulary.router, prefix=API)
app.include_router(notifications.router, prefix=API)
app.include_router(chat.router, prefix=API)
app.include_router(leaderboard.router, prefix=API)
app.include_router(battles.router, prefix=API)
app.include_router(events.router, prefix=API)
app.include_router(library.router, prefix=API)
app.include_router(leads.router, prefix=API)
app.include_router(ws.router, prefix=API)


@app.get(f"{API}", tags=["meta"], summary="API metadata")
async def api_index() -> dict:
    return {
        "name": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
        "google_client_id": settings.google_client_id,
        "docs": "/docs",
        "endpoints": {
            "auth": f"{API}/auth",
            "admin": f"{API}/admin",
            "users": f"{API}/users",
            "courses": f"{API}/courses",
            "vocabulary": f"{API}/vocabulary",
            "notifications": f"{API}/notifications",
            "chat": f"{API}/chat",
            "leaderboard": f"{API}/leaderboard",
            "battles": f"{API}/battles",
            "events": f"{API}/events",
            "library": f"{API}/books | {API}/podcasts | {API}/games | {API}/levels",
            "leads": f"{API}/leads",
            "realtime": f"{API}/ws/chat/{{id}} | {API}/ws/battles/{{id}} | {API}/ws/notifications",
        },
    }


@app.get(f"{API}/config", tags=["meta"], summary="Public client configuration")
async def public_config() -> dict:
    return {"google_client_id": settings.google_client_id}


# ===========================================================================
# Static frontend
# ===========================================================================
class FrontendFiles(StaticFiles):
    """Static handler with ``cleanUrls`` support and a source-file denylist.

    Only an explicit allowlist of web asset extensions is served, and no path
    segment may start with a dot or live in a blocked top-level directory.  That
    keeps ``backend/``, ``.env``, ``.git/`` and the local SQLite file private
    even though the frontend lives in the repository root.
    """

    ALLOWED_SUFFIXES = {
        ".html",
        ".css",
        ".js",
        ".mjs",
        ".json",
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".ico",
        ".mp3",
        ".mp4",
        ".webm",
        ".woff",
        ".woff2",
        ".ttf",
        ".txt",
        ".xml",
        ".webmanifest",
        ".pdf",
    }
    ROUTE_ALIASES = {
        "login": "kirish.html",
        "register": "kirish.html",
        "dashboard": "app.html",
        "settings": "settings.html",
    }
    #: Never expose the backend source, env files, git metadata or internal docs.
    BLOCKED_TOP_LEVEL = {
        "backend",
        "docs",
        "node_modules",
        "tests",
        "scripts",
        "static",
        "__pycache__",
        ".venv",
        "venv",
    }
    #: Individually blocked files that would otherwise match the allowlist.
    BLOCKED_FILES = {
        "requirements.txt",
        "requirements-dev.txt",
        "railway.json",
        "pytest.ini",
        "dockerfile",
        "docker-compose.yml",
    }

    @staticmethod
    def _segments(path: str) -> list[str]:
        return [part for part in path.replace("\\", "/").split("/") if part not in ("", ".")]

    def _is_blocked(self, path: str) -> bool:
        segments = self._segments(path)
        if not segments:
            return False
        if any(segment.startswith(".") for segment in segments):
            return True
        if segments[0].lower() in self.BLOCKED_TOP_LEVEL:
            return True
        return segments[-1].lower() in self.BLOCKED_FILES

    def _clean_url_target(self, path: str) -> str | None:
        """Return ``path + '.html'`` when that file exists inside the root."""
        try:
            root = Path(self.directory).resolve()
            candidate = (root / f"{path}.html").resolve()
        except (OSError, ValueError):
            return None
        if not str(candidate).startswith(str(root)):
            return None  # path traversal attempt
        return f"{path}.html" if candidate.is_file() else None

    def resolve_path(self, path: str) -> str | None:
        """Map a request path to a servable file, or ``None`` to reject it.

        This is the single decision point used by :meth:`get_response`, and it is
        unit-tested directly.
        """
        normalized = path.replace("\\", "/").strip("/")
        if normalized in ("", "."):
            normalized = "index.html"

        if self._is_blocked(normalized):
            return None

        if normalized in self.ROUTE_ALIASES:
            return self.ROUTE_ALIASES[normalized]

        suffix = Path(normalized).suffix.lower()
        if suffix == "":
            # ``cleanUrls``: /app -> app.html. Extension-less real files
            # (Dockerfile, Procfile, LICENSE, ...) are never served.
            return self._clean_url_target(normalized)
        if suffix not in self.ALLOWED_SUFFIXES:
            return None
        return normalized

    async def get_response(self, path: str, scope):  # type: ignore[override]
        target = self.resolve_path(path)
        if target is None:
            raise StarletteHTTPException(status_code=404, detail="Not found")
        return await super().get_response(target, scope)


if settings.serve_frontend and settings.static_dir.exists():
    @app.get("/kirish", include_in_schema=False)
    async def legacy_login_url() -> RedirectResponse:
        return RedirectResponse("/login", status_code=307)

    @app.get("/app", include_in_schema=False)
    async def legacy_dashboard_url() -> RedirectResponse:
        return RedirectResponse("/dashboard", status_code=307)

    app.mount(
        "/",
        FrontendFiles(directory=str(settings.static_dir), html=True),
        name="frontend",
    )
    logger.info("Serving frontend from %s", settings.static_dir)
else:
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {"name": settings.app_name, "docs": "/docs"}


@app.get("/404", include_in_schema=False)
async def not_found_page() -> FileResponse:
    return FileResponse(settings.static_dir / "404.html", status_code=404)

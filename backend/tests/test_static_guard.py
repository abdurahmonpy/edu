"""Unit tests for the static frontend handler's path guard.

The frontend lives in the repository root next to the backend, so the guard is
the only thing preventing ``/.env`` or ``/backend/app/config.py`` from being
served as static files.
"""

from __future__ import annotations

import pytest
from backend.app.main import FrontendFiles


@pytest.fixture(scope="module")
def handler() -> FrontendFiles:
    from backend.app.config import settings

    return FrontendFiles(directory=str(settings.static_dir), html=True)


BLOCKED = [
    "backend",
    "backend/app/main.py",
    "backend/requirements.txt",
    "backend/.env.example",
    ".env",
    ".git/config",
    "docs/spec-social.md",
    "Dockerfile",
    "Procfile",
    "requirements.txt",
    "requirements-dev.txt",
    "railway.json",
    "dev_englify.db",
    "tests/conftest.py",
    "__pycache__/main.cpython-314.pyc",
    "assets/../../backend/app/config.py",
    "/../backend/app/config.py",
]

ALLOWED = [
    "index.html",
    "app.html",
    "kirish.html",
    "settings.html",
    "assets/js/api.js",
    "assets/js/config.js",
    "404.html",
    "vercel.json",
]


@pytest.mark.parametrize("path", BLOCKED)
def test_blocked_paths_resolve_to_nothing(handler, path):
    assert handler.resolve_path(path) is None, f"{path} must not be served"


@pytest.mark.parametrize("path", ALLOWED)
def test_allowed_paths_resolve(handler, path):
    assert handler.resolve_path(path) == path, f"{path} should be servable"


def test_root_serves_index(handler):
    assert handler.resolve_path("") == "index.html"
    assert handler.resolve_path(".") == "index.html"
    assert handler.resolve_path("/") == "index.html"


def test_clean_url_resolves_html_files(handler):
    assert handler.resolve_path("app") == "app.html"
    assert handler.resolve_path("kirish") == "kirish.html"
    assert handler.resolve_path("dars") == "dars.html"


def test_named_auth_and_dashboard_routes(handler):
    assert handler.resolve_path("login") == "kirish.html"
    assert handler.resolve_path("register") == "kirish.html"
    assert handler.resolve_path("dashboard") == "app.html"
    assert handler.resolve_path("settings") == "settings.html"


def test_clean_url_rejects_missing_and_extensionless(handler):
    assert handler._clean_url_target("yoq-sahifa") is None
    assert handler._clean_url_target("Dockerfile") is None
    assert handler._clean_url_target("requirements") is None


def test_clean_url_cannot_escape_the_root(handler):
    assert handler._clean_url_target("../secrets") is None
    assert handler._clean_url_target("../../etc/passwd") is None


def test_disallowed_extension_is_rejected(handler):
    for path in ("backend/app/config.pyc", "notes.md", "data.sqlite3", "app.exe"):
        assert handler.resolve_path(path) is None

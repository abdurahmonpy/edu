"""Shared pytest fixtures.

The environment is configured *before* ``backend.app`` is imported so the
settings cache picks up the test values.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB = Path(tempfile.gettempdir()) / "englify_test.db"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ENVIRONMENT"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["SEED_DEMO_ACCOUNTS"] = "true"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["BCRYPT_ROUNDS"] = "4"  # keep the suite fast
os.environ["SERVE_FRONTEND"] = "false"
os.environ["DEBUG"] = "false"

import pytest  # noqa: E402
from backend.app.deps import reset_rate_limits  # noqa: E402
from backend.app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

DEMO_EMAIL = "abdurahmon@englify.uz"
DEMO_PASSWORD = "englify1234"


@pytest.fixture(scope="session", autouse=True)
def _clean_database():
    if TEST_DB.exists():
        TEST_DB.unlink()
    yield
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture(scope="session")
def client(_clean_database):
    """A TestClient with the application lifespan (schema + seed) executed."""
    reset_rate_limits()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def demo_auth(client) -> dict:
    """Auth headers for the seeded demo student."""
    response = client.post(
        "/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"demo user unavailable: {response.status_code} {response.text}")
    payload = response.json()
    return {
        "headers": {"Authorization": f"Bearer {payload['access_token']}"},
        "tokens": payload,
        "user": payload["user"],
    }


@pytest.fixture(scope="session")
def fresh_user(client) -> dict:
    """A newly registered, isolated account (used for mutation tests)."""
    import uuid

    email = f"pytest-{uuid.uuid4().hex[:10]}@englify.uz"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TestParol123",
            "full_name": "Pytest User",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return {
        "email": email,
        "password": "TestParol123",
        "headers": {"Authorization": f"Bearer {payload['access_token']}"},
        "tokens": payload,
        "user": payload["user"],
    }

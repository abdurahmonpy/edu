"""Auth flow tests: register, login, refresh rotation, profile, passwords."""

from __future__ import annotations

import uuid

import pytest
from backend.app.deps import _client_key
from backend.tests.conftest import DEMO_EMAIL, DEMO_PASSWORD
from starlette.requests import Request


def test_production_rejects_weak_jwt_secret():
    from backend.app.config import Settings

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://user:pass@host/db",
            public_base_url="https://englify.example",
            secret_key="dev-insecure-secret-change-me",
        )


def test_production_rejects_ephemeral_sqlite_database():
    from backend.app.config import Settings

    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings(
            environment="production",
            secret_key="a" * 64,
            database_url="sqlite+aiosqlite:///./englify.db",
        )


def test_production_requires_public_https_base_url_when_smtp_is_enabled():
    from backend.app.config import Settings

    with pytest.raises(ValueError, match="PUBLIC_BASE_URL"):
        Settings(
            environment="production",
            secret_key="a" * 64,
            database_url="postgresql+asyncpg://user:pass@host/db",
            public_base_url="http://127.0.0.1:8000",
            smtp_host="smtp.example.test",
            smtp_from_email="noreply@example.test",
        )


def test_production_rejects_demo_accounts():
    from backend.app.config import Settings

    with pytest.raises(ValueError, match="SEED_DEMO_ACCOUNTS"):
        Settings(
            environment="production",
            secret_key="a" * 64,
            database_url="postgresql+asyncpg://user:pass@host/db",
            public_base_url="https://englify.example",
            seed_demo_accounts=True,
        )


def test_production_rejects_exposed_password_reset_tokens():
    from backend.app.config import Settings

    with pytest.raises(ValueError, match="EXPOSE_RESET_TOKEN"):
        Settings(
            environment="production",
            secret_key="a" * 64,
            database_url="postgresql+asyncpg://user:pass@host/db",
            public_base_url="https://englify.example",
            expose_reset_token=True,
        )


def test_rate_limit_does_not_trust_caller_supplied_forwarded_for():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", b"203.0.113.45")],
        "client": ("198.51.100.17", 1234),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
        "http_version": "1.1",
        "root_path": "",
    }
    assert _client_key(Request(scope), "auth") == "auth:198.51.100.17"


# ===========================================================================
# health
# ===========================================================================
def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_touches_database(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "up"


def test_api_index(client):
    response = client.get("/api/v1")
    assert response.status_code == 200
    assert "auth" in response.json()["endpoints"]


# ===========================================================================
# registration
# ===========================================================================
def test_register_returns_tokens_and_user(client):
    email = f"reg-{uuid.uuid4().hex[:8]}@englify.uz"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "KuchliParol1", "full_name": "  Ali   Valiyev "},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == email
    assert body["user"]["full_name"] == "Ali Valiyev"  # whitespace collapsed
    assert body["user"]["points"] == 0
    assert body["user"]["level"] == "starter"
    assert body["user"]["level_title"] == "Starter"


def test_register_duplicate_email_conflicts(client, fresh_user):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": fresh_user["email"],
            "password": "BoshqaParol1",
            "full_name": "Boshqa Odam",
        },
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"weak-{uuid.uuid4().hex[:8]}@englify.uz",
            "password": "abc",
            "full_name": "Zaif Parol",
        },
    )
    assert response.status_code == 422
    assert "8" in response.text


def test_register_rejects_bad_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "KuchliParol1", "full_name": "Test Odam"},
    )
    assert response.status_code == 422


def test_new_account_is_bootstrapped_with_chat_and_notification(client, fresh_user):
    headers = fresh_user["headers"]

    notifications = client.get("/api/v1/notifications", headers=headers).json()
    assert notifications["total"] >= 1
    assert any("xush kelibsiz" in item["title"].lower() for item in notifications["items"])

    conversations = client.get("/api/v1/chat/conversations", headers=headers).json()
    titles = {item["title"] for item in conversations}
    assert "Support Service" in titles
    assert any("Alomat" in title for title in titles)

    stats = client.get("/api/v1/users/me/stats", headers=headers).json()
    assert len(stats["skills"]) == 5
    assert {skill["skill"] for skill in stats["skills"]} == {
        "vocabulary",
        "writing",
        "reading",
        "listening",
        "grammar",
    }


# ===========================================================================
# login
# ===========================================================================
def test_login_success(client, fresh_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": fresh_user["email"], "password": fresh_user["password"]},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == fresh_user["email"]


def test_login_is_case_insensitive_on_email(client, fresh_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": fresh_user["email"].upper(), "password": fresh_user["password"]},
    )
    assert response.status_code == 200


def test_login_wrong_password_is_generic_401(client, fresh_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": fresh_user["email"], "password": "Noto'g'riParol1"},
    )
    assert response.status_code == 401
    assert "parol" in response.json()["detail"].lower()


def test_login_unknown_email_same_message(client):
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "yoq-bunday@englify.uz", "password": "KuchliParol1"},
    )
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": "XatoParol123"},
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_demo_user_can_log_in(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
    )
    assert response.status_code == 200


# ===========================================================================
# tokens
# ===========================================================================
def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code
        == 401
    )


def test_me_returns_current_user(client, fresh_user):
    response = client.get("/api/v1/auth/me", headers=fresh_user["headers"])
    assert response.status_code == 200
    assert response.json()["id"] == fresh_user["user"]["id"]


def test_refresh_rotates_and_invalidates_old_token(client, fresh_user):
    refresh_token = fresh_user["tokens"]["refresh_token"]

    first = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200, first.text
    new_tokens = first.json()
    assert new_tokens["refresh_token"] != refresh_token

    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401

    second = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert second.status_code == 200
    # keep the freshest pair for later tests
    fresh_user["tokens"] = second.json()
    fresh_user["headers"] = {"Authorization": f"Bearer {second.json()['access_token']}"}


def test_logout_revokes_refresh_token(client, fresh_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": fresh_user["email"], "password": fresh_user["password"]},
    ).json()
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"refresh_token": login["refresh_token"]},
    )
    assert response.status_code == 200
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
        ).status_code
        == 401
    )


# ===========================================================================
# profile
# ===========================================================================
def test_update_profile(client, fresh_user):
    response = client.patch(
        "/api/v1/auth/me",
        headers=fresh_user["headers"],
        json={"full_name": "Yangi Ism", "bio": "Ingliz tili o'rganaman", "daily_goal_minutes": 30},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "Yangi Ism"
    assert body["daily_goal_minutes"] == 30

    reread = client.get("/api/v1/auth/me", headers=fresh_user["headers"]).json()
    assert reread["full_name"] == "Yangi Ism"


def test_daily_goal_is_validated(client, fresh_user):
    response = client.patch(
        "/api/v1/auth/me", headers=fresh_user["headers"], json={"daily_goal_minutes": 5000}
    )
    assert response.status_code == 422


# ===========================================================================
# passwords
# ===========================================================================
def test_change_password_and_login_with_new_one(client, fresh_user):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=fresh_user["headers"],
        json={"current_password": fresh_user["password"], "new_password": "YangiParol99"},
    )
    assert response.status_code == 200, response.text

    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": fresh_user["email"], "password": fresh_user["password"]},
        ).status_code
        == 401
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": fresh_user["email"], "password": "YangiParol99"},
    )
    assert login.status_code == 200

    fresh_user["password"] = "YangiParol99"
    fresh_user["headers"] = {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_change_password_rejects_wrong_current(client, fresh_user):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=fresh_user["headers"],
        json={"current_password": "ButunlayXato1", "new_password": "YanaBoshqa1"},
    )
    assert response.status_code == 400


def test_forgot_and_reset_password(client, fresh_user, monkeypatch):
    forgot = client.post(
        "/api/v1/auth/forgot-password", json={"email": fresh_user["email"]}
    )
    assert forgot.status_code == 200

    # the token is only exposed when EXPOSE_RESET_TOKEN is on
    from backend.app.config import settings
    from backend.app.routers import auth

    delivered = []

    async def fake_send_email(email, token):
        delivered.append((email, token))
        return True

    monkeypatch.setattr(auth, "send_password_reset_email", fake_send_email)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@example.test")
    monkeypatch.setattr(settings, "expose_reset_token", True)
    with_token = client.post(
        "/api/v1/auth/forgot-password", json={"email": fresh_user["email"]}
    ).json()
    token = with_token["reset_token"]
    assert token
    assert delivered == [(fresh_user["email"], token)]

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "TiklanganParol7"},
    )
    assert reset.status_code == 200, reset.text

    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": fresh_user["email"], "password": "TiklanganParol7"},
        ).status_code
        == 200
    )

    reused = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "YanaBoshqaParol1"},
    )
    assert reused.status_code == 400  # single use

    fresh_user["password"] = "TiklanganParol7"


def test_forgot_password_does_not_leak_account_existence(client):
    response = client.post(
        "/api/v1/auth/forgot-password", json={"email": "mavjud-emas@englify.uz"}
    )
    assert response.status_code == 200
    assert response.json()["reset_token"] is None

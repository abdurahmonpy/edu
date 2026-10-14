"""Application settings.

All configuration comes from environment variables so the exact same image can
run locally, on Railway, or anywhere else.  See ``backend/.env.example`` for the
full list.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> backend/app -> backend -> <repo root>
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------------------------------------------------------- general
    app_name: str = "Englify API"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Public base URL of this service (used for links inside notifications).
    public_base_url: str = "http://127.0.0.1:8000"

    # --------------------------------------------------------------- database
    # Postgres on Railway, e.g.
    #   postgresql+asyncpg://postgres:pw@containers-us-west-x.railway.app:6543/railway
    # SQLite is used as a zero-config fallback for local development.
    database_url: str = "sqlite+aiosqlite:///./englify.db"
    db_echo: bool = False
    auto_create_tables: bool = True
    seed_demo_data: bool = True
    seed_demo_accounts: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 5

    # ------------------------------------------------------------------- auth
    secret_key: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day
    refresh_token_expire_days: int = 30
    password_min_length: int = 8
    bcrypt_rounds: int = 12
    # Number of failed logins before the account is temporarily locked.
    max_failed_logins: int = 10
    login_lockout_minutes: int = 15

    # ------------------------------------------------------------------- cors
    # Comma separated list, or "*" to allow everything.
    cors_origins: str = "*"

    # -------------------------------------------------------------- rate limit
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    auth_rate_limit_requests: int = 12
    auth_rate_limit_window_seconds: int = 60

    # --------------------------------------------------------------- email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Englify"
    smtp_starttls: bool = True

    # ------------------------------------------------------------------ misc
    # Serve the static HTML frontend from this service (single Railway app).
    serve_frontend: bool = True
    static_dir: Path = REPO_ROOT
    # Dev convenience: expose the password-reset token in the API response
    # because no SMTP provider is configured.  NEVER enable in production.
    expose_reset_token: bool = False

    leaderboard_min_activity: int = 0
    default_daily_goal_minutes: int = 20

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, value: str) -> str:
        return (value or "").strip()

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw in ("", "*"):
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith(("postgres://", "postgresql"))

    @property
    def smtp_is_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from_email)

    @model_validator(mode="after")
    def validate_production_auth_settings(self) -> Settings:
        if self.is_production:
            if not self.is_postgres:
                raise ValueError(
                    "Production DATABASE_URL must point to PostgreSQL; SQLite is not persistent on Railway."
                )
            if self.smtp_is_configured and not self.public_base_url.startswith("https://"):
                raise ValueError(
                    "PUBLIC_BASE_URL must be the public HTTPS URL when SMTP is configured."
                )
            if self.secret_key == "dev-insecure-secret-change-me" or len(self.secret_key) < 32:
                raise ValueError("Production SECRET_KEY must be a unique value of at least 32 characters.")
            if self.expose_reset_token:
                raise ValueError("EXPOSE_RESET_TOKEN cannot be enabled in production.")
            if self.seed_demo_accounts:
                raise ValueError("SEED_DEMO_ACCOUNTS must be disabled in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

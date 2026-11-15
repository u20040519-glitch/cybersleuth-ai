# =============================================================================
# CYBERSLEUTH AI - Application configuration
# =============================================================================
# All settings are environment-driven. Secrets never live in source control.
# `backend/.env` is gitignored; `backend/.env.example` documents every key.
# =============================================================================

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    """Runtime configuration, loaded from the environment and `backend/.env`."""

    model_config = SettingsConfigDict(
        # Only `backend/.env` is read. The repository-root `.env` belongs to
        # the frontend tooling and carries settings (such as a SQLite
        # DATABASE_URL) that do not apply to the API.
        env_file=(str(BACKEND_ROOT / ".env"),),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- Application ------------------------------------------------------
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    APP_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # --- Database ----------------------------------------------------------
    # Local development uses the portable PostgreSQL server managed by
    # `app.database.local_postgres`; the URL below is injected at startup when
    # it is not explicitly supplied.
    DATABASE_URL: str | None = None
    # Restricted runtime connection used by the API. When unset, the local
    # embedded server provisions the cybersleuth_app role automatically.
    APP_DATABASE_URL: str | None = None
    LOCAL_PG_DATA_DIR: str = str(BACKEND_ROOT / ".pgdata")
    LOCAL_PG_PORT: int = 5432

    # The API connects with a restricted, non-superuser role so that Row
    # Level Security is genuinely enforced by the database. In local
    # development the role is provisioned automatically by the bootstrap.
    APP_DB_USER: str = "cybersleuth_app"
    APP_DB_PASSWORD: str = "cybersleuth_local_dev"

    # --- Supabase (optional) ----------------------------------------------
    # When SUPABASE_URL is set the backend uses Supabase Storage for evidence
    # objects and (optionally) Supabase Auth for identities. When it is not
    # set the local auth provider and the on-disk storage backend are used.
    # The SQL schema and RLS policies are identical in both cases.
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # --- Authentication ----------------------------------------------------
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_COOKIE_NAME: str = "cybersleuth_session"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: str = "lax"
    ARGON2ID_MEMORY_COST: int = 65536
    ARGON2ID_TIME_COST: int = 3
    ARGON2ID_PARALLELISM: int = 4
    REGISTRATION_EMAIL_VERIFICATION_REQUIRED: bool = False

    # --- Evidence handling -------------------------------------------------
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt,json,csv,png,jpg,jpeg,tiff,mp3,wav,m4a,apk,zip,mp4,mov"
    UPLOAD_DIRECTORY: str = str(BACKEND_ROOT / "storage")
    STORAGE_BACKEND: str = "local"  # local | supabase

    # --- Forensics ---------------------------------------------------------
    # When false the forensic modules return `status: unavailable` instead of
    # running, for deployments that do not ship the scientific stack.
    FORENSIC_MODULES_ENABLED: bool = True
    SPACY_MODEL: str = "en_core_web_sm"

    # --- AI ----------------------------------------------------------------
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # --- Observability -----------------------------------------------------
    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "INFO"

    # --- CORS --------------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("ALLOWED_EXTENSIONS")
    @classmethod
    def _normalise_extensions(cls, v: str) -> str:
        return ",".join(sorted({e.strip().lower().lstrip(".") for e in v.split(",") if e.strip()}))

    @property
    def allowed_extension_set(self) -> set[str]:
        return {e for e in self.ALLOWED_EXTENSIONS.split(",") if e}

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def storage_root(self) -> Path:
        return Path(self.UPLOAD_DIRECTORY)

    @property
    def uses_supabase_storage(self) -> bool:
        return self.STORAGE_BACKEND == "supabase" and bool(self.SUPABASE_URL)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

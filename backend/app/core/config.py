# =============================================================================
# PROJECT NEXUS AI - Application Configuration
# =============================================================================
# Pydantic Settings with startup validation for required environment variables.
# Secrets are never printed to logs.
# =============================================================================

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=True)
    app_secret_key: str = Field(default="change-me")
    app_base_url: str = Field(default="http://localhost:8000")
    frontend_url: str = Field(default="http://localhost:3000")

    # --- Database ---
    database_url: str = Field(default="sqlite+aiosqlite:///./nexus_ai.db")

    # --- Security / Authentication ---
    argon2id_memory_cost: int = Field(default=65536)
    argon2id_time_cost: int = Field(default=3)
    argon2id_parallelism: int = Field(default=4)
    jwt_access_token_expire_minutes: int = Field(default=30)
    jwt_refresh_token_expire_days: int = Field(default=7)
    session_cookie_name: str = Field(default="nexus_session")
    session_cookie_secure: bool = Field(default=False)
    session_cookie_samesite: str = Field(default="lax")

    # --- Email (SMTP) ---
    smtp_host: Optional[str] = Field(default=None)
    smtp_port: int = Field(default=587)
    smtp_username: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    smtp_from_email: str = Field(default="noreply@example.com")
    smtp_from_name: str = Field(default="PROJECT NEXUS AI")
    email_verification_expire_hours: int = Field(default=24)
    password_reset_expire_hours: int = Field(default=1)

    # --- Gemini AI (backend only) ---
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-1.5-flash")
    gemini_api_base_url: str = Field(default="https://generativelanguage.googleapis.com")

    # --- Rate Limiting (Redis) ---
    redis_url: Optional[str] = Field(default=None)
    rate_limit_login_per_min: int = Field(default=5)
    rate_limit_register_per_min: int = Field(default=3)
    rate_limit_password_reset_per_min: int = Field(default=3)
    rate_limit_email_verify_per_min: int = Field(default=3)
    rate_limit_chatbot_per_min: int = Field(default=20)
    rate_limit_report_per_min: int = Field(default=5)
    rate_limit_upload_per_min: int = Field(default=10)

    # --- File Upload ---
    max_upload_size_mb: int = Field(default=100)
    allowed_extensions: str = Field(default="pdf,docx,txt,json,csv,png,jpg,jpeg,tiff")
    upload_directory: str = Field(default="./uploads")

    # --- Analytics ---
    analytics_provider: str = Field(default="none")
    analytics_write_key: Optional[str] = Field(default=None)
    analytics_api_url: str = Field(default="https://analytics.example.com")

    # --- Error Tracking ---
    sentry_dsn: Optional[str] = Field(default=None)
    sentry_environment: str = Field(default="development")
    sentry_release: str = Field(default="1.0.0")

    # --- Storage ---
    storage_provider: str = Field(default="local")
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    aws_s3_bucket: Optional[str] = Field(default=None)
    aws_s3_region: str = Field(default="us-east-1")

    # --- Backups ---
    backup_encryption_key: Optional[str] = Field(default=None)
    backup_retention_days: int = Field(default=30)
    backup_schedule_cron: str = Field(default="0 2 * * *")

    # --- Organization / Legal ---
    org_name: str = Field(default="PROJECT NEXUS AI (Academic Project)")
    org_address: Optional[str] = Field(default=None)
    org_support_email: str = Field(default="support@example.com")
    org_privacy_email: str = Field(default="privacy@example.com")
    org_website: Optional[str] = Field(default=None)
    org_legal_entity: str = Field(default="Academic / Student Project")
    policy_version: str = Field(default="1.0.0")
    policy_effective_date: str = Field(default="2026-11-13")

    # --- Security Features ---
    mfa_enabled: bool = Field(default=False)
    registration_email_verification_required: bool = Field(default=True)
    account_deletion_grace_period_days: int = Field(default=7)

    # --- Validation ---
    @field_validator("app_secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if not v or v == "change-me" or len(v) < 32:
            raise ValueError(
                "APP_SECRET_KEY must be set to a secure random string of at least 32 characters"
            )
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v

    def validate_required_secrets(self) -> List[str]:
        """Validate that all required secrets are configured. Returns list of missing items."""
        missing: List[str] = []
        if not self.app_secret_key or self.app_secret_key == "change-me":
            missing.append("APP_SECRET_KEY")
        if self.smtp_host and not self.smtp_username:
            missing.append("SMTP_USERNAME (required when SMTP_HOST is set)")
        if self.gemini_api_key and self.gemini_api_key == "change-me":
            missing.append("GEMINI_API_KEY (placeholder value)")
        if self.redis_url is None and self.app_env == "production":
            missing.append("REDIS_URL (required in production for rate limiting)")
        return missing

    def is_email_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_username and self.smtp_password)

    def is_gemini_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key != "change-me")

    def is_redis_configured(self) -> bool:
        return bool(self.redis_url)


settings = Settings()
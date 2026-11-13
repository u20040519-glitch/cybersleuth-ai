# =============================================================================
# PROJECT NEXUS AI - Main FastAPI Application
# =============================================================================
# App initialization, middleware, error handling, startup/shutdown events.
# =============================================================================

import logging
from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api import api_router
from app.api import cases, evidence, consent, echo, mosaic, timeglass, chatbot, reports, onboarding
from app.core.config import settings
from app.core.rate_limit import setup_rate_limiting
from app.db.database import init_db, close_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    logger.info("Starting PROJECT NEXUS AI backend...")

    # Initialize Sentry error tracking
    if settings.sentry_dsn and settings.sentry_dsn != "change-me":
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[
                FastApiIntegration(transaction_style="url"),
                SqlalchemyIntegration(),
            ],
            environment=settings.sentry_environment,
            release=settings.sentry_release,
            # Privacy: scrub sensitive data before sending to Sentry
            before_send=lambda event, hint: _scrub_sensitive_data(event),
            before_send_transaction=lambda event, hint: _scrub_sensitive_data(event),
            traces_sample_rate=0.1,
        )
        logger.info("Sentry error tracking initialized")
    else:
        logger.warning("Sentry DSN not configured - error tracking disabled")

    missing = settings.validate_required_secrets()
    if missing:
        logger.warning("Missing or placeholder secrets: %s", ", ".join(missing))

    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    await close_db()
    logger.info("Application shutdown complete")


# ---------------------------------------------------------------------------
# Create FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PROJECT NEXUS AI",
    description="Secure AI-assisted digital forensic investigation platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Rate limiting middleware
setup_rate_limiting(app)

# CORS - restrict to frontend URL in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, settings.app_base_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*"] if settings.app_debug else [settings.app_base_url],
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Return 429 with helpful message for rate-limited requests."""
    logger.warning("Rate limit exceeded for %s", request.client.host if request.client else "unknown")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.retry_after,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global error handler - never exposes stack traces or internals."""
    logger.error("Unhandled error: %s: %s", type(exc).__name__, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint. Does not expose internal infrastructure details."""
    return {
        "status": "healthy",
        "service": "PROJECT NEXUS AI",
        "version": "1.0.0",
        "environment": settings.app_env,
    }


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

app.include_router(api_router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(consent.router)
app.include_router(echo.router)
app.include_router(mosaic.router)
app.include_router(timeglass.router)
app.include_router(chatbot.router)
app.include_router(reports.router)
app.include_router(onboarding.router)


# ---------------------------------------------------------------------------
# Sentry sensitive data scrubbing
# ---------------------------------------------------------------------------

_SENSITIVE_FIELDS = {
    "password", "password_hash", "access_token", "refresh_token",
    "api_key", "secret", "session", "cookie", "authorization",
    "smtp_password", "gemini_api_key", "database_url",
}


def _scrub_value(key: str, value: any) -> any:
    """Recursively scrub sensitive values from event data."""
    if isinstance(key, str) and key.lower() in _SENSITIVE_FIELDS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: _scrub_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value("", v) for v in value]
    if isinstance(value, str):
        # Scrub potential secrets in strings
        import re
        # Scrub JWT-like tokens
        value = re.sub(
            r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
            "[JWT_REDACTED]",
            value,
        )
        # Scrub potential API keys (32+ hex chars)
        value = re.sub(r"\b[0-9a-f]{32,}\b", "[HASH_REDACTED]", value)
    return value


def _scrub_sensitive_data(event: dict, hint: any = None) -> dict:
    """Scrub sensitive data from Sentry events before transmission."""
    # Scrub request data
    if "request" in event and isinstance(event["request"], dict):
        req = event["request"]
        if "headers" in req and isinstance(req["headers"], dict):
            req["headers"] = {
                k: "[REDACTED]" if k.lower() in ("authorization", "cookie")
                else v
                for k, v in req["headers"].items()
            }
        if "data" in req:
            req["data"] = _scrub_value("", req["data"])
        if "query_string" in req and isinstance(req["query_string"], str):
            req["query_string"] = _scrub_value("", req["query_string"])

    # Scrub extra/contexts
    if "extra" in event and isinstance(event["extra"], dict):
        event["extra"] = _scrub_value("", event["extra"])
    if "contexts" in event and isinstance(event["contexts"], dict):
        event["contexts"] = _scrub_value("", event["contexts"])

    # Scrub breadcrumbs
    if "breadcrumbs" in event and isinstance(event["breadcrumbs"], dict):
        values = event["breadcrumbs"].get("values", [])
        for crumb in values:
            if isinstance(crumb, dict) and "data" in crumb:
                crumb["data"] = _scrub_value("", crumb["data"])

    return event
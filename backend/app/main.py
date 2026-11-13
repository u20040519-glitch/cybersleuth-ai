# =============================================================================
# PROJECT NEXUS AI - Main FastAPI Application
# =============================================================================
# App initialization, middleware, error handling, startup/shutdown events.
# =============================================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api import api_router
from app.api import cases, evidence, consent, echo, mosaic, timeglass, chatbot, reports, onboarding
from app.core.config import settings
from app.db.database import init_db, close_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def _get_remote_address(request: Request) -> str:
    """Get client IP for rate limiting (respects forwarded headers)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_get_remote_address)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    logger.info("Starting PROJECT NEXUS AI backend...")
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

# Rate limiter state
app.state.limiter = limiter

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
    logger.error("Unhandled error: %s", type(exc).__name__)
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
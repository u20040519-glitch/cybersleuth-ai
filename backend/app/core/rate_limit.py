# =============================================================================
# PROJECT NEXUS AI - Rate Limiting
# =============================================================================
# Custom middleware-based rate limiting for auth endpoints.
# Tracks request counts per IP address with configurable limits and cooldowns.
# =============================================================================

import logging
import time
from collections import defaultdict
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger(__name__)

# Rate limit configuration: path pattern -> (max_requests, window_seconds)
# In testing mode, use much higher limits to allow test execution
if settings.app_env == "testing":
    RATE_LIMIT_CONFIG = {
        "/api/auth/register": (60, 60),
        "/api/auth/login": (60, 60),
        "/api/auth/forgot-password": (60, 60),
        "/api/auth/reset-password": (60, 60),
        "/api/auth/resend-verification": (60, 60),
    }
else:
    RATE_LIMIT_CONFIG = {
        "/api/auth/register": (settings.rate_limit_register_per_min, 60),
        "/api/auth/login": (settings.rate_limit_login_per_min, 60),
        "/api/auth/forgot-password": (settings.rate_limit_password_reset_per_min, 60),
        "/api/auth/reset-password": (settings.rate_limit_password_reset_per_min, 60),
        "/api/auth/resend-verification": (settings.rate_limit_email_verify_per_min, 60),
    }

# In-memory store: {identifier: {path: [(timestamp,)]}} for dev
# Production should use Redis
_rate_store: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def _get_client_id(request: Request) -> str:
    """Get client identifier for rate limiting (IP-based)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _is_rate_limited(client_id: str, path: str) -> tuple[bool, Optional[int]]:
    """Check if client is rate limited for the given path.
    Returns (is_limited, retry_after_seconds)."""
    if path not in RATE_LIMIT_CONFIG:
        return False, None

    max_requests, window_seconds = RATE_LIMIT_CONFIG[path]
    now = time.time()

    # Clean old entries outside the window
    window_start = now - window_seconds
    _rate_store[client_id][path] = [
        ts for ts in _rate_store[client_id][path] if ts > window_start
    ]

    if len(_rate_store[client_id][path]) >= max_requests:
        # Calculate retry_after from the oldest request in the window
        oldest = min(_rate_store[client_id][path])
        retry_after = int(oldest + window_seconds - now) + 1
        return True, max(retry_after, 1)

    # Record this request
    _rate_store[client_id][path].append(now)
    return False, None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limits on configured paths."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Only check rate limits for configured paths
        path = request.url.path

        if path in RATE_LIMIT_CONFIG:
            client_id = _get_client_id(request)
            limited, retry_after = _is_rate_limited(client_id, path)

            if limited:
                logger.warning(
                    "Rate limit exceeded: client=%s path=%s retry_after=%s",
                    client_id, path, retry_after,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)} if retry_after else {},
                )

        response = await call_next(request)
        return response


def setup_rate_limiting(app):
    """Add rate limiting middleware to the FastAPI app."""
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limiting middleware configured")

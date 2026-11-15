# =============================================================================
# CYBERSLEUTH AI - FastAPI application
# =============================================================================
# The API owns authorisation, evidence integrity and the forensic pipeline.
# The frontend is a client of this service and holds no secrets.
# =============================================================================

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analysis, audit, auth, correlation, dashboard, evidence, health, investigations, reports
from app.core.config import settings
from app.core.database import dispose_engine, get_engine

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
)
logger = logging.getLogger("cybersleuth")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the database, apply migrations and prepare storage."""
    logger.info("Starting CyberSleuth AI API (env=%s)", settings.APP_ENV)

    from app.database.bootstrap import bootstrap_database

    try:
        await bootstrap_database()
    except Exception:
        logger.exception("Could not bootstrap the database; the API will start but may fail requests")

    try:
        from app.services.storage import get_storage

        get_storage()
    except Exception:
        logger.exception("Could not initialise the storage backend")

    logger.info("CyberSleuth AI API ready on %s", settings.APP_BASE_URL)
    try:
        yield
    finally:
        await dispose_engine()
        logger.info("CyberSleuth AI API stopped")


app = FastAPI(
    title="CyberSleuth AI API",
    description=(
        "Backend for the CyberSleuth AI multimodal digital forensics platform. "
        "Owns authentication, evidence integrity, the forensic analysis pipeline, "
        "correlation and report generation."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Evidence-SHA256", "X-Report-SHA256", "Content-Disposition"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline browser security headers on every response.

    A Content-Security-Policy is deliberately not set here: this service only
    serves JSON/PDF/files, and a strict policy would only complicate the
    OpenAPI docs UI. Framing and MIME sniffing are locked down instead.
    """
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.APP_ENV.lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Return validation problems in a shape the frontend can display."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "The request body is not valid.",
            "errors": [
                {"loc": [str(part) for part in err.get("loc", [])], "msg": err.get("msg")}
                for err in exc.errors()
            ],
        },
    )


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
app.include_router(health.router, prefix="/api")
# A top-level alias keeps the service discoverable by orchestrators and by
# clients that do not use the `/api` prefix.
app.include_router(health.router, prefix="")
app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(investigations.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(correlation.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(analysis.listing_router, prefix="/api")

for module_router in analysis.routers.values():
    app.include_router(module_router, prefix="/api")


@app.get("/", tags=["health"])
async def root():
    """Service banner."""
    return {
        "service": "CyberSleuth AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }

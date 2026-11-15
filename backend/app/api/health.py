# =============================================================================
# CYBERSLEUTH AI - Health and readiness
# =============================================================================

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])

APP_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    """Report the readiness of every subsystem the platform depends on."""
    database_state = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database_state = "unavailable"

    storage_state = "ok"
    try:
        from app.services.storage import get_storage

        storage = get_storage()
        storage.root if hasattr(storage, "root") else None
    except Exception:
        storage_state = "unavailable"

    from app.api.analysis import _load_analyzer

    forensic_available = any(
        _load_analyzer(module)[1] for module in ("deeptrace", "spytrace", "voiceproof", "cybersleuth")
    )

    from app.services.gemini import get_gemini

    ai_available = get_gemini().is_configured

    return HealthResponse(
        status="ok" if database_state == "ok" else "degraded",
        version=APP_VERSION,
        database=database_state,
        storage=storage_state,
        forensic_modules=forensic_available,
        ai_explanation=ai_available,
        time=datetime.now(timezone.utc),
    )

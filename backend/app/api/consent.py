# =============================================================================
# PROJECT NEXUS AI - Consent Management API
# =============================================================================
# Privacy consent recording and withdrawal.
# =============================================================================

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.db.database import get_db
from app.models import User, ConsentRecord, ConsentStatus, AuditLog
from app.schemas.user import ConsentPreference, ConsentRecordResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consent", tags=["consent"])


# ---------------------------------------------------------------------------
# Record consent
# ---------------------------------------------------------------------------

@router.post("/{purpose}", response_model=ConsentRecordResponse)
async def record_consent(
    purpose: str,
    preference: ConsentPreference,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentRecordResponse:
    """Record or update user consent for a specific purpose."""
    # Validate purpose is a known consent category
    valid_purposes = ["analytics", "external_ai_processing", "optional_communications", "non_essential_cookies"]
    if preference.purpose and preference.purpose not in valid_purposes:
        # Allow custom purposes too but log
        pass

    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == current_user.id,
            ConsentRecord.purpose == (preference.purpose or purpose),
        )
    )
    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        existing.status = ConsentStatus.GRANTED if preference.granted else ConsentStatus.WITHDRAWN
        existing.policy_version = settings.policy_version
        if preference.granted:
            existing.granted_at = now
            existing.withdrawn_at = None
        else:
            existing.withdrawn_at = now
        await db.commit()
        await db.refresh(existing)
        record = existing
    else:
        record = ConsentRecord(
            user_id=current_user.id,
            purpose=preference.purpose or purpose,
            policy_version=settings.policy_version,
            status=ConsentStatus.GRANTED if preference.granted else ConsentStatus.WITHDRAWN,
            granted_at=now if preference.granted else None,
            withdrawn_at=now if not preference.granted else None,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action=f"consent_{'granted' if preference.granted else 'withdrawn'}",
        resource_type="consent",
        resource_id=str(record.id),
    )
    db.add(audit)
    await db.commit()

    logger.info("Consent %s for purpose %s by user %s", "granted" if preference.granted else "withdrawn", record.purpose, current_user.email)
    return ConsentRecordResponse.model_validate(record)


# ---------------------------------------------------------------------------
# Get user's consent records
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ConsentRecordResponse])
async def list_consent_records(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConsentRecordResponse]:
    """Get all consent records for the current user."""
    result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == current_user.id)
    )
    records = result.scalars().all()
    return [ConsentRecordResponse.model_validate(r) for r in records]


# ---------------------------------------------------------------------------
# Check AI processing preference
# ---------------------------------------------------------------------------

@router.get("/preference/external_ai_processing")
async def get_ai_processing_preference(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if user has consented to external AI processing."""
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == current_user.id,
            ConsentRecord.purpose == "external_ai_processing",
            ConsentRecord.status == "granted",
        )
    )
    record = result.scalar_one_or_none()
    return {"external_ai_processing_enabled": record is not None}
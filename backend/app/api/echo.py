# =============================================================================
# PROJECT NEXUS AI - ECHO Evidence Gap Discovery API
# =============================================================================
# Evidence gap discovery module.
# =============================================================================

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.db.database import get_db
from app.models import User, Case, EvidenceGap
from app.schemas.user import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/echo", tags=["echo"])


class EvidenceGapCreate:
    def __init__(self, gap_description: str, suggested_evidence: Optional[str] = None, priority: str = "medium"):
        self.gap_description = gap_description
        self.suggested_evidence = suggested_evidence
        self.priority = priority


@router.post("/cases/{case_id}/gaps")
async def create_evidence_gap(
    case_id: str,
    gap_description: str,
    suggested_evidence: Optional[str] = None,
    priority: str = "medium",
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an evidence gap record for a case (ECHO module)."""
    try:
        case_uuid = UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case ID")

    result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if case.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    gap = EvidenceGap(
        case_id=case_uuid,
        gap_description=gap_description,
        suggested_evidence=suggested_evidence,
        priority=priority,
    )
    db.add(gap)
    await db.commit()
    await db.refresh(gap)

    return {
        "id": str(gap.id),
        "gap_description": gap.gap_description,
        "suggested_evidence": gap.suggested_evidence,
        "priority": gap.priority,
        "created_at": gap.created_at,
    }


@router.get("/cases/{case_id}/gaps")
async def list_evidence_gaps(
    case_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List evidence gaps for a case."""
    try:
        case_uuid = UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case ID")

    result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if case.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    result = await db.execute(
        select(EvidenceGap).where(EvidenceGap.case_id == case_uuid)
    )
    gaps = result.scalars().all()

    return [
        {
            "id": str(g.id),
            "gap_description": g.gap_description,
            "suggested_evidence": g.suggested_evidence,
            "priority": g.priority,
            "created_at": g.created_at,
        }
        for g in gaps
    ]
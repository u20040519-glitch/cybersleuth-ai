# =============================================================================
# PROJECT NEXUS AI - TIMEGLASS Temporal Analysis API
# =============================================================================
# Timeline/event analysis module.
# =============================================================================

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.models import User, Case, Event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/timeglass", tags=["timeglass"])


@router.post("/cases/{case_id}/events")
async def create_event(
    case_id: str,
    event_timestamp: str,
    event_description: str,
    source_evidence_id: Optional[str] = None,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a timeline event for a case (TIMEGLASS module)."""
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

    # Parse timestamp
    try:
        ts = datetime.fromisoformat(event_timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp format")

    source_uuid = None
    if source_evidence_id:
        try:
            source_uuid = UUID(source_evidence_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid evidence ID")

    event = Event(
        case_id=case_uuid,
        event_timestamp=ts,
        event_description=event_description,
        source_evidence_id=source_uuid,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    return {
        "id": str(event.id),
        "event_timestamp": event.event_timestamp.isoformat(),
        "event_description": event.event_description,
        "source_evidence_id": str(event.source_evidence_id) if event.source_evidence_id else None,
        "created_at": event.created_at,
    }


@router.get("/cases/{case_id}/events")
async def list_events(
    case_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List timeline events for a case, ordered by timestamp."""
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
        select(Event).where(Event.case_id == case_uuid).order_by(Event.event_timestamp)
    )
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "event_timestamp": e.event_timestamp.isoformat(),
            "event_description": e.event_description,
            "source_evidence_id": str(e.source_evidence_id) if e.source_evidence_id else None,
            "created_at": e.created_at,
        }
        for e in events
    ]
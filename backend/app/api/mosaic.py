# =============================================================================
# PROJECT NEXUS AI - MOSAIC Scenario Reconstruction API
# =============================================================================
# Scenario reconstruction module.
# =============================================================================

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.models import User, Case, Scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mosaic", tags=["mosaic"])


@router.post("/cases/{case_id}/scenarios")
async def create_scenario(
    case_id: str,
    scenario_name: str,
    scenario_description: str,
    confidence_level: Optional[str] = None,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a reconstructed scenario for a case (MOSAIC module)."""
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

    scenario = Scenario(
        case_id=case_uuid,
        scenario_name=scenario_name,
        scenario_description=scenario_description,
        confidence_level=confidence_level,
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)

    return {
        "id": str(scenario.id),
        "scenario_name": scenario.scenario_name,
        "scenario_description": scenario.scenario_description,
        "confidence_level": scenario.confidence_level,
        "created_at": scenario.created_at,
    }


@router.get("/cases/{case_id}/scenarios")
async def list_scenarios(
    case_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List scenarios for a case."""
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
        select(Scenario).where(Scenario.case_id == case_uuid)
    )
    scenarios = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "scenario_name": s.scenario_name,
            "scenario_description": s.scenario_description,
            "confidence_level": s.confidence_level,
            "created_at": s.created_at,
        }
        for s in scenarios
    ]
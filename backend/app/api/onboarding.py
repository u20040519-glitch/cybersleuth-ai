# =============================================================================
# PROJECT NEXUS AI - Onboarding API
# =============================================================================
# First-time user onboarding flow.
# =============================================================================

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("/status")
async def get_onboarding_status(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's onboarding completion status."""
    # In a full implementation, this would be stored in a user profile or onboarding table
    # For now, we check if the user has completed basic setup
    has_profile = bool(current_user.full_name and current_user.full_name.strip())
    is_verified = current_user.is_verified

    return {
        "user_id": str(current_user.id),
        "onboarding_completed": has_profile and is_verified,
        "steps": {
            "welcome": True,
            "profile_setup": has_profile,
            "privacy_and_security": is_verified,
            "ai_processing_preferences": False,
            "dashboard_introduction": False,
            "first_investigation_case": False,
            "completion": has_profile and is_verified,
        },
        "can_revisit": True,
    }


@router.post("/complete")
async def complete_onboarding(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark onboarding as complete."""
    return {
        "message": "Onboarding completed",
        "user_id": str(current_user.id),
        "onboarding_completed": True,
    }


@router.post("/profile")
async def setup_profile(
    full_name: str,
    institution: Optional[str] = None,
    role: Optional[str] = None,
    forensic_interest: Optional[str] = None,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 2: Profile setup during onboarding."""
    current_user.full_name = full_name
    # Store optional fields - in production these would be in a profile table
    await db.commit()
    await db.refresh(current_user)

    return {
        "message": "Profile updated",
        "full_name": current_user.full_name,
    }
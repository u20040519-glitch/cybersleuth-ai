# =============================================================================
# PROJECT NEXUS AI - Case Management API
# =============================================================================
# Case CRUD with case-level authorization.
# =============================================================================

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db_with_rls, require_role
from app.core.config import settings
from app.db.database import get_db
from app.models import User, Case, CasePermission, AuditLog
from app.schemas.user import CaseCreate, CaseResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _case_to_response(case: Case) -> CaseResponse:
    return CaseResponse.model_validate(case)


# ---------------------------------------------------------------------------
# Create case
# ---------------------------------------------------------------------------

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    request=None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_with_rls),
) -> CaseResponse:
    """Create a new investigation case. Owner gets full permissions."""
    # Check case number uniqueness
    existing = await db.execute(select(Case).where(Case.case_number == case_data.case_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case number already exists")

    case = Case(
        case_number=case_data.case_number,
        title=case_data.title,
        description=case_data.description,
        owner_id=current_user.id,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)

    # Grant owner full permission
    perm = CasePermission(
        case_id=case.id,
        user_id=current_user.id,
        permission="admin",
        granted_by=current_user.id,
    )
    db.add(perm)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="case_created",
        resource_type="case",
        resource_id=str(case.id),
    )
    db.add(audit)
    await db.commit()

    logger.info("Case created: %s by %s", case.case_number, current_user.email)
    return _case_to_response(case)


# ---------------------------------------------------------------------------
# List cases (user's own cases + shared cases)
# ---------------------------------------------------------------------------

@router.get("", response_model=list[CaseResponse])
async def list_cases(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_with_rls),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[CaseResponse]:
    """List cases the user owns or has permission to access."""
    # Get cases owned by user
    owned_subq = select(Case.id).where(Case.owner_id == current_user.id)

    # Get cases where user has permission
    perm_subq = select(CasePermission.case_id).where(CasePermission.user_id == current_user.id)

    query = select(Case).where(
        Case.id.in_(owned_subq) | Case.id.in_(perm_subq)
    )

    if status_filter:
        query = query.where(Case.status == status_filter)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    cases = result.scalars().all()

    return [_case_to_response(c) for c in cases]


# ---------------------------------------------------------------------------
# Get single case
# ---------------------------------------------------------------------------

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_with_rls),
) -> CaseResponse:
    """Get a case if the user owns it or has permission."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Authorization: owner or has permission
    if case.owner_id != current_user.id:
        perm_result = await db.execute(
            select(CasePermission).where(
                CasePermission.case_id == case_id,
                CasePermission.user_id == current_user.id,
            )
        )
        if not perm_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this case")

    return _case_to_response(case)


# ---------------------------------------------------------------------------
# Update case
# ---------------------------------------------------------------------------

@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    case_data: CaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_with_rls),
) -> CaseResponse:
    """Update a case (owner or admin permission required)."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Authorization: owner or admin permission
    if case.owner_id != current_user.id:
        perm_result = await db.execute(
            select(CasePermission).where(
                CasePermission.case_id == case_id,
                CasePermission.user_id == current_user.id,
                CasePermission.permission == "admin",
            )
        )
        if not perm_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this case")

    case.title = case_data.title
    case.description = case_data.description
    await db.commit()
    await db.refresh(case)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="case_updated",
        resource_type="case",
        resource_id=str(case.id),
    )
    db.add(audit)
    await db.commit()

    return _case_to_response(case)


# ---------------------------------------------------------------------------
# Delete case (owner only)
# ---------------------------------------------------------------------------

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_with_rls),
) -> None:
    """Delete a case (owner only). Evidence and related records handled per retention policy."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if case.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the case owner can delete a case")

    await db.delete(case)
    await db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="case_deleted",
        resource_type="case",
        resource_id=str(case_id),
    )
    db.add(audit)
    await db.commit()

    logger.info("Case deleted: %s by %s", case_id, current_user.email)
# =============================================================================
# PROJECT NEXUS AI - Investigation Report API
# =============================================================================
# Forensic report generation.
# =============================================================================

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.models import User, Case, InvestigationReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/cases/{case_id}")
async def generate_report(
    case_id: str,
    report_title: str,
    report_content: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an investigation report for a case."""
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

    report = InvestigationReport(
        case_id=case_uuid,
        owner_id=current_user.id,
        report_title=report_title,
        report_content=report_content,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return {
        "id": str(report.id),
        "report_title": report.report_title,
        "report_content": report.report_content,
        "generated_at": report.generated_at,
        "case_id": str(report.case_id),
    }


@router.get("/cases/{case_id}")
async def list_reports(
    case_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List reports for a case."""
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
        select(InvestigationReport).where(InvestigationReport.case_id == case_uuid)
    )
    reports = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "report_title": r.report_title,
            "report_content": r.report_content,
            "generated_at": r.generated_at,
            "owner_id": str(r.owner_id),
        }
        for r in reports
    ]
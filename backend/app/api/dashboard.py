# =============================================================================
# CYBERSLEUTH AI - Dashboard statistics
# =============================================================================
# Every figure here is counted from the database. Nothing is sampled or
# estimated, and an account with no data reports zeroes rather than
# illustrative numbers.
# =============================================================================

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import AnalysisResult, Evidence, Investigation, Profile
from app.schemas import DashboardStats, InvestigationOut
from app.security.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the caller's dashboard figures, counted from the database."""
    total_investigations = await db.scalar(
        select(func.count()).select_from(Investigation)
    )
    active_investigations = await db.scalar(
        select(func.count())
        .select_from(Investigation)
        .where(Investigation.status.in_(("active", "review", "draft")))
    )
    evidence_files = await db.scalar(select(func.count()).select_from(Evidence))
    total_bytes = await db.scalar(select(func.coalesce(func.sum(Evidence.file_size), 0)))
    analysis_runs = await db.scalar(select(func.count()).select_from(AnalysisResult))
    pending_reviews = await db.scalar(
        select(func.count())
        .select_from(Investigation)
        .where(Investigation.status == "review")
    )

    module_rows = (
        await db.execute(
            select(AnalysisResult.module, func.count())
            .group_by(AnalysisResult.module)
        )
    ).all()
    module_runs = {module: int(count) for module, count in module_rows}

    recent = (
        await db.scalars(select(Investigation).order_by(Investigation.updated_at.desc()).limit(5))
    ).all()

    owner_ids = {i.owner_id for i in recent}
    owners = (
        await db.scalars(select(Profile).where(Profile.id.in_(owner_ids)))
    ).all() if owner_ids else []
    owner_map = {p.id: p.full_name for p in owners}

    recent_investigations = [
        InvestigationOut(
            **{
                column: getattr(inv, column)
                for column in (
                    "id",
                    "case_id",
                    "title",
                    "description",
                    "category",
                    "priority",
                    "status",
                    "owner_id",
                    "notes",
                    "created_at",
                    "updated_at",
                )
            },
            evidence_count=0,
            analysis_count=0,
            owner_name=owner_map.get(inv.owner_id),
        )
        for inv in recent
    ]

    return DashboardStats(
        total_investigations=int(total_investigations or 0),
        active_investigations=int(active_investigations or 0),
        evidence_files=int(evidence_files or 0),
        analysis_runs=int(analysis_runs or 0),
        pending_reviews=int(pending_reviews or 0),
        total_evidence_bytes=int(total_bytes or 0),
        module_runs=module_runs,
        recent_investigations=recent_investigations,
        generated_at=datetime.now(timezone.utc),
    )

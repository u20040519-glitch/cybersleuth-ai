# =============================================================================
# CYBERSLEUTH AI - Correlation routes (Phase 5)
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.correlation.engine import correlate
from app.models import AnalysisResult, CorrelationResult, Evidence, Investigation, Profile
from app.schemas import CorrelationFindingOut, CorrelationResponse
from app.security.deps import client_ip, get_current_user
from app.services.audit import record_audit

router = APIRouter(prefix="/correlation", tags=["correlation"])


async def _load_investigation(db: AsyncSession, investigation_id: uuid.UUID) -> Investigation:
    investigation = await db.scalar(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


async def _gather(db: AsyncSession, investigation_id: uuid.UUID):
    investigation = await _load_investigation(db, investigation_id)

    evidence_rows = (
        await db.scalars(
            select(Evidence).where(Evidence.investigation_id == investigation_id)
        )
    ).all()

    uploader_ids = {e.uploaded_by for e in evidence_rows}
    uploaders = (
        await db.scalars(select(Profile).where(Profile.id.in_(uploader_ids)))
    ).all() if uploader_ids else []
    uploader_map = {p.id: p.full_name for p in uploaders}

    evidence = [
        {
            "id": str(e.id),
            "original_filename": e.original_filename,
            "sha256_hash": e.sha256_hash,
            "status": e.status,
            "uploaded_by_name": uploader_map.get(e.uploaded_by),
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
        }
        for e in evidence_rows
    ]

    analysis_rows = (
        await db.scalars(
            select(AnalysisResult)
            .join(Evidence, Evidence.id == AnalysisResult.evidence_id)
            .where(Evidence.investigation_id == investigation_id)
            .order_by(AnalysisResult.created_at.asc())
        )
    ).all()

    analyses = [
        {
            "id": str(a.id),
            "evidence_id": str(a.evidence_id),
            "module": a.module,
            "status": a.status,
            "result_data": a.result_data or {},
        }
        for a in analysis_rows
    ]

    owner = await db.scalar(select(Profile).where(Profile.id == investigation.owner_id))
    investigation_dict = {
        "id": str(investigation.id),
        "case_id": investigation.case_id,
        "title": investigation.title,
        "description": investigation.description,
        "category": investigation.category,
        "priority": investigation.priority,
        "status": investigation.status,
        "owner_name": owner.full_name if owner else None,
        "created_at": investigation.created_at.isoformat() if investigation.created_at else None,
    }

    return investigation, investigation_dict, evidence, analyses


@router.post("/{investigation_id}", response_model=CorrelationResponse)
async def run_correlation(
    request: Request,
    investigation_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the correlation engine over an investigation and persist the findings."""
    investigation, investigation_dict, evidence, analyses = await _gather(db, investigation_id)

    result = await correlate(
        investigation=investigation_dict,
        evidence=evidence,
        analyses=analyses,
        explain=True,
    )

    # Replace the previous run so repeated runs do not accumulate duplicates.
    existing = (
        await db.scalars(
            select(CorrelationResult).where(
                CorrelationResult.investigation_id == investigation_id
            )
        )
    ).all()
    for row in existing:
        await db.delete(row)
    await db.flush()

    persisted: List[CorrelationResult] = []
    for connection in result["connections"]:
        row = CorrelationResult(
            investigation_id=investigation_id,
            source_evidence_id=None,
            finding_id=connection["type"],
            correlation_type=connection["type"],
            description=connection["description"],
            confidence=connection["confidence"],
            timestamp=datetime.fromisoformat(connection["timestamp"])
            if connection.get("timestamp")
            else None,
            verified=False,
            result_data={
                "source": connection["source"],
                "target": connection["target"],
                "evidence_ids": connection["evidence_ids"],
            },
        )
        db.add(row)
        persisted.append(row)
    await db.flush()

    await record_audit(
        db,
        action="correlate",
        resource="investigation",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(investigation_id),
        ip_address=client_ip(request),
        details={"connections": len(result["connections"]), "events": result["total_events"]},
    )

    return CorrelationResponse(
        investigation_id=investigation_id,
        timeline=result["timeline"],
        connections=result["connections"],
        graph=result["graph"],
        findings=[CorrelationFindingOut.model_validate(row) for row in persisted],
        explanation=result.get("explanation"),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/{investigation_id}", response_model=CorrelationResponse)
async def get_correlation(
    investigation_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current correlation view for an investigation."""
    _, investigation_dict, evidence, analyses = await _gather(db, investigation_id)

    result = await correlate(
        investigation=investigation_dict,
        evidence=evidence,
        analyses=analyses,
        explain=False,
    )

    rows = (
        await db.scalars(
            select(CorrelationResult)
            .where(CorrelationResult.investigation_id == investigation_id)
            .order_by(CorrelationResult.created_at.asc())
        )
    ).all()

    return CorrelationResponse(
        investigation_id=investigation_id,
        timeline=result["timeline"],
        connections=result["connections"],
        graph=result["graph"],
        findings=[CorrelationFindingOut.model_validate(row) for row in rows],
        explanation=result.get("explanation"),
        generated_at=datetime.now(timezone.utc),
    )

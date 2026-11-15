# =============================================================================
# CYBERSLEUTH AI - Report routes (Phase 6)
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import sha256_bytes
from app.models import (
    AnalysisResult,
    ChainOfCustody,
    Evidence,
    GeneratedReport,
    Investigation,
    Profile,
)
from app.schemas import ReportCreate, ReportOut
from app.security.deps import client_ip, get_current_user
from app.services.audit import record_audit
from app.services.storage import BUCKET_REPORTS, StorageError, build_key, get_storage

router = APIRouter(prefix="/reports", tags=["reports"])


async def _load_investigation(db: AsyncSession, investigation_id: uuid.UUID) -> Investigation:
    investigation = await db.scalar(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


def _to_out(report: GeneratedReport) -> ReportOut:
    return ReportOut(
        id=report.id,
        investigation_id=report.investigation_id,
        title=report.title,
        status=report.status,
        storage_path=report.storage_path,
        file_size=report.file_size,
        sha256_hash=report.sha256_hash,
        generated_by=report.generated_by,
        generated_at=report.generated_at,
        metadata=report.metadata_json or {},
        download_url=(
            f"/api/reports/{report.id}/download" if report.status == "ready" else None
        ),
    )


@router.get("", response_model=List[ReportOut])
async def list_reports(
    investigation_id: Optional[uuid.UUID] = Query(default=None),
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(GeneratedReport).order_by(GeneratedReport.generated_at.desc())
    if investigation_id is not None:
        query = query.where(GeneratedReport.investigation_id == investigation_id)
    rows = (await db.scalars(query)).all()
    return [_to_out(row) for row in rows]


@router.post(
    "/{investigation_id}",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    request: Request,
    investigation_id: uuid.UUID,
    payload: ReportCreate,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Render the investigation report as a PDF and store it."""
    investigation = await _load_investigation(db, investigation_id)

    owner = await db.scalar(select(Profile).where(Profile.id == investigation.owner_id))

    evidence_rows = (
        await db.scalars(
            select(Evidence)
            .where(Evidence.investigation_id == investigation_id)
            .order_by(Evidence.uploaded_at.asc())
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
            "file_size": e.file_size,
            "mime_type": e.mime_type,
            "sha256_hash": e.sha256_hash,
            "status": e.status,
            "uploaded_by_name": uploader_map.get(e.uploaded_by),
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
            "metadata": e.metadata_json or {},
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
            "confidence_score": a.confidence_score,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "result_data": a.result_data or {},
        }
        for a in analysis_rows
    ]

    from app.models import CorrelationResult

    correlation_rows = (
        await db.scalars(
            select(CorrelationResult)
            .where(CorrelationResult.investigation_id == investigation_id)
            .order_by(CorrelationResult.created_at.asc())
        )
    ).all()

    correlations = [
        {
            "id": str(c.id),
            "correlation_type": c.correlation_type,
            "description": c.description,
            "confidence": c.confidence,
            "verified": c.verified,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
        }
        for c in correlation_rows
    ]

    custody_rows = (
        await db.scalars(
            select(ChainOfCustody)
            .join(Evidence, Evidence.id == ChainOfCustody.evidence_id)
            .where(Evidence.investigation_id == investigation_id)
            .order_by(ChainOfCustody.timestamp.asc())
        )
    ).all()

    evidence_name = {
        str(e.id): e.original_filename for e in evidence_rows
    }
    custody = [
        {
            "evidence_id": str(c.evidence_id),
            "evidence_name": evidence_name.get(str(c.evidence_id), ""),
            "event_type": c.event_type,
            "actor_name": c.actor_name,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "details": c.details,
            "event_hash": c.event_hash,
            "previous_hash": c.previous_hash,
        }
        for c in custody_rows
    ]

    title = payload.title or f"{investigation.case_id} — Forensic Report"

    report = GeneratedReport(
        investigation_id=investigation_id,
        title=title,
        status="generating",
        generated_by=profile.id,
        generated_at=datetime.now(timezone.utc),
        metadata_json={
            "evidence_count": len(evidence),
            "analysis_count": len(analyses),
            "correlation_count": len(correlations),
        },
    )
    db.add(report)
    await db.flush()

    try:
        from app.reports.pdf import render_report

        pdf_bytes = render_report(
            investigation={
                "id": str(investigation.id),
                "case_id": investigation.case_id,
                "title": investigation.title,
                "description": investigation.description,
                "category": investigation.category,
                "priority": investigation.priority,
                "status": investigation.status,
                "owner_name": owner.full_name if owner else None,
                "created_at": investigation.created_at.isoformat()
                if investigation.created_at
                else None,
                "updated_at": investigation.updated_at.isoformat()
                if investigation.updated_at
                else None,
                "notes": investigation.notes,
            },
            evidence=evidence,
            analyses=analyses,
            correlations=correlations,
            custody=custody,
            options={
                "include_evidence": payload.include_evidence,
                "include_custody": payload.include_custody,
                "include_analysis": payload.include_analysis,
                "include_correlation": payload.include_correlation,
            },
        )
    except Exception as exc:
        report.status = "failed"
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Report rendering failed: {exc}")

    key = build_key(BUCKET_REPORTS, investigation_id, f"{report.id}.pdf")
    storage = get_storage()
    try:
        storage.put(BUCKET_REPORTS, key, pdf_bytes)
    except StorageError as exc:
        report.status = "failed"
        await db.flush()
        raise HTTPException(status_code=500, detail=str(exc))

    report.status = "ready"
    report.storage_path = key
    report.file_size = len(pdf_bytes)
    report.sha256_hash = sha256_bytes(pdf_bytes)
    await db.flush()

    await record_audit(
        db,
        action="generate_report",
        resource="report",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(report.id),
        ip_address=client_ip(request),
        details={"investigation_id": str(investigation_id), "bytes": len(pdf_bytes)},
    )

    return _to_out(report)


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await db.scalar(select(GeneratedReport).where(GeneratedReport.id == report_id))
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_out(report)


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    request: Request,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a rendered report."""
    report = await db.scalar(select(GeneratedReport).where(GeneratedReport.id == report_id))
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "ready" or not report.storage_path:
        raise HTTPException(status_code=409, detail="The report is not ready for download")

    storage = get_storage()
    try:
        payload = storage.get(BUCKET_REPORTS, report.storage_path)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await record_audit(
        db,
        action="download_report",
        resource="report",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(report.id),
        ip_address=client_ip(request),
    )

    return Response(
        content=payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="report-{report.id}.pdf"',
            "X-Report-SHA256": report.sha256_hash or "",
        },
    )

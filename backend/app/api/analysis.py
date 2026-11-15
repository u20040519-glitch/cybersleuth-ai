# =============================================================================
# CYBERSLEUTH AI - Forensic analysis routes (Phase 4)
# =============================================================================
# One endpoint per module, all sharing the same contract:
#
#   POST /api/deeptrace/analyze   {"evidence_id": "...", "options": {...}}
#   POST /api/spytrace/analyze    {"evidence_id": "...", "options": {...}}
#   POST /api/voiceproof/analyze  {"evidence_id": "...", "options": {...}}
#   POST /api/cybersleuth/analyze {"evidence_id": "...", "options": {...}}
# =============================================================================

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import sha256_file
from app.models import AnalysisResult, Evidence, EvidenceEvent, Investigation, Profile
from app.schemas import AnalysisJobOut, AnalysisRequest, AnalysisResultOut
from app.security.deps import client_ip, get_current_user
from app.services.audit import record_audit
from app.services.custody import append_custody_event
from app.services.storage import BUCKET_ORIGINALS, StorageError, get_storage

logger = logging.getLogger(__name__)

MODULES = ("deeptrace", "spytrace", "voiceproof", "cybersleuth")


def _load_analyzer(module: str) -> Tuple[Any, bool]:
    """Import the analyzer for a module. Returns (callable, available)."""
    try:
        if module == "deeptrace":
            from app.forensic.deeptrace import analyzer as module_impl
        elif module == "spytrace":
            from app.forensic.spytrace import analyzer as module_impl
        elif module == "voiceproof":
            from app.forensic.voiceproof import analyzer as module_impl
        elif module == "cybersleuth":
            from app.forensic.cybersleuth import analyzer as module_impl
        else:
            raise ValueError(module)
    except Exception:
        logger.exception("Could not import the %s analyzer", module)
        return None, False

    return module_impl.analyze, bool(getattr(module_impl, "AVAILABLE", True))


async def _materialise_evidence(db: AsyncSession, evidence: Evidence) -> Path:
    """Copy the stored original to a temporary file so the module can read it."""
    storage = get_storage()
    stored = storage.path_for(BUCKET_ORIGINALS, evidence.storage_path)
    if stored is not None:
        return stored

    import tempfile

    suffix = Path(evidence.original_filename).suffix
    tmp_dir = Path(tempfile.mkdtemp(prefix="cybersleuth-analysis-"))
    target = tmp_dir / f"evidence{suffix}"
    try:
        payload = storage.get(BUCKET_ORIGINALS, evidence.storage_path)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    target.write_bytes(payload)
    return target


def _build_router(module: str) -> APIRouter:
    router = APIRouter(prefix=f"/{module}", tags=[module])

    @router.post("/analyze", response_model=AnalysisResultOut)
    async def analyze(
        request: Request,
        payload: AnalysisRequest,
        profile=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Run one forensic module against one evidence item."""
        evidence = await db.scalar(select(Evidence).where(Evidence.id == payload.evidence_id))
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence not found")

        investigation = await db.scalar(
            select(Investigation).where(Investigation.id == evidence.investigation_id)
        )
        if investigation is None:
            raise HTTPException(status_code=404, detail="Investigation not found")

        analyzer, available = _load_analyzer(module)

        options: Dict[str, Any] = dict(payload.options or {})
        options.setdefault("evidence_id", str(evidence.id))
        options.setdefault("investigation_id", str(investigation.id))

        # Derived artefacts are written next to the evidence, never over it.
        import tempfile

        output_dir = Path(tempfile.mkdtemp(prefix=f"cybersleuth-{module}-"))
        options["output_dir"] = str(output_dir)

        if analyzer is None or not available:
            result = {
                "module": module,
                "status": "unavailable",
                "reason": (
                    f"The {module} module is not available on this deployment. "
                    "Install its dependencies and restart the API."
                ),
                "summary": f"{module} analysis is unavailable on this deployment.",
                "confidence_score": None,
                "filename": evidence.original_filename,
                "sha256": evidence.sha256_hash,
                "mime": evidence.mime_type,
                "dimensions": None,
                "findings": [],
                "timeline": [],
                "metadata": {},
                "derived_files": [],
            }
        else:
            source = await _materialise_evidence(db, evidence)
            try:
                result = await asyncio.to_thread(analyzer, str(source), options)
            except Exception as exc:
                logger.exception("%s analysis failed", module)
                result = {
                    "module": module,
                    "status": "failed",
                    "reason": str(exc),
                    "summary": f"{module} analysis failed: {exc}",
                    "confidence_score": None,
                    "filename": evidence.original_filename,
                    "sha256": evidence.sha256_hash,
                    "mime": evidence.mime_type,
                    "dimensions": None,
                    "findings": [],
                    "timeline": [],
                    "metadata": {},
                    "derived_files": [],
                }

        result.setdefault("module", module)
        result.setdefault("filename", evidence.original_filename)
        result.setdefault("sha256", evidence.sha256_hash)
        result.setdefault("mime", evidence.mime_type)

        record = AnalysisResult(
            evidence_id=evidence.id,
            module=module,
            status="completed" if result.get("status") == "completed" else result.get("status", "failed"),
            result_data=result,
            confidence_score=result.get("confidence_score"),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.flush()

        if record.status == "completed":
            evidence.status = "analyzed"
            evidence.processed_at = datetime.now(timezone.utc)
            await db.flush()

        await append_custody_event(
            db,
            evidence_id=evidence.id,
            event_type="process",
            actor_id=profile.id,
            actor_name=profile.full_name,
            details=(
                f"{module} analysis finished with status '{record.status}' "
                f"({len(result.get('findings') or [])} findings)."
            ),
        )
        db.add(
            EvidenceEvent(
                evidence_id=evidence.id,
                event_type="process",
                actor_id=profile.id,
                actor_name=profile.full_name,
                details=f"{module} analysis: {record.status}",
            )
        )

        await record_audit(
            db,
            action="analyze",
            resource="analysis",
            user_id=profile.id,
            user_name=profile.full_name,
            resource_id=str(record.id),
            ip_address=client_ip(request),
            details={"module": module, "status": record.status, "evidence_id": str(evidence.id)},
        )

        return AnalysisResultOut.model_validate(record)

    return router


# One router per module, so the frontend can call /deeptrace/analyze etc.
routers = {module: _build_router(module) for module in MODULES}


# -----------------------------------------------------------------------------
# Shared analysis listing
# -----------------------------------------------------------------------------
listing_router = APIRouter(prefix="/analysis", tags=["analysis"])


@listing_router.get("/results", response_model=List[AnalysisResultOut])
async def list_results(
    investigation_id: Optional[uuid.UUID] = Query(default=None),
    evidence_id: Optional[uuid.UUID] = Query(default=None),
    module: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List analysis results the caller can access."""
    query = select(AnalysisResult).join(
        Evidence, Evidence.id == AnalysisResult.evidence_id
    ).order_by(AnalysisResult.created_at.desc())

    if investigation_id is not None:
        query = query.where(Evidence.investigation_id == investigation_id)
    if evidence_id is not None:
        query = query.where(AnalysisResult.evidence_id == evidence_id)
    if module:
        query = query.where(AnalysisResult.module == module)

    query = query.limit(limit)
    rows = (await db.scalars(query)).all()
    return [AnalysisResultOut.model_validate(row) for row in rows]


@listing_router.get("/results/{result_id}", response_model=AnalysisResultOut)
async def get_result(
    result_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.scalar(select(AnalysisResult).where(AnalysisResult.id == result_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return AnalysisResultOut.model_validate(row)

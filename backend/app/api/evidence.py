# =============================================================================
# CYBERSLEUTH AI - Evidence routes (Phase 3)
# =============================================================================
# Upload, integrity verification, chain of custody and controlled download.
# =============================================================================

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import sha256_file
from app.models import ChainOfCustody, Evidence, EvidenceEvent, Investigation, Profile
from app.schemas import (
    CustodyEntryOut,
    CustodyVerification,
    EvidenceEventOut,
    EvidenceOut,
    IntegrityCheckResult,
)
from app.security.deps import client_ip, get_current_user
from app.services.audit import record_audit
from app.services.custody import append_custody_event, verify_custody_chain
from app.services.evidence import validate_upload
from app.services.storage import (
    BUCKET_ORIGINALS,
    StorageError,
    build_key,
    get_storage,
    guess_mime_type,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evidence", tags=["evidence"])


async def _load_evidence(db: AsyncSession, evidence_id: uuid.UUID) -> Evidence:
    evidence = await db.scalar(select(Evidence).where(Evidence.id == evidence_id))
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return evidence


def _to_out(evidence: Evidence, uploader_name: Optional[str] = None) -> EvidenceOut:
    return EvidenceOut(
        id=evidence.id,
        investigation_id=evidence.investigation_id,
        original_filename=evidence.original_filename,
        file_size=evidence.file_size,
        mime_type=evidence.mime_type,
        sha256_hash=evidence.sha256_hash,
        storage_path=evidence.storage_path,
        status=evidence.status,
        uploaded_by=evidence.uploaded_by,
        uploaded_at=evidence.uploaded_at,
        processed_at=evidence.processed_at,
        thumbnail_path=evidence.thumbnail_path,
        metadata=evidence.metadata_json or {},
        uploaded_by_name=uploader_name,
    )


@router.get("", response_model=List[EvidenceOut])
async def list_evidence(
    investigation_id: Optional[uuid.UUID] = Query(default=None),
    evidence_type: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=120),
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List evidence the caller can access."""
    query = select(Evidence).order_by(Evidence.uploaded_at.desc())

    if investigation_id is not None:
        query = query.where(Evidence.investigation_id == investigation_id)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(func_lower(Evidence.original_filename).like(pattern))

    rows = (await db.scalars(query)).all()
    if not rows:
        return []

    uploader_ids = {e.uploaded_by for e in rows}
    uploaders = {
        p.id: p.full_name
        for p in (await db.scalars(select(Profile).where(Profile.id.in_(uploader_ids)))).all()
    }

    results = []
    for evidence in rows:
        if evidence_type and evidence_type != "all":
            detected = (evidence.metadata_json or {}).get("type", "")
            if detected != evidence_type:
                continue
        results.append(_to_out(evidence, uploaders.get(evidence.uploaded_by)))
    return results


def func_lower(column):
    from sqlalchemy import func

    return func.lower(column)


@router.post("/upload", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    request: Request,
    investigation_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept an original evidence file.

    The file is written to a temporary location, validated, hashed, and only
    then copied into the immutable originals bucket. The stored SHA-256 is
    computed from the bytes that were actually written.
    """
    investigation = await db.scalar(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")

    original_filename = file.filename or "unnamed"
    suffix = Path(original_filename).suffix

    tmp_dir = Path(tempfile.mkdtemp(prefix="cybersleuth-upload-"))
    tmp_path = tmp_dir / f"upload{suffix}"

    try:
        total = 0
        with open(tmp_path, "wb") as handle:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"The upload exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit."
                        ),
                    )
                handle.write(chunk)

        validation = validate_upload(
            path=tmp_path,
            original_filename=original_filename,
            declared_mime=file.content_type or "application/octet-stream",
            size=total,
        )

        if not validation.valid:
            await record_audit(
                db,
                action="upload_rejected",
                resource="evidence",
                user_id=profile.id,
                user_name=profile.full_name,
                resource_id=str(investigation_id),
                ip_address=client_ip(request),
                details={"filename": original_filename, "reason": validation.error},
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=validation.error)

        # Write the original to the immutable bucket first, under a random key.
        # The database row is then created with storage_path already set, so the
        # immutable-original trigger never sees an UPDATE.
        key = build_key(BUCKET_ORIGINALS, investigation_id, f"{uuid.uuid4().hex}-{validation.filename}")
        storage = get_storage()
        try:
            storage.put_file(BUCKET_ORIGINALS, key, tmp_path)
        except StorageError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        # Re-hash the stored object to prove the bytes on disk match the hash.
        stored_path = storage.path_for(BUCKET_ORIGINALS, key)
        if stored_path is not None:
            stored_hash = sha256_file(stored_path)
            if stored_hash != validation.sha256:
                try:
                    stored_path.unlink(missing_ok=True)
                except OSError:
                    logger.error("failed intake object left behind at %s", stored_path)
                raise HTTPException(
                    status_code=500,
                    detail="The stored object does not match the computed hash.",
                )

        evidence = Evidence(
            investigation_id=investigation_id,
            original_filename=validation.filename,
            file_size=validation.size,
            mime_type=validation.detected_mime,
            sha256_hash=validation.sha256,
            storage_path=key,
            status="uploaded",
            uploaded_by=profile.id,
            metadata_json={
                **validation.metadata,
                "declared_mime": validation.declared_mime,
                "detected_mime": validation.detected_mime,
                "type": _evidence_type(validation.detected_mime),
                "warnings": validation.warnings,
            },
        )
        db.add(evidence)
        await db.flush()

        await append_custody_event(
            db,
            evidence_id=evidence.id,
            event_type="upload",
            actor_id=profile.id,
            actor_name=profile.full_name,
            details=(
                f"Original uploaded and verified. SHA-256 {evidence.sha256_hash}. "
                f"{evidence.file_size} bytes."
            ),
        )
        db.add(
            EvidenceEvent(
                evidence_id=evidence.id,
                event_type="upload",
                actor_id=profile.id,
                actor_name=profile.full_name,
                details=validation.filename,
            )
        )

        await record_audit(
            db,
            action="upload",
            resource="evidence",
            user_id=profile.id,
            user_name=profile.full_name,
            resource_id=str(evidence.id),
            ip_address=client_ip(request),
            details={
                "filename": validation.filename,
                "sha256": evidence.sha256_hash,
                "size": evidence.file_size,
            },
        )

        return _to_out(evidence, profile.full_name)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _evidence_type(mime: str) -> str:
    """Map a MIME type onto the evidence categories the UI filters on."""
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("audio/"):
        return "audio"
    if mime.startswith("video/"):
        return "video"
    if mime in ("application/pdf",):
        return "document"
    if mime.startswith("text/"):
        return "text"
    if mime in ("application/zip", "application/x-zip-compressed"):
        return "archive"
    if mime == "application/vnd.android.package-archive":
        return "apk"
    if mime in ("application/json", "application/xml"):
        return "structured"
    return "binary"


@router.get("/{evidence_id}", response_model=EvidenceOut)
async def get_evidence(
    evidence_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evidence = await _load_evidence(db, evidence_id)
    uploader = await db.scalar(select(Profile).where(Profile.id == evidence.uploaded_by))
    return _to_out(evidence, uploader.full_name if uploader else None)


@router.get("/{evidence_id}/download")
async def download_evidence(
    request: Request,
    evidence_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the original file. Every download is recorded in the custody ledger."""
    evidence = await _load_evidence(db, evidence_id)
    storage = get_storage()

    try:
        payload = storage.get(BUCKET_ORIGINALS, evidence.storage_path)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await append_custody_event(
        db,
        evidence_id=evidence.id,
        event_type="access",
        actor_id=profile.id,
        actor_name=profile.full_name,
        details=f"Original downloaded ({len(payload)} bytes).",
    )
    db.add(
        EvidenceEvent(
            evidence_id=evidence.id,
            event_type="access",
            actor_id=profile.id,
            actor_name=profile.full_name,
            details="Original downloaded",
        )
    )
    await record_audit(
        db,
        action="download",
        resource="evidence",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(evidence.id),
        ip_address=client_ip(request),
    )

    return StreamingResponse(
        iter([payload]),
        media_type=evidence.mime_type or guess_mime_type(evidence.original_filename),
        headers={
            "Content-Disposition": f'attachment; filename="{evidence.original_filename}"',
            "X-Evidence-SHA256": evidence.sha256_hash,
        },
    )


@router.post("/{evidence_id}/integrity-check", response_model=IntegrityCheckResult)
async def integrity_check(
    request: Request,
    evidence_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-hash the stored original and compare it with the recorded hash."""
    evidence = await _load_evidence(db, evidence_id)
    storage = get_storage()

    stored_path = storage.path_for(BUCKET_ORIGINALS, evidence.storage_path)
    if stored_path is None:
        try:
            payload = storage.get(BUCKET_ORIGINALS, evidence.storage_path)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        import hashlib

        actual = hashlib.sha256(payload).hexdigest()
    else:
        actual = sha256_file(stored_path)

    intact = actual == evidence.sha256_hash

    await append_custody_event(
        db,
        evidence_id=evidence.id,
        event_type="process",
        actor_id=profile.id,
        actor_name=profile.full_name,
        details=(
            f"Integrity check performed: {'intact' if intact else 'MISMATCH'}."
        ),
    )
    await record_audit(
        db,
        action="integrity_check",
        resource="evidence",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(evidence.id),
        ip_address=client_ip(request),
        details={"intact": intact, "actual_sha256": actual},
    )

    return IntegrityCheckResult(
        evidence_id=evidence.id,
        expected_sha256=evidence.sha256_hash,
        actual_sha256=actual,
        intact=intact,
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/{evidence_id}/custody", response_model=List[CustodyEntryOut])
async def custody_chain(
    evidence_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the tamper-evident custody ledger for an evidence item."""
    await _load_evidence(db, evidence_id)
    rows = (
        await db.scalars(
            select(ChainOfCustody)
            .where(ChainOfCustody.evidence_id == evidence_id)
            .order_by(ChainOfCustody.timestamp.asc())
        )
    ).all()
    return [CustodyEntryOut.model_validate(row) for row in rows]


@router.get("/{evidence_id}/custody/verify", response_model=CustodyVerification)
async def verify_custody(
    evidence_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recompute the custody hash chain and report whether it is intact."""
    await _load_evidence(db, evidence_id)
    return CustodyVerification(**await verify_custody_chain(db, evidence_id))


@router.get("/{evidence_id}/events", response_model=List[EvidenceEventOut])
async def list_events(
    evidence_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the chronological event log for an evidence item."""
    await _load_evidence(db, evidence_id)
    rows = (
        await db.scalars(
            select(EvidenceEvent)
            .where(EvidenceEvent.evidence_id == evidence_id)
            .order_by(EvidenceEvent.timestamp.asc())
        )
    ).all()
    return [EvidenceEventOut.model_validate(row) for row in rows]

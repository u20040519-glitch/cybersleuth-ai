# =============================================================================
# PROJECT NEXUS AI - Evidence Management API
# =============================================================================
# Evidence upload, tracking, and chain of custody.
# =============================================================================

import logging
import hashlib
import os
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.db.database import get_db
from app.models import User, Case, EvidenceFile, ChainOfCustodyRecord, AuditLog
from app.schemas.user import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


def _allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed = [e.strip().lower() for e in settings.allowed_extensions.split(",")]
    return ext in allowed


def _compute_file_hash(file_content: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


# ---------------------------------------------------------------------------
# Upload evidence
# ---------------------------------------------------------------------------

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload evidence file to a case. Enforces upload quotas and file validation."""
    # Parse case UUID
    try:
        case_uuid = UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case ID")

    # Verify case exists and user has access
    result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if case.owner_id != current_user.id:
        perm_result = await db.execute(
            select(CasePermission).where(
                CasePermission.case_id == case_uuid,
                CasePermission.user_id == current_user.id,
                CasePermission.permission.in_(["read", "write", "admin"]),
            )
        )
        if not perm_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to upload evidence to this case")

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    if not _allowed_file(file.filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")

    # Read file content
    content = await file.read()
    file_size = len(content)

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {settings.max_upload_size_mb} MB limit",
        )

    # Compute hash
    file_hash = _compute_file_hash(content)

    # Check for duplicate (same hash in same case)
    existing = await db.execute(
        select(EvidenceFile).where(
            EvidenceFile.case_id == case_uuid,
            EvidenceFile.file_hash_sha256 == file_hash,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate evidence file already exists")

    # Store file
    upload_dir = Path(settings.upload_directory) / str(case_uuid)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{UUID(int=0).hex[:8]}_{file.filename}"
    # Use a unique name
    import uuid as _uuid
    stored_filename = f"{_uuid.uuid4().hex}_{file.filename}"
    file_path = upload_dir / stored_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Create evidence record
    evidence = EvidenceFile(
        case_id=case_uuid,
        uploader_id=current_user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        mime_type=file.content_type or "application/octet-stream",
        file_hash_sha256=file_hash,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)

    # Chain of custody record
    custody = ChainOfCustodyRecord(
        case_id=case_uuid,
        evidence_file_id=evidence.id,
        action="uploaded",
        performed_by=current_user.id,
        notes=f"Original upload: {file.filename}",
    )
    db.add(custody)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="evidence_uploaded",
        resource_type="evidence",
        resource_id=str(evidence.id),
    )
    db.add(audit)
    await db.commit()

    logger.info("Evidence uploaded: %s to case %s by %s", file.filename, case_id, current_user.email)

    return {
        "id": str(evidence.id),
        "original_filename": evidence.original_filename,
        "file_size_bytes": evidence.file_size_bytes,
        "mime_type": evidence.mime_type,
        "file_hash_sha256": evidence.file_hash_sha256,
        "status": evidence.status,
        "uploaded_at": evidence.uploaded_at,
    }


# ---------------------------------------------------------------------------
# List evidence for a case
# ---------------------------------------------------------------------------

@router.get("/case/{case_id}")
async def list_evidence(
    case_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List evidence files for a case."""
    try:
        case_uuid = UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case ID")

    result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if case.owner_id != current_user.id:
        perm_result = await db.execute(
            select(CasePermission).where(
                CasePermission.case_id == case_uuid,
                CasePermission.user_id == current_user.id,
            )
        )
        if not perm_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    result = await db.execute(
        select(EvidenceFile).where(EvidenceFile.case_id == case_uuid)
    )
    evidence_files = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "original_filename": e.original_filename,
            "file_size_bytes": e.file_size_bytes,
            "mime_type": e.mime_type,
            "file_hash_sha256": e.file_hash_sha256,
            "status": e.status,
            "uploaded_at": e.uploaded_at,
            "processed_at": e.processed_at,
        }
        for e in evidence_files
    ]
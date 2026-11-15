# =============================================================================
# CYBERSLEUTH AI - Investigation routes
# =============================================================================
# Access control is enforced twice: the database refuses to return rows the
# caller may not see (RLS), and the routes return 404 for investigations the
# caller is not a member of, so the existence of another team's case is never
# disclosed.
# =============================================================================

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import (
    AnalysisResult,
    Evidence,
    Investigation,
    InvestigationMember,
    Profile,
)
from app.schemas import (
    InvestigationCreate,
    InvestigationDetail,
    InvestigationOut,
    InvestigationUpdate,
    MemberCreate,
    MemberOut,
)
from app.security.deps import client_ip, get_current_user
from app.services.audit import record_audit

router = APIRouter(prefix="/investigations", tags=["investigations"])


async def _load_investigation(db: AsyncSession, investigation_id: uuid.UUID) -> Investigation:
    """Fetch an investigation, or raise 404 when the caller may not see it."""
    investigation = await db.scalar(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    if investigation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    return investigation


async def _counts(db: AsyncSession, investigation_id: uuid.UUID) -> tuple[int, int]:
    evidence_count = await db.scalar(
        select(func.count()).select_from(Evidence).where(Evidence.investigation_id == investigation_id)
    )
    analysis_count = await db.scalar(
        select(func.count())
        .select_from(AnalysisResult)
        .join(Evidence, Evidence.id == AnalysisResult.evidence_id)
        .where(Evidence.investigation_id == investigation_id)
    )
    return int(evidence_count or 0), int(analysis_count or 0)


async def _to_out(
    db: AsyncSession,
    investigation: Investigation,
    owner_name: Optional[str] = None,
) -> InvestigationOut:
    evidence_count, analysis_count = await _counts(db, investigation.id)

    member_rows = await db.scalars(
        select(InvestigationMember).where(InvestigationMember.investigation_id == investigation.id)
    )
    members = list(member_rows)

    assigned = []
    if members:
        member_ids = [m.user_id for m in members]
        profiles = await db.scalars(select(Profile).where(Profile.id.in_(member_ids)))
        assigned = [p.email for p in profiles]

    return InvestigationOut(
        **{
            column: getattr(investigation, column)
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
        evidence_count=evidence_count,
        analysis_count=analysis_count,
        owner_name=owner_name,
        assigned_users=assigned,
    )


@router.get("", response_model=List[InvestigationOut])
async def list_investigations(
    search: Optional[str] = Query(default=None, max_length=120),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the investigations the caller can access."""
    query = select(Investigation).order_by(Investigation.updated_at.desc())

    if status_filter and status_filter != "all":
        query = query.where(Investigation.status == status_filter)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            func.lower(Investigation.title).like(pattern)
            | func.lower(Investigation.case_id).like(pattern)
            | func.lower(func.coalesce(Investigation.description, "")).like(pattern)
        )

    investigations = (await db.scalars(query)).all()
    if not investigations:
        return []

    owner_ids = {i.owner_id for i in investigations}
    owners = {
        p.id: p.full_name
        for p in (await db.scalars(select(Profile).where(Profile.id.in_(owner_ids)))).all()
    }

    return [
        await _to_out(db, investigation, owners.get(investigation.owner_id))
        for investigation in investigations
    ]


@router.post("", response_model=InvestigationOut, status_code=status.HTTP_201_CREATED)
async def create_investigation(
    payload: InvestigationCreate,
    request: Request,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an investigation owned by the caller."""
    investigation = Investigation(
        case_id=payload.case_id.strip(),
        title=payload.title.strip(),
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        status=payload.status,
        notes=payload.notes,
        owner_id=profile.id,
    )
    db.add(investigation)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An investigation with that case_id already exists",
        ) from exc

    # The database trigger adds the owner as a lead member. Additional members
    # are inserted explicitly.
    for member_id in payload.member_ids:
        if member_id == profile.id:
            continue
        exists = await db.scalar(
            select(Profile).where(Profile.id == member_id)
        )
        if exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {member_id} does not exist",
            )
        db.add(
            InvestigationMember(
                investigation_id=investigation.id,
                user_id=member_id,
                member_role="member",
            )
        )
    await db.flush()

    await record_audit(
        db,
        action="create",
        resource="investigation",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(investigation.id),
        ip_address=client_ip(request),
        details={"case_id": investigation.case_id},
    )

    return await _to_out(db, investigation, profile.full_name)


@router.get("/{investigation_id}", response_model=InvestigationDetail)
async def get_investigation(
    investigation_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return one investigation with its members, evidence and analyses."""
    investigation = await _load_investigation(db, investigation_id)

    owner = await db.scalar(select(Profile).where(Profile.id == investigation.owner_id))
    base = await _to_out(db, investigation, owner.full_name if owner else None)

    member_rows = (
        await db.scalars(
            select(InvestigationMember).where(
                InvestigationMember.investigation_id == investigation_id
            )
        )
    ).all()
    member_ids = [m.user_id for m in member_rows]
    profiles = (
        await db.scalars(select(Profile).where(Profile.id.in_(member_ids)))
    ).all() if member_ids else []
    profile_map = {p.id: p for p in profiles}

    members = [
        MemberOut(
            id=m.id,
            investigation_id=m.investigation_id,
            user_id=m.user_id,
            member_role=m.member_role,
            created_at=m.created_at,
            user_email=profile_map[m.user_id].email if m.user_id in profile_map else None,
            user_name=profile_map[m.user_id].full_name if m.user_id in profile_map else None,
        )
        for m in member_rows
    ]

    evidence_rows = (
        await db.scalars(
            select(Evidence)
            .where(Evidence.investigation_id == investigation_id)
            .order_by(Evidence.uploaded_at.desc())
        )
    ).all()

    uploader_ids = {e.uploaded_by for e in evidence_rows}
    uploaders = (
        await db.scalars(select(Profile).where(Profile.id.in_(uploader_ids)))
    ).all() if uploader_ids else []
    uploader_map = {p.id: p.full_name for p in uploaders}

    evidence = [
        {
            "id": e.id,
            "investigation_id": e.investigation_id,
            "original_filename": e.original_filename,
            "file_size": e.file_size,
            "mime_type": e.mime_type,
            "sha256_hash": e.sha256_hash,
            "storage_path": e.storage_path,
            "status": e.status,
            "uploaded_by": e.uploaded_by,
            "uploaded_at": e.uploaded_at,
            "processed_at": e.processed_at,
            "thumbnail_path": e.thumbnail_path,
            "metadata": e.metadata_json or {},
            "uploaded_by_name": uploader_map.get(e.uploaded_by),
        }
        for e in evidence_rows
    ]

    analysis_rows = (
        await db.scalars(
            select(AnalysisResult)
            .join(Evidence, Evidence.id == AnalysisResult.evidence_id)
            .where(Evidence.investigation_id == investigation_id)
            .order_by(AnalysisResult.created_at.desc())
        )
    ).all()

    analysis = [
        {
            "id": a.id,
            "evidence_id": a.evidence_id,
            "module": a.module,
            "status": a.status,
            "result_data": a.result_data,
            "confidence_score": a.confidence_score,
            "created_at": a.created_at,
            "completed_at": a.completed_at,
        }
        for a in analysis_rows
    ]

    return InvestigationDetail(
        **base.model_dump(),
        members=members,
        evidence=evidence,
        analysis=analysis,
    )


@router.patch("/{investigation_id}", response_model=InvestigationOut)
async def update_investigation(
    investigation_id: uuid.UUID,
    payload: InvestigationUpdate,
    request: Request,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an investigation."""
    investigation = await _load_investigation(db, investigation_id)

    changes = payload.model_dump(exclude_none=True)
    if not changes:
        return await _to_out(db, investigation)

    for field, value in changes.items():
        setattr(investigation, field, value)
    await db.flush()
    # The touch_updated_at trigger rewrites updated_at server-side; refresh so
    # the attributes are materialised before serialising (async-safe).
    await db.refresh(investigation)

    await record_audit(
        db,
        action="update",
        resource="investigation",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(investigation.id),
        ip_address=client_ip(request),
        details={"fields": sorted(changes.keys())},
    )

    owner = await db.scalar(select(Profile).where(Profile.id == investigation.owner_id))
    return await _to_out(db, investigation, owner.full_name if owner else None)


@router.delete("/{investigation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investigation(
    investigation_id: uuid.UUID,
    request: Request,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an investigation and everything attached to it."""
    investigation = await _load_investigation(db, investigation_id)

    await record_audit(
        db,
        action="delete",
        resource="investigation",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(investigation.id),
        ip_address=client_ip(request),
        details={"case_id": investigation.case_id},
    )

    await db.delete(investigation)
    return None


# -----------------------------------------------------------------------------
# Members
# -----------------------------------------------------------------------------
@router.get("/{investigation_id}/members", response_model=List[MemberOut])
async def list_members(
    investigation_id: uuid.UUID,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _load_investigation(db, investigation_id)

    rows = (
        await db.scalars(
            select(InvestigationMember).where(
                InvestigationMember.investigation_id == investigation_id
            )
        )
    ).all()
    if not rows:
        return []

    profiles = (
        await db.scalars(select(Profile).where(Profile.id.in_([r.user_id for r in rows])))
    ).all()
    profile_map = {p.id: p for p in profiles}

    return [
        MemberOut(
            id=r.id,
            investigation_id=r.investigation_id,
            user_id=r.user_id,
            member_role=r.member_role,
            created_at=r.created_at,
            user_email=profile_map[r.user_id].email if r.user_id in profile_map else None,
            user_name=profile_map[r.user_id].full_name if r.user_id in profile_map else None,
        )
        for r in rows
    ]


@router.post(
    "/{investigation_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    investigation_id: uuid.UUID,
    payload: MemberCreate,
    request: Request,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Grant another user access to the investigation."""
    await _load_investigation(db, investigation_id)

    target = await db.scalar(select(Profile).where(Profile.id == payload.user_id))
    if target is None:
        raise HTTPException(status_code=404, detail="User does not exist")

    existing = await db.scalar(
        select(InvestigationMember).where(
            InvestigationMember.investigation_id == investigation_id,
            InvestigationMember.user_id == payload.user_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="User is already a member")

    member = InvestigationMember(
        investigation_id=investigation_id,
        user_id=payload.user_id,
        member_role=payload.member_role,
    )
    db.add(member)
    await db.flush()

    await record_audit(
        db,
        action="add_member",
        resource="investigation",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(investigation_id),
        ip_address=client_ip(request),
        details={"added_user_id": str(payload.user_id)},
    )

    return MemberOut(
        id=member.id,
        investigation_id=member.investigation_id,
        user_id=member.user_id,
        member_role=member.member_role,
        created_at=member.created_at,
        user_email=target.email,
        user_name=target.full_name,
    )


@router.delete(
    "/{investigation_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    investigation_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a user's access to the investigation."""
    await _load_investigation(db, investigation_id)

    member = await db.scalar(
        select(InvestigationMember).where(
            InvestigationMember.investigation_id == investigation_id,
            InvestigationMember.user_id == user_id,
        )
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    await record_audit(
        db,
        action="remove_member",
        resource="investigation",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(investigation_id),
        ip_address=client_ip(request),
        details={"removed_user_id": str(user_id)},
    )

    await db.delete(member)
    return None

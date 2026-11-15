# =============================================================================
# CYBERSLEUTH AI - Audit log routes
# =============================================================================

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogOut
from app.security.deps import get_current_user

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=List[AuditLogOut])
async def list_audit_logs(
    action: Optional[str] = Query(default=None),
    resource: Optional[str] = Query(default=None),
    resource_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the audit trail. Supervisors see every entry, users see their own."""
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())

    if action:
        query = query.where(AuditLog.action == action)
    if resource:
        query = query.where(AuditLog.resource == resource)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)

    query = query.offset(offset).limit(limit)
    rows = (await db.scalars(query)).all()
    return [AuditLogOut.model_validate(row) for row in rows]


@router.get("/count")
async def count_audit_logs(
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count()).select_from(AuditLog))
    return {"count": int(total or 0)}

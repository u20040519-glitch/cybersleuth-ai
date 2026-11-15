# =============================================================================
# CYBERSLEUTH AI - Audit trail writer
# =============================================================================
# Every privileged action is recorded. The audit table is append-only at the
# database level, so this writer only ever inserts.
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog

logger = logging.getLogger(__name__)


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    resource: str,
    user_id: Optional[Any] = None,
    user_name: str = "system",
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    """Append one entry to the audit trail.

    Audit failures are logged but never raised: losing an audit row must not
    take down the operation that was being audited.
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            user_name=user_name,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details or {},
        )
        db.add(entry)
        await db.flush()
        return entry
    except Exception:
        logger.exception("Failed to write audit entry action=%s resource=%s", action, resource)
        return AuditLog(action=action, resource=resource, user_name=user_name)

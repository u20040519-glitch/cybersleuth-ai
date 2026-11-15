# =============================================================================
# CYBERSLEUTH AI - Authentication dependencies
# =============================================================================
# Request-scoped identity resolution. The bearer token is decoded first (no
# database access needed), the identity is pushed into the session, and the
# SQLAlchemy `after_begin` hook sets the matching PostgreSQL GUCs. Every
# subsequent query therefore runs under the correct RLS policy.
# =============================================================================

from __future__ import annotations

import uuid
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, set_db_identity
from app.core.security import TokenPayload, decode_token
from app.models import Profile

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def _identity_from_request(request: Request, payload: TokenPayload) -> None:
    """Record the caller's identity on the request so the DB session can use it."""
    request.state.user_id = payload.user_id
    request.state.user_email = payload.email
    request.state.user_role = payload.role
    request.state.token_payload = payload


async def get_current_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> TokenPayload:
    """Decode the bearer token and attach the identity to the request."""
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_EXCEPTION

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise CREDENTIALS_EXCEPTION

    _identity_from_request(request, payload)
    return payload


async def get_current_user(
    request: Request,
    token: TokenPayload = Depends(get_current_token),
    db: AsyncSession = Depends(get_db),
) -> Profile:
    """Resolve the authenticated user, enforcing RLS by setting the identity."""
    # Publish the identity before the first query so that every statement in
    # this transaction runs under the correct RLS policy.
    await set_db_identity(
        db, user_id=str(token.user_id), role=token.role, email=token.email
    )

    profile = await db.scalar(select(Profile).where(Profile.id == token.user_id))

    if profile is None:
        raise CREDENTIALS_EXCEPTION

    request.state.profile = profile
    return profile


async def get_optional_user(
    request: Request,
    token: TokenPayload = Depends(get_current_token),
    db: AsyncSession = Depends(get_db),
) -> Optional[Profile]:
    """Like `get_current_user` but tolerates a missing profile."""
    await set_db_identity(
        db, user_id=str(token.user_id), role=token.role, email=token.email
    )
    return await db.scalar(select(Profile).where(Profile.id == token.user_id))


async def require_supervisor(
    profile: Profile = Depends(get_current_user),
) -> Profile:
    """Dependency that only supervisors satisfy."""
    if profile.role != "supervisor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires the supervisor role",
        )
    return profile


def current_user_id(request: Request) -> uuid.UUID:
    """The authenticated user id, taken from the request state."""
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise CREDENTIALS_EXCEPTION
    return user_id


def client_ip(request: Request) -> Optional[str]:
    """Best-effort client IP, honouring a single proxy hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None

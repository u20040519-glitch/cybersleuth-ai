# =============================================================================
# PROJECT NEXUS AI - API Dependencies
# =============================================================================
# Authentication dependencies: get current user from JWT cookie/header.
# =============================================================================

import logging
from typing import Optional
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

# OAuth2 scheme for token in Authorization header (fallback)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = None,
) -> User:
    """Get the current authenticated user from a secure HTTP-only cookie or Bearer header."""
    token: Optional[str] = None

    # Prefer HTTP-only cookie (never exposes token to JavaScript)
    if access_token:
        token = access_token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )
    return current_user


async def get_verified_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Ensure the current user is verified (email verification required)."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return current_user


def require_role(*allowed_roles: str):
    """Dependency factory to require specific roles."""

    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker
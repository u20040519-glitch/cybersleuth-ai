# =============================================================================
# PROJECT NEXUS AI - API Dependencies
# =============================================================================
# Authentication dependencies: get current user from JWT cookie/header.
# RLS dependencies: set PostgreSQL session variables for Row Level Security.
# =============================================================================

import logging
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.database import AsyncSessionLocal, get_db
from app.models import User

logger = logging.getLogger(__name__)

# OAuth2 scheme for token in Authorization header (fallback)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Step 1: Get DB session without RLS (for authentication lookup)
# ---------------------------------------------------------------------------

async def get_db_raw() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a raw database session (no RLS context)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Step 2: Authenticate user (uses raw DB session)
# ---------------------------------------------------------------------------

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_raw),
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


# ---------------------------------------------------------------------------
# Step 3: Get DB session WITH RLS context (for authorized operations)
# ---------------------------------------------------------------------------

async def get_db_with_rls(
    current_user: User = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session with RLS context set
    based on the authenticated user. Use this for all data operations after auth."""
    async with AsyncSessionLocal() as session:
        try:
            # Set PostgreSQL session variables for Row Level Security
            if settings.database_url.startswith("postgresql"):
                await session.execute(
                    text("SELECT set_config('app.current_user_id', $1, true)"),
                    [str(current_user.id)],
                )
                await session.execute(
                    text("SELECT set_config('app.current_user_role', $1, true)"),
                    [current_user.role],
                )
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Convenience aliases
# ---------------------------------------------------------------------------

# For endpoints that need both the user and an RLS-enabled DB session
async def get_rls_db(
    current_user: User = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_db_with_rls - provides DB session with RLS context."""
    async with AsyncSessionLocal() as session:
        try:
            if settings.database_url.startswith("postgresql"):
                await session.execute(
                    text("SELECT set_config('app.current_user_id', $1, true)"),
                    [str(current_user.id)],
                )
                await session.execute(
                    text("SELECT set_config('app.current_user_role', $1, true)"),
                    [current_user.role],
                )
            yield session
        finally:
            await session.close()


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

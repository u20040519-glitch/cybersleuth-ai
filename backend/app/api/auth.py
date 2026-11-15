# =============================================================================
# CYBERSLEUTH AI - Authentication routes
# =============================================================================

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.ratelimit import get_limiter
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.security.deps import client_ip, get_current_user
from app.services.audit import record_audit
from app.services.auth import AuthenticationError, RegistrationError, authenticate, register_user

router = APIRouter(prefix="/auth", tags=["auth"])

# Auth endpoints are the abuse-prone surface; limit them per client IP.
_login_limiter = get_limiter("auth-login", max_requests=10, window_seconds=60)
_register_limiter = get_limiter("auth-register", max_requests=5, window_seconds=60)


def _enforce_rate_limit(request: Request, limiter, bucket: str) -> None:
    key = f"{bucket}:{client_ip(request) or 'unknown'}"
    allowed, retry_after = limiter.check(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def _issue_tokens(profile) -> TokenResponse:
    access_token, _ = create_access_token(profile.id, profile.email, profile.role)
    refresh_token, _, _ = create_refresh_token(profile.id, profile.email, profile.role)
    return TokenResponse(
        user=UserOut.model_validate(profile),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create an account and sign the new user in."""
    _enforce_rate_limit(request, _register_limiter, "register")
    try:
        profile = await register_user(
            db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
        )
    except RegistrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except AuthenticationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    await record_audit(
        db,
        action="register",
        resource="profile",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(profile.id),
        ip_address=client_ip(request),
    )

    return _issue_tokens(profile)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Exchange credentials for an access token and a refresh token."""
    _enforce_rate_limit(request, _login_limiter, "login")
    try:
        profile = await authenticate(db, email=payload.email, password=payload.password)
    except AuthenticationError as exc:
        await record_audit(
            db,
            action="login_failed",
            resource="session",
            user_name=payload.email,
            ip_address=client_ip(request),
            details={"email": payload.email},
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    await record_audit(
        db,
        action="login",
        resource="session",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(profile.id),
        ip_address=client_ip(request),
    )

    return _issue_tokens(profile)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Issue a new access token from a valid refresh token."""
    import jwt

    try:
        token = decode_token(payload.refresh_token, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    from sqlalchemy import select

    from app.core.database import set_db_identity
    from app.models import Profile

    # The profile is protected by RLS, so publish the identity before reading it.
    await set_db_identity(db, user_id=str(token.user_id), role=token.role, email=token.email)
    profile = await db.scalar(select(Profile).where(Profile.id == token.user_id))
    if profile is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")

    return _issue_tokens(profile)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    profile=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record the end of a session.

    Access tokens are stateless and short lived, so the client discards them;
    the audit trail keeps the record.
    """
    await record_audit(
        db,
        action="logout",
        resource="session",
        user_id=profile.id,
        user_name=profile.full_name,
        resource_id=str(profile.id),
        ip_address=client_ip(request),
    )
    return MessageResponse(message="Signed out")


@router.get("/me", response_model=UserOut)
async def me(profile=Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserOut.model_validate(profile)

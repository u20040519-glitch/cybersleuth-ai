# =============================================================================
# PROJECT NEXUS AI - Authentication API Routes
# =============================================================================
# Registration, login, logout, email verification, password reset.
# All routes connect to real backend services and database.
# =============================================================================

import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.database import get_db
from app.models import User
from app.schemas.user import (
    UserRegistration,
    UserLogin,
    UserResponse,
    TokenResponse,
    EmailVerificationRequest,
    ForgotPassword,
    ResetPassword,
    ChangePassword,
    UserProfileUpdate,
    ErrorResponse,
)
from app.services.auth import (
    register_user,
    authenticate_user,
    verify_email_token,
    resend_verification_email,
    request_password_reset,
    reset_password_with_token,
    logout_user,
    change_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def register(
    registration: UserRegistration,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account. Requires explicit terms and privacy acceptance."""
    try:
        user = await register_user(
            db=db,
            registration=registration,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return UserResponse.model_validate(user)
    except ValueError as exc:
        logger.error("Registration validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Registration error: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your input and try again.",
        )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and issue access + refresh tokens in secure HTTP-only cookies."""
    user = await authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    if not user:
        # Generic error - do not reveal whether email exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email before logging in.",
        )

    # Create tokens
    access_token = create_access_token(subject=str(user.id), additional_claims={"role": user.role})
    refresh_token = create_refresh_token(subject=str(user.id))

    # Set secure HTTP-only cookies
    cookie_kwargs = {
        "httponly": True,
        "secure": settings.session_cookie_secure,
        "samesite": settings.session_cookie_samesite,
        "path": "/",
    }
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        **cookie_kwargs,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        **cookie_kwargs,
    )

    logger.info("User logged in: %s", user.email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Invalidate the active session and clear authentication cookies."""
    await logout_user(
        db=db,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Clear secure cookies
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")

    return JSONResponse(content={"message": "Logged out successfully"})


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Verify email ownership using a secure token."""
    try:
        await verify_email_token(db=db, token=token)
        return JSONResponse(content={"message": "Email verified successfully"})
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    request_data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Request a new verification email. Rate-limited."""
    success = await resend_verification_email(db=db, email=request_data.email)
    # Always return success to avoid email enumeration
    return JSONResponse(
        content={"message": "If an unverified account exists, a verification email has been sent."}
    )


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request_data: ForgotPassword,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Request a password reset. Always returns success to prevent email enumeration."""
    await request_password_reset(db=db, email=request_data.email)
    return JSONResponse(
        content={
            "message": "If an account exists for this email, a password reset link has been sent."
        }
    )


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPassword,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Reset password using a valid single-use token."""
    try:
        await reset_password_with_token(
            db=db,
            token=request_data.token,
            new_password=request_data.new_password,
        )
        return JSONResponse(content={"message": "Password reset successfully"})
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Change password (authenticated)
# ---------------------------------------------------------------------------

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password_route(
    request_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Change the password for the currently authenticated user."""
    try:
        await change_password(
            db=db,
            user_id=current_user.id,
            current_password=request_data.current_password,
            new_password=request_data.new_password,
        )
        return JSONResponse(content={"message": "Password changed successfully"})
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Profile management
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get the current user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update the current user's profile."""
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
) -> TokenResponse:
    """Refresh the access token using the refresh token cookie."""
    from app.core.security import create_access_token, create_refresh_token, decode_token

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    new_access_token = create_access_token(subject=str(user_id))

    cookie_kwargs = {
        "httponly": True,
        "secure": settings.session_cookie_secure,
        "samesite": settings.session_cookie_samesite,
        "path": "/",
    }
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        **cookie_kwargs,
    )

    return TokenResponse(access_token=new_access_token)
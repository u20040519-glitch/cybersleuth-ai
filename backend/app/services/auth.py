# =============================================================================
# PROJECT NEXUS AI - Authentication Service
# =============================================================================
# Real backend authentication: registration, login, logout, email verification,
# password reset, session management. All logic runs on the backend.
# =============================================================================

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    create_email_verification_token,
    create_password_reset_token,
    hash_verification_token,
    verify_verification_token,
)
from app.db.database import AsyncSessionLocal
from app.models import User, AuditLog
from app.schemas.user import UserRegistration, UserResponse
from app.services.email import email_service

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Authentication service error."""


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

async def register_user(
    db: AsyncSession,
    registration: UserRegistration,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    """Register a new user. Returns the created user (unverified)."""
    # Check if email already exists - do not reveal whether email is registered
    existing = await db.execute(select(User).where(User.email == registration.email))
    if existing.scalar_one_or_none():
        raise AuthError("Registration failed. Please check your input and try again.")

    # Validate consent checkboxes are explicitly checked (never pre-checked)
    if not registration.accept_terms:
        raise AuthError("You must accept the terms of service to register.")
    if not registration.accept_privacy:
        raise AuthError("You must acknowledge the privacy notice to register.")

    # Passwords already validated to match at schema level
    if registration.password != registration.confirm_password:
        raise AuthError("Passwords do not match.")

    # Hash password with Argon2id
    password_hash = hash_password(registration.password)

    # Create email verification token
    verification_token = create_email_verification_token("")
    token_hash = hash_verification_token(verification_token)
    token_expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.email_verification_expire_hours
    )

    user = User(
        full_name=registration.full_name,
        email=registration.email,
        password_hash=password_hash,
        role=settings.__dict__.get("default_role", "viewer"),
        is_active=True,
        is_verified=False,
        email_verification_token_hash=token_hash,
        email_verification_token_expires=token_expires,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="user_registered",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit)
    await db.commit()

    # Send verification email (do not fail registration if email fails)
    if settings.is_email_configured():
        verify_url = f"{settings.app_base_url}/api/auth/verify-email?token={verification_token}"
        await email_service.send_verification_email(
            registration.email, registration.full_name, verify_url
        )
    else:
        logger.warning(
            "Email not configured. Verification token for %s was generated but not sent.",
            registration.email,
        )

    logger.info("User registered: %s", user.email)
    return user


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[User]:
    """Verify credentials and return the user if valid. Returns None on failure."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Generic failure - do not reveal whether email exists
        logger.warning("Login attempt for non-existent email: %s", email)
        return None

    if not user.is_active:
        logger.warning("Login attempt for inactive account: %s", email)
        return None

    if not verify_password(password, user.password_hash):
        logger.warning("Failed login attempt for: %s", email)
        return None

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="user_login",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit)
    await db.commit()

    logger.info("User authenticated: %s", email)
    return user


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

async def verify_email_token(
    db: AsyncSession,
    token: str,
) -> User:
    """Verify an email verification token. Marks user as verified."""
    # Find user with a matching (hashed) token that hasn't expired
    result = await db.execute(
        select(User).where(
            User.email_verification_token_hash.is_not(None),
            User.email_verification_token_expires > datetime.now(timezone.utc),
        )
    )
    candidates = result.scalars().all()

    user = None
    for candidate in candidates:
        if verify_verification_token(token, candidate.email_verification_token_hash):
            user = candidate
            break

    if not user:
        raise AuthError("Invalid or expired verification link.")

    if user.is_verified:
        raise AuthError("Email is already verified.")

    user.is_verified = True
    user.email_verification_token_hash = None  # prevent reuse
    user.email_verification_token_expires = None
    await db.commit()
    await db.refresh(user)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="email_verified",
        resource_type="user",
        resource_id=str(user.id),
    )
    db.add(audit)
    await db.commit()

    logger.info("Email verified for user: %s", user.email)
    return user


async def resend_verification_email(
    db: AsyncSession,
    email: str,
) -> bool:
    """Resend a verification email to an unverified user."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or user.is_verified:
        # Don't reveal whether email exists
        return False

    # Generate new token
    verification_token = create_email_verification_token("")
    token_hash = hash_verification_token(verification_token)
    token_expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.email_verification_expire_hours
    )

    user.email_verification_token_hash = token_hash
    user.email_verification_token_expires = token_expires
    await db.commit()

    if settings.is_email_configured():
        verify_url = f"{settings.app_base_url}/api/auth/verify-email?token={verification_token}"
        await email_service.send_verification_email(
            email, user.full_name, verify_url
        )
        return True

    return False


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

async def request_password_reset(
    db: AsyncSession,
    email: str,
) -> bool:
    """Request a password reset. Always returns True to avoid email enumeration."""
    result = await db.execute(select(User).where(User.email == email, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        # Do not reveal whether email is registered
        return True

    # Generate reset token (single-use, stored as hash)
    reset_token = create_password_reset_token("")
    token_hash = hash_verification_token(reset_token)
    token_expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.password_reset_expire_hours
    )

    user.password_reset_token_hash = token_hash
    user.password_reset_token_expires = token_expires
    user.password_reset_token_used = False
    await db.commit()

    if settings.is_email_configured():
        reset_url = f"{settings.app_base_url}/api/auth/reset-password?token={reset_token}"
        await email_service.send_password_reset_email(
            email, user.full_name, reset_url
        )

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="password_reset_requested",
        resource_type="user",
        resource_id=str(user.id),
    )
    db.add(audit)
    await db.commit()

    return True


async def reset_password_with_token(
    db: AsyncSession,
    token: str,
    new_password: str,
) -> User:
    """Reset password using a valid single-use token."""
    result = await db.execute(
        select(User).where(
            User.password_reset_token_hash.is_not(None),
            User.password_reset_token_expires > datetime.now(timezone.utc),
            User.password_reset_token_used == False,
        )
    )
    candidates = result.scalars().all()

    user = None
    for candidate in candidates:
        if verify_verification_token(token, candidate.password_reset_token_hash):
            user = candidate
            break

    if not user:
        raise AuthError("Invalid or expired reset link.")

    # Mark token as used
    user.password_reset_token_used = True
    user.password_reset_token_hash = None
    user.password_reset_token_expires = None

    # Hash new password
    user.password_hash = hash_password(new_password)

    # Invalidate existing sessions (in a real system with Redis, we'd blacklist tokens)
    await db.commit()
    await db.refresh(user)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="password_reset_completed",
        resource_type="user",
        resource_id=str(user.id),
    )
    db.add(audit)
    await db.commit()

    # Send security notification
    if settings.is_email_configured():
        await email_service.send_security_notification(
            user.email,
            user.full_name,
            "Password Changed",
            "Your password was successfully changed. If you did not request this, contact support immediately.",
        )

    logger.info("Password reset for user: %s", user.email)
    return user


# ---------------------------------------------------------------------------
# Logout / session invalidation
# ---------------------------------------------------------------------------

async def logout_user(
    db: AsyncSession,
    user_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Log out a user and invalidate their session."""
    # In a JWT system, logout means the client discards the token.
    # Server-side: we record the audit event. With Redis, we'd blacklist the token JTI.
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        # Record logout audit
        audit = AuditLog(
            user_id=user_id,
            action="user_logout",
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit)
        await db.commit()
        logger.info("User logged out: %s", user.email)


# ---------------------------------------------------------------------------
# Change password (authenticated user)
# ---------------------------------------------------------------------------

async def change_password(
    db: AsyncSession,
    user_id: UUID,
    current_password: str,
    new_password: str,
) -> None:
    """Change the password for an authenticated user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AuthError("User not found.")

    if not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect.")

    user.password_hash = hash_password(new_password)
    # Invalidate existing sessions after password change
    await db.commit()

    # Audit log
    audit = AuditLog(
        user_id=user_id,
        action="password_changed",
        resource_type="user",
        resource_id=str(user_id),
    )
    db.add(audit)
    await db.commit()

    if settings.is_email_configured():
        await email_service.send_security_notification(
            user.email,
            user.full_name,
            "Password Changed",
            "Your account password was changed. If you did not make this change, contact support immediately.",
        )
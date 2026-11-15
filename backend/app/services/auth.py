# =============================================================================
# CYBERSLEUTH AI - Authentication service
# =============================================================================
# Two providers behind one interface:
#
#   local     the application owns `auth.users` and verifies Argon2 hashes
#   supabase  GoTrue (Supabase Auth) owns identities and the password check
#
# Both produce the same result: a `profiles` row (created by the
# `handle_new_user` trigger in either environment) and our own signed JWTs,
# so every downstream code path is identical.
# =============================================================================

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import set_db_identity
from app.core.security import hash_password, verify_password
from app.models import AuthUser, Profile

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when credentials are rejected."""

    def __init__(self, message: str = "Invalid credentials", status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RegistrationError(AuthenticationError):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message, status_code)


def _uses_supabase_auth() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: str = "investigator",
) -> Profile:
    """Create an identity and its profile. Raises `RegistrationError` on failure."""
    email = email.strip().lower()

    if _uses_supabase_auth():
        return await _register_via_supabase(db, email, password, full_name, role)

    existing = await db.scalar(select(AuthUser).where(AuthUser.email == email))
    if existing is not None:
        raise RegistrationError("An account with that email already exists")

    user = AuthUser(
        email=email,
        encrypted_password=hash_password(password),
        email_confirmed_at=datetime.now(timezone.utc),
        raw_user_meta_data={"full_name": full_name, "role": role},
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Publish the identity so that the `profiles` row (which is protected by
    # RLS) can be read back inside this transaction.
    await set_db_identity(db, user_id=str(user.id), role=role, email=email)

    # The `handle_new_user` trigger creates the profile row.
    await db.flush()

    profile = await db.scalar(select(Profile).where(Profile.id == user.id))
    if profile is None:
        # Trigger did not fire (for example on a partially migrated database).
        profile = Profile(
            id=user.id,
            email=email,
            full_name=full_name,
            role=role,
        )
        db.add(profile)
        await db.flush()

    return profile


async def _register_via_supabase(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    role: str,
) -> Profile:
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "password": password,
        "data": {"full_name": full_name, "role": role},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(f"{url}/signup", json=payload, headers=headers)

    if response.status_code >= 400:
        detail = response.json() if response.content else {}
        message = detail.get("msg") or detail.get("error_description") or "Registration failed"
        raise RegistrationError(str(message), status_code=response.status_code)

    body = response.json()
    user_id = body.get("id") or (body.get("user") or {}).get("id")
    if not user_id:
        raise RegistrationError("Supabase did not return a user id")

    await set_db_identity(db, user_id=str(user_id), role=role, email=email)

    # The trigger creates the profile row on Supabase too; give the write a
    # moment to land before reading it back.
    profile = None
    for _ in range(10):
        profile = await db.scalar(select(Profile).where(Profile.id == user_id))
        if profile is not None:
            break
        await db.flush()

    if profile is None:
        profile = Profile(id=user_id, email=email, full_name=full_name, role=role)
        db.add(profile)
        await db.flush()

    return profile


# -----------------------------------------------------------------------------
# Login
# -----------------------------------------------------------------------------
async def authenticate(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> Profile:
    """Verify credentials and return the matching profile."""
    email = email.strip().lower()

    if _uses_supabase_auth():
        return await _authenticate_via_supabase(db, email, password)

    user = await db.scalar(select(AuthUser).where(AuthUser.email == email))
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid email or password")

    if not verify_password(password, user.encrypted_password):
        raise AuthenticationError("Invalid email or password")

    # The profile is protected by RLS, so the identity has to be published
    # before it can be read.
    role = (user.raw_user_meta_data or {}).get("role", "investigator")
    await set_db_identity(db, user_id=str(user.id), role=role, email=user.email)

    profile = await db.scalar(select(Profile).where(Profile.id == user.id))
    if profile is None:
        raise AuthenticationError("Account is missing its profile record")

    return profile


async def _authenticate_via_supabase(
    db: AsyncSession,
    email: str,
    password: str,
) -> Profile:
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/token"
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{url}?grant_type=password",
            json={"email": email, "password": password},
            headers=headers,
        )

    if response.status_code >= 400:
        raise AuthenticationError("Invalid email or password")

    body = response.json()
    user_id = body.get("user", {}).get("id")
    if not user_id:
        raise AuthenticationError("Supabase did not return a user id")

    await set_db_identity(db, user_id=str(user_id), email=email)

    profile = await db.scalar(select(Profile).where(Profile.id == user_id))
    if profile is None:
        raise AuthenticationError("Account is missing its profile record")

    return profile


# -----------------------------------------------------------------------------
# Lookup helpers
# -----------------------------------------------------------------------------
async def get_profile_by_email(db: AsyncSession, email: str) -> Optional[Profile]:
    return await db.scalar(select(Profile).where(Profile.email == email.strip().lower()))

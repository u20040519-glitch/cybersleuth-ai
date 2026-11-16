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

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import set_db_identity
from app.core.security import hash_password, verify_password
from app.models import AuthUser, Profile

logger = logging.getLogger(__name__)

# Whether the SECURITY DEFINER helpers from migration 013 exist. They are
# created on a standalone PostgreSQL (the local parity shim) and are absent on
# Supabase, where GoTrue owns `auth.users` and the table-level grants from
# migration 008 still apply. The answer is cached per process.
_local_helpers: Optional[bool] = None


async def _has_local_auth_helpers(db: AsyncSession) -> bool:
    """True when the migration 013 helper functions are available."""
    global _local_helpers

    if _local_helpers is None:
        try:
            row = await db.execute(
                text(
                    "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                    "WHERE n.nspname = 'public' AND p.proname = 'local_auth_credentials' "
                    "LIMIT 1"
                )
            )
            _local_helpers = row.first() is not None
        except Exception:  # pragma: no cover - defensive
            logger.exception("Could not determine whether the local auth helpers exist")
            _local_helpers = False

        logger.info("Local authentication helpers available: %s", _local_helpers)

    return _local_helpers


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

    metadata = {"full_name": full_name, "role": role}

    if await _has_local_auth_helpers(db):
        user_id = await _create_local_user(db, email, password, metadata)
    else:
        user_id = await _create_local_user_via_table(db, email, password, metadata)

    # Publish the identity so that the `profiles` row (which is protected by
    # RLS) can be read back inside this transaction.
    await set_db_identity(db, user_id=str(user_id), role=role, email=email)

    # The `handle_new_user` trigger creates the profile row.
    await db.flush()

    profile = await db.scalar(select(Profile).where(Profile.id == user_id))
    if profile is None:
        # Trigger did not fire (for example on a partially migrated database).
        profile = Profile(
            id=user_id,
            email=email,
            full_name=full_name,
            role=role,
        )
        db.add(profile)
        await db.flush()

    return profile


async def _create_local_user(
    db: AsyncSession,
    email: str,
    password: str,
    metadata: dict,
) -> uuid.UUID:
    """Create an identity through the SECURITY DEFINER helper.

    The application role has no INSERT privilege on `auth.users` (migration
    012), so the row is written by the helper function, which runs with the
    privileges of its owner.
    """
    existing = await _local_credentials(db, email)
    if existing is not None:
        raise RegistrationError("An account with that email already exists")

    user_id = uuid.uuid4()
    result = await db.execute(
        text("SELECT public.local_auth_create_user(:id, :email, :password, :metadata)"),
        {
            "id": user_id,
            "email": email,
            "password": hash_password(password),
            "metadata": json.dumps(metadata),
        },
    )
    created = result.scalar()
    if not created:
        raise RegistrationError("Could not create the account")

    return uuid.UUID(str(created))


async def _create_local_user_via_table(
    db: AsyncSession,
    email: str,
    password: str,
    metadata: dict,
) -> uuid.UUID:
    """Create an identity with the table-level grants (Supabase parity path)."""
    existing = await db.scalar(select(AuthUser).where(AuthUser.email == email))
    if existing is not None:
        raise RegistrationError("An account with that email already exists")

    user = AuthUser(
        email=email,
        encrypted_password=hash_password(password),
        email_confirmed_at=datetime.now(timezone.utc),
        raw_user_meta_data=metadata,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    return user.id


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

    credentials = await _local_credentials(db, email)
    if credentials is None or not credentials.get("is_active", True):
        raise AuthenticationError("Invalid email or password")

    if not verify_password(password, credentials["encrypted_password"]):
        raise AuthenticationError("Invalid email or password")

    # The profile is protected by RLS, so the identity has to be published
    # before it can be read.
    user_id = credentials["id"]
    role = (credentials.get("raw_user_meta_data") or {}).get("role", "investigator")
    await set_db_identity(db, user_id=str(user_id), role=role, email=email)

    profile = await db.scalar(select(Profile).where(Profile.id == user_id))
    if profile is None:
        raise AuthenticationError("Account is missing its profile record")

    return profile


async def _local_credentials(db: AsyncSession, email: str) -> Optional[dict]:
    """Read the credential row of a single account.

    When the migration 013 helpers exist they are used: the application role
    has no SELECT privilege on `auth.users` (migration 012), so the row is read
    through a SECURITY DEFINER function. On Supabase the helpers do not exist
    and the table-level grants from migration 008 still apply, so the ORM is
    used there.
    """
    if await _has_local_auth_helpers(db):
        result = await db.execute(
            text(
                "SELECT id, email, encrypted_password, raw_user_meta_data, is_active "
                "FROM public.local_auth_credentials(:email)"
            ),
            {"email": email},
        )
        row = result.mappings().first()
        return dict(row) if row is not None else None

    user = await db.scalar(select(AuthUser).where(AuthUser.email == email))
    if user is None:
        return None

    return {
        "id": user.id,
        "email": user.email,
        "encrypted_password": user.encrypted_password,
        "raw_user_meta_data": user.raw_user_meta_data or {},
        "is_active": user.is_active,
    }


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

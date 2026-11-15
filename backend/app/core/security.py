# =============================================================================
# CYBERSLEUTH AI - Password hashing and JWT handling
# =============================================================================

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher(
    memory_cost=settings.ARGON2ID_MEMORY_COST,
    time_cost=settings.ARGON2ID_TIME_COST,
    parallelism=settings.ARGON2ID_PARALLELISM,
)

# Fast, deterministic hash used to verify that a file has not changed.
_file_hasher = hashlib.sha256()


# -----------------------------------------------------------------------------
# Passwords
# -----------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verification of a plaintext password against an Argon2 hash."""
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:  # pragma: no cover - malformed hash in the database
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when a stored hash was produced with weaker parameters."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:
        return True


# -----------------------------------------------------------------------------
# File integrity
# -----------------------------------------------------------------------------
def sha256_file(path) -> str:
    """Streaming SHA-256 of a file, returned as lowercase hex."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------------
# Tokens
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class TokenPayload:
    user_id: uuid.UUID
    email: str
    role: str
    token_type: str
    expires_at: datetime
    jti: str


def _encode(payload: Dict[str, Any], expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    body = {
        **payload,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "iss": "cybersleuth-ai",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(body, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID, email: str, role: str) -> tuple[str, datetime]:
    """Create a short-lived access token. Returns (token, expiry)."""
    expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = secrets.token_urlsafe(16)
    token = _encode(
        {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "type": "access",
            "jti": jti,
        },
        expires,
    )
    return token, datetime.now(timezone.utc) + expires


def create_refresh_token(user_id: uuid.UUID, email: str, role: str) -> tuple[str, datetime, str]:
    """Create a long-lived refresh token. Returns (token, expiry, jti)."""
    expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    jti = secrets.token_urlsafe(24)
    token = _encode(
        {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "type": "refresh",
            "jti": jti,
        },
        expires,
    )
    return token, datetime.now(timezone.utc) + expires, jti


def decode_token(token: str, expected_type: str = "access") -> TokenPayload:
    """Decode and validate a JWT. Raises `jwt` exceptions on failure."""
    payload = jwt.decode(
        token,
        settings.APP_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer="cybersleuth-ai",
        options={"require": ["exp", "sub", "type"]},
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected a {expected_type} token")

    return TokenPayload(
        user_id=uuid.UUID(str(payload["sub"])),
        email=str(payload.get("email", "")),
        role=str(payload.get("role", "investigator")),
        token_type=str(payload["type"]),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        jti=str(payload.get("jti", "")),
    )


def constant_time_equals(left: str, right: str) -> bool:
    """Timing-safe string comparison."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))

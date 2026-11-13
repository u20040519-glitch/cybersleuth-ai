# =============================================================================
# PROJECT NEXUS AI - Security & Cryptography
# =============================================================================
# Password hashing with Argon2id (via argon2-cffi), JWT token management,
# secure token generation. Secrets are NEVER logged or exposed.
# =============================================================================

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from argon2 import PasswordHasher, Type, exceptions as argon2_exceptions
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Password hashing (Argon2id)
# ---------------------------------------------------------------------------

# Configure Argon2id with security parameters from settings
_hasher = PasswordHasher(
    memory_cost=settings.argon2id_memory_cost,
    time_cost=settings.argon2id_time_cost,
    parallelism=settings.argon2id_parallelism,
    salt_len=16,
    hash_len=32,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id. Returns the encoded hash string."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an Argon2id hash."""
    try:
        _hasher.verify(hashed_password, plain_password)
        return True
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception as exc:
        logger.error("Password verification error: %s", type(exc).__name__)
        return False


# ---------------------------------------------------------------------------
# Secure token generation
# ---------------------------------------------------------------------------

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token (URL-safe base64)."""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token for storage. Only hashes are stored, never raw tokens."""
    return _hasher.hash(token)


def verify_token(plain_token: str, hashed_token: str) -> bool:
    """Verify a plain token against its stored hash."""
    try:
        _hasher.verify(hashed_token, plain_token)
        return True
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception as exc:
        logger.error("Token verification error: %s", type(exc).__name__)
        return False


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.app_secret_key, algorithm="HS256"
    )
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.app_secret_key, algorithm="HS256"
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT token. Returns None if invalid/expired."""
    try:
        payload = jwt.decode(
            token, settings.app_secret_key, algorithms=["HS256"]
        )
        return payload
    except JWTError:
        return None
    except Exception as exc:
        logger.error("Token decode error: %s", type(exc).__name__)
        return None


# ---------------------------------------------------------------------------
# Email verification / password reset tokens
# ---------------------------------------------------------------------------

def create_email_verification_token(user_id: str = "") -> str:
    """Create a secure email verification token (stored as hash)."""
    return generate_secure_token()


def create_password_reset_token(user_id: str = "") -> str:
    """Create a secure password reset token (stored as hash, single-use)."""
    return generate_secure_token()


def hash_verification_token(token: str) -> str:
    """Hash a verification token for storage."""
    return hash_token(token)


def verify_verification_token(plain_token: str, hashed_token: str) -> bool:
    """Verify a verification token against its hash."""
    return verify_token(plain_token, hashed_token)
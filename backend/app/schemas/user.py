# =============================================================================
# PROJECT NEXUS AI - Pydantic Schemas
# =============================================================================
# Request/response validation schemas for the API.
# =============================================================================

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserRegistration(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str
    accept_terms: bool = Field(..., description="Must accept terms of service")
    accept_privacy: bool = Field(..., description="Must acknowledge privacy notice")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Jane Investigator",
                "email": "jane@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "accept_terms": True,
                "accept_privacy": True,
            }
        }
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: str
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    institution: Optional[str] = Field(None, max_length=255)
    role_in_org: Optional[str] = Field(None, max_length=100)
    forensic_interest: Optional[str] = Field(None, max_length=255)


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12, max_length=128)


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str = Field(..., min_length=12, max_length=128)


# ---------------------------------------------------------------------------
# Token schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class EmailVerificationRequest(BaseModel):
    email: EmailStr


# ---------------------------------------------------------------------------
# Case schemas
# ---------------------------------------------------------------------------

class CaseCreate(BaseModel):
    case_number: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class CaseResponse(BaseModel):
    id: UUID
    case_number: str
    title: str
    description: Optional[str]
    status: str
    owner_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Consent schemas
# ---------------------------------------------------------------------------

class ConsentPreference(BaseModel):
    purpose: str
    granted: bool


class ConsentRecordResponse(BaseModel):
    id: UUID
    purpose: str
    policy_version: str
    status: str
    granted_at: Optional[datetime]
    withdrawn_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Cookie preference schemas
# ---------------------------------------------------------------------------

class CookiePreferenceUpdate(BaseModel):
    essential: bool = True
    analytics: bool = False
    functional: bool = False
    marketing: bool = False
    consent_version: str


class CookiePreferenceResponse(BaseModel):
    id: UUID
    essential: bool
    analytics: bool
    functional: bool
    marketing: bool
    consent_version: str
    consent_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Data deletion request schemas
# ---------------------------------------------------------------------------

class DataDeletionRequestCreate(BaseModel):
    reason: Optional[str] = None


class DataDeletionRequestResponse(BaseModel):
    id: UUID
    tracking_id: str
    status: str
    requested_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Generic error response
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    message: str
    code: Optional[str] = None
# =============================================================================
# PROJECT NEXUS AI - Pydantic Schemas Package
# =============================================================================

from app.schemas.user import (  # noqa: F401
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
    CaseCreate,
    CaseResponse,
    ConsentPreference,
    ConsentRecordResponse,
    CookiePreferenceUpdate,
    CookiePreferenceResponse,
    DataDeletionRequestCreate,
    DataDeletionRequestResponse,
)

__all__ = [
    "UserRegistration",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "EmailVerificationRequest",
    "ForgotPassword",
    "ResetPassword",
    "ChangePassword",
    "UserProfileUpdate",
    "ErrorResponse",
    "CaseCreate",
    "CaseResponse",
    "ConsentPreference",
    "ConsentRecordResponse",
    "CookiePreferenceUpdate",
    "CookiePreferenceResponse",
    "DataDeletionRequestCreate",
    "DataDeletionRequestResponse",
]
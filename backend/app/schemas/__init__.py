# =============================================================================
# CYBERSLEUTH AI - Pydantic schemas (the public API contract)
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Users and auth
# -----------------------------------------------------------------------------
class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    avatar_url: Optional[str] = None
    organization: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    confirm_password: str
    role: str = Field(default="investigator", pattern="^(investigator|supervisor)$")

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, v: str, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    user: UserOut
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MessageResponse(BaseModel):
    ok: bool = True
    message: str = ""


# -----------------------------------------------------------------------------
# Investigations
# -----------------------------------------------------------------------------
class InvestigationBase(BaseModel):
    case_id: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    category: str = Field(default="general", max_length=64)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    status: str = Field(default="draft", pattern="^(draft|active|review|closed|archived)$")
    notes: Optional[str] = None


class InvestigationCreate(InvestigationBase):
    member_ids: List[uuid.UUID] = Field(default_factory=list)


class InvestigationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=64)
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high|critical)$")
    status: Optional[str] = Field(default=None, pattern="^(draft|active|review|closed|archived)$")
    notes: Optional[str] = None


class InvestigationOut(ORMModel):
    id: uuid.UUID
    case_id: str
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    status: str
    owner_id: uuid.UUID
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    evidence_count: int = 0
    analysis_count: int = 0
    owner_name: Optional[str] = None
    assigned_users: List[str] = Field(default_factory=list)


class InvestigationDetail(InvestigationOut):
    members: List["MemberOut"] = Field(default_factory=list)
    evidence: List["EvidenceOut"] = Field(default_factory=list)
    analysis: List["AnalysisResultOut"] = Field(default_factory=list)


class MemberOut(ORMModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    user_id: uuid.UUID
    member_role: str
    created_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None


class MemberCreate(BaseModel):
    user_id: uuid.UUID
    member_role: str = Field(default="member", pattern="^(member|reviewer|lead)$")


# -----------------------------------------------------------------------------
# Evidence
# -----------------------------------------------------------------------------
class EvidenceOut(ORMModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    original_filename: str
    file_size: int
    mime_type: str
    sha256_hash: str
    storage_path: str
    status: str
    uploaded_by: uuid.UUID
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    thumbnail_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    uploaded_by_name: Optional[str] = None


class EvidenceEventOut(ORMModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    event_type: str
    actor_id: Optional[uuid.UUID] = None
    actor_name: str
    timestamp: datetime
    details: Optional[str] = None


class CustodyEntryOut(ORMModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    event_type: str
    actor_id: Optional[uuid.UUID] = None
    actor_name: str
    timestamp: datetime
    details: Optional[str] = None
    previous_hash: str
    event_hash: str


class CustodyVerification(BaseModel):
    evidence_id: uuid.UUID
    event_count: int
    valid: bool
    broken_at: Optional[str] = None
    head_hash: str


class IntegrityCheckResult(BaseModel):
    evidence_id: uuid.UUID
    expected_sha256: str
    actual_sha256: str
    intact: bool
    checked_at: datetime


# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------
MODULES = ("deeptrace", "spytrace", "voiceproof", "cybersleuth")


class AnalysisRequest(BaseModel):
    evidence_id: uuid.UUID
    options: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_id")
    @classmethod
    def _require_id(cls, v):
        if v is None:
            raise ValueError("evidence_id is required")
        return v


class AnalysisResultOut(ORMModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    module: str
    status: str
    result_data: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class AnalysisJobOut(BaseModel):
    job_id: str
    status: str
    module: str
    evidence_id: uuid.UUID
    result: Optional[AnalysisResultOut] = None
    error: Optional[str] = None


# -----------------------------------------------------------------------------
# Correlation
# -----------------------------------------------------------------------------
class CorrelationFindingOut(ORMModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    source_evidence_id: Optional[uuid.UUID] = None
    finding_id: Optional[str] = None
    correlation_type: str
    description: str
    confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    verified: bool
    created_at: datetime
    result_data: Optional[Dict[str, Any]] = None


class CorrelationResponse(BaseModel):
    investigation_id: uuid.UUID
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    connections: List[Dict[str, Any]] = Field(default_factory=list)
    graph: Dict[str, Any] = Field(default_factory=dict)
    findings: List[CorrelationFindingOut] = Field(default_factory=list)
    explanation: Optional[Dict[str, Any]] = None
    generated_at: datetime


# -----------------------------------------------------------------------------
# Reports
# -----------------------------------------------------------------------------
class ReportOut(ORMModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    title: str
    status: str
    storage_path: Optional[str] = None
    file_size: int = 0
    sha256_hash: Optional[str] = None
    generated_by: uuid.UUID
    generated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    download_url: Optional[str] = None


class ReportCreate(BaseModel):
    title: Optional[str] = None
    include_evidence: bool = True
    include_custody: bool = True
    include_analysis: bool = True
    include_correlation: bool = True


# -----------------------------------------------------------------------------
# Audit
# -----------------------------------------------------------------------------
class AuditLogOut(ORMModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_name: str
    action: str
    resource: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime


# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_investigations: int
    active_investigations: int
    evidence_files: int
    analysis_runs: int
    pending_reviews: int
    total_evidence_bytes: int
    module_runs: Dict[str, int] = Field(default_factory=dict)
    recent_investigations: List[InvestigationOut] = Field(default_factory=list)
    generated_at: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    storage: str
    forensic_modules: bool
    ai_explanation: bool
    time: datetime


InvestigationDetail.model_rebuild()

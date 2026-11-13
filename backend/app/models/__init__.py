# =============================================================================
# PROJECT NEXUS AI - Database Models
# =============================================================================
# Models for users, cases, evidence, chain of custody, and compliance tables.
# =============================================================================

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


def _uuid() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    INVESTIGATOR = "investigator"
    ANALYST = "analyst"
    VIEWER = "viewer"


class CaseStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class EvidenceStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ConsentStatus(str, enum.Enum):
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    NOT_REQUESTED = "not_requested"


class DeletionRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(512), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token_hash = Column(String(512), nullable=True)
    email_verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    password_reset_token_hash = Column(String(512), nullable=True)
    password_reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    password_reset_token_used = Column(Boolean, default=False, nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    account_deleted_at = Column(DateTime(timezone=True), nullable=True)
    deletion_requested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    cases = relationship("Case", back_populates="owner", cascade="all, delete-orphan")
    evidence_files = relationship(
        "EvidenceFile", back_populates="uploader", cascade="all, delete-orphan"
    )
    chatbot_conversations = relationship(
        "ChatbotConversation", back_populates="user", cascade="all, delete-orphan"
    )
    investigation_reports = relationship(
        "InvestigationReport", back_populates="owner", cascade="all, delete-orphan"
    )
    consent_records = relationship(
        "ConsentRecord", back_populates="user", cascade="all, delete-orphan"
    )
    cookie_preferences = relationship(
        "CookiePreference", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


# ---------------------------------------------------------------------------
# Case model
# ---------------------------------------------------------------------------

class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_number = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(CaseStatus), default=CaseStatus.DRAFT, nullable=False)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    closed_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="cases")
    evidence_files = relationship(
        "EvidenceFile", back_populates="case", cascade="all, delete-orphan"
    )
    extracted_observations = relationship(
        "ExtractedObservation", back_populates="case", cascade="all, delete-orphan"
    )
    evidence_claims = relationship(
        "EvidenceClaim", back_populates="case", cascade="all, delete-orphan"
    )
    evidence_gaps = relationship(
        "EvidenceGap", back_populates="case", cascade="all, delete-orphan"
    )
    scenarios = relationship(
        "Scenario", back_populates="case", cascade="all, delete-orphan"
    )
    events = relationship(
        "Event", back_populates="case", cascade="all, delete-orphan"
    )
    chain_of_custody_records = relationship(
        "ChainOfCustodyRecord", back_populates="case", cascade="all, delete-orphan"
    )
    investigation_reports = relationship(
        "InvestigationReport", back_populates="case", cascade="all, delete-orphan"
    )
    permissions = relationship(
        "CasePermission", back_populates="case", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("case_number", name="uq_case_number"),
    )


# ---------------------------------------------------------------------------
# Case Permission model (case-level authorization)
# ---------------------------------------------------------------------------

class CasePermission(Base):
    __tablename__ = "case_permissions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission = Column(String(50), nullable=False)  # read, write, admin
    granted_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", back_populates="permissions")
    user = relationship("User", foreign_keys=[user_id])
    grantor = relationship("User", foreign_keys=[granted_by])


# ---------------------------------------------------------------------------
# Evidence File model
# ---------------------------------------------------------------------------

class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    uploader_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(200), nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False, index=True)
    status = Column(Enum(EvidenceStatus), default=EvidenceStatus.UPLOADED, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    case = relationship("Case", back_populates="evidence_files")
    uploader = relationship("User", back_populates="evidence_files")


# ---------------------------------------------------------------------------
# Extracted Observation (ECHO)
# ---------------------------------------------------------------------------

class ExtractedObservation(Base):
    __tablename__ = "extracted_observations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_file_id = Column(
        UUID(as_uuid=False), ForeignKey("evidence_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    observation_text = Column(Text, nullable=False)
    confidence_score = Column(Integer, nullable=True)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", back_populates="extracted_observations")


# ---------------------------------------------------------------------------
# Evidence Claim (MOSAIC)
# ---------------------------------------------------------------------------

class EvidenceClaim(Base):
    __tablename__ = "evidence_claims"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_text = Column(Text, nullable=False)
    source_observation_id = Column(
        UUID(as_uuid=False), ForeignKey("extracted_observations.id"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", back_populates="evidence_claims")


# ---------------------------------------------------------------------------
# Evidence Gap (ECHO)
# ---------------------------------------------------------------------------

class EvidenceGap(Base):
    __tablename__ = "evidence_gaps"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    gap_description = Column(Text, nullable=False)
    suggested_evidence = Column(Text, nullable=True)
    priority = Column(String(50), default="medium", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", back_populates="evidence_gaps")


# ---------------------------------------------------------------------------
# Scenario (MOSAIC)
# ---------------------------------------------------------------------------

class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_name = Column(String(255), nullable=False)
    scenario_description = Column(Text, nullable=False)
    confidence_level = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", back_populates="scenarios")


# ---------------------------------------------------------------------------
# Event (TIMEGLASS)
# ---------------------------------------------------------------------------

class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    event_description = Column(Text, nullable=False)
    source_evidence_id = Column(
        UUID(as_uuid=False), ForeignKey("evidence_files.id"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", back_populates="events")


# ---------------------------------------------------------------------------
# Chatbot Conversation & Message
# ---------------------------------------------------------------------------

class ChatbotConversation(Base):
    __tablename__ = "chatbot_conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(
        UUID(as_uuid=False), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="chatbot_conversations")
    messages = relationship(
        "ChatbotMessage", back_populates="conversation", cascade="all, delete-orphan"
    )


class ChatbotMessage(Base):
    __tablename__ = "chatbot_messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    conversation_id = Column(
        UUID(as_uuid=False), ForeignKey("chatbot_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(50), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("ChatbotConversation", back_populates="messages")


# ---------------------------------------------------------------------------
# Investigation Report
# ---------------------------------------------------------------------------

class InvestigationReport(Base):
    __tablename__ = "investigation_reports"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    report_title = Column(String(255), nullable=False)
    report_content = Column(Text, nullable=False)
    report_file_path = Column(String(1000), nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", back_populates="investigation_reports")
    owner = relationship("User", back_populates="investigation_reports")


# ---------------------------------------------------------------------------
# Chain of Custody Record
# ---------------------------------------------------------------------------

class ChainOfCustodyRecord(Base):
    __tablename__ = "chain_of_custody_records"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_file_id = Column(
        UUID(as_uuid=False), ForeignKey("evidence_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action = Column(String(255), nullable=False)
    performed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    case = relationship("Case", back_populates="chain_of_custody_records")


# ---------------------------------------------------------------------------
# Consent Record (privacy compliance)
# ---------------------------------------------------------------------------

class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(255), nullable=False)
    policy_version = Column(String(50), nullable=False)
    status = Column(Enum(ConsentStatus), default=ConsentStatus.NOT_REQUESTED, nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="consent_records")

    __table_args__ = (
        UniqueConstraint("user_id", "purpose", name="uq_user_purpose_consent"),
    )


# ---------------------------------------------------------------------------
# Cookie Preference
# ---------------------------------------------------------------------------

class CookiePreference(Base):
    __tablename__ = "cookie_preferences"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    essential = Column(Boolean, default=True, nullable=False)
    analytics = Column(Boolean, default=False, nullable=False)
    functional = Column(Boolean, default=False, nullable=False)
    marketing = Column(Boolean, default=False, nullable=False)
    consent_version = Column(String(50), nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    withdrawal_timestamp = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="cookie_preferences")


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="audit_logs")


# ---------------------------------------------------------------------------
# Data Deletion Request
# ---------------------------------------------------------------------------

class DataDeletionRequest(Base):
    __tablename__ = "data_deletion_requests"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tracking_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(Enum(DeletionRequestStatus), default=DeletionRequestStatus.PENDING, nullable=False)
    reason = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    retention_basis = Column(Text, nullable=True)  # why evidence retained, if applicable

    reviewer = relationship("User", foreign_keys=[reviewed_by])
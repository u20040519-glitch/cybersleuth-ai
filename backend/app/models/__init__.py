# =============================================================================
# CYBERSLEUTH AI - SQLAlchemy models
# =============================================================================
# These mirror `supabase/migrations/*.sql` exactly. The migration files are the
# source of truth for the deployed database; these classes are the ORM view of
# the same schema.
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# -----------------------------------------------------------------------------
# auth.users - local parity shim for Supabase Auth (GoTrue)
# -----------------------------------------------------------------------------
class AuthUser(Base):
    """Mirror of the `auth.users` table.

    On Supabase this table is owned by GoTrue and must never be written by the
    application. Locally the backend provides an equivalent so that the same
    trigger, policies and code paths work without a cloud project.
    """

    __tablename__ = "users"
    __table_args__ = ({"schema": "auth"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False, default="")
    email_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_user_meta_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# -----------------------------------------------------------------------------
# 1. profiles
# -----------------------------------------------------------------------------
class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), primary_key=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="investigator")
    avatar_url: Mapped[str | None] = mapped_column(Text)
    organization: Mapped[str | None] = mapped_column(String(255))


# -----------------------------------------------------------------------------
# 2. investigations
# -----------------------------------------------------------------------------
class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"
    __table_args__ = (
        UniqueConstraint("case_id", name="uq_investigations_case_id"),
        Index("ix_investigations_owner_id", "owner_id"),
        Index("ix_investigations_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)


# -----------------------------------------------------------------------------
# 3. investigation_members
# -----------------------------------------------------------------------------
class InvestigationMember(Base):
    __tablename__ = "investigation_members"
    __table_args__ = (
        UniqueConstraint("investigation_id", "user_id", name="uq_member_investigation_user"),
        Index("ix_investigation_members_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    member_role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# -----------------------------------------------------------------------------
# 4. evidence
# -----------------------------------------------------------------------------
class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        Index("ix_evidence_investigation_id", "investigation_id"),
        Index("ix_evidence_sha256_hash", "sha256_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False, default="application/octet-stream")
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024))
    # The database column is `metadata`; the attribute is renamed to avoid
    # clashing with SQLAlchemy's MetaData name.
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


# -----------------------------------------------------------------------------
# 5. analysis_results
# -----------------------------------------------------------------------------
class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (
        Index("ix_analysis_results_evidence_id", "evidence_id"),
        Index("ix_analysis_results_module", "module"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )
    module: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    result_data: Mapped[dict | None] = mapped_column(JSONB)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# -----------------------------------------------------------------------------
# 6. evidence_events
# -----------------------------------------------------------------------------
class EvidenceEvent(Base):
    __tablename__ = "evidence_events"
    __table_args__ = (Index("ix_evidence_events_evidence_id", "evidence_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    details: Mapped[str | None] = mapped_column(Text)


# -----------------------------------------------------------------------------
# 7. forensic_timelines
# -----------------------------------------------------------------------------
class ForensicTimeline(Base):
    __tablename__ = "forensic_timelines"
    __table_args__ = (Index("ix_forensic_timelines_investigation_id", "investigation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE")
    )
    module: Mapped[str] = mapped_column(String(32), nullable=False)
    events: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# -----------------------------------------------------------------------------
# 8. chain_of_custody
# -----------------------------------------------------------------------------
class ChainOfCustody(Base):
    """Append-only custody ledger.

    Each row stores the SHA-256 of the previous row, so any alteration of the
    history breaks the hash chain and is detectable.
    """

    __tablename__ = "chain_of_custody"
    __table_args__ = (
        Index("ix_chain_of_custody_evidence_id", "evidence_id"),
        Index("ix_chain_of_custody_event_hash", "event_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    details: Mapped[str | None] = mapped_column(Text)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)


# -----------------------------------------------------------------------------
# 9. generated_reports
# -----------------------------------------------------------------------------
class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    __table_args__ = (Index("ix_generated_reports_investigation_id", "investigation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generating")
    storage_path: Mapped[str | None] = mapped_column(String(1024))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256_hash: Mapped[str | None] = mapped_column(String(64))
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


# -----------------------------------------------------------------------------
# 10. audit_logs  (write-once)
# -----------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_resource", "resource"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    user_name: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict | None] = mapped_column(JSONB)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# -----------------------------------------------------------------------------
# 11. correlation_results
# -----------------------------------------------------------------------------
class CorrelationResult(Base):
    __tablename__ = "correlation_results"
    __table_args__ = (Index("ix_correlation_results_investigation_id", "investigation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL")
    )
    finding_id: Mapped[str | None] = mapped_column(String(128))
    correlation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    result_data: Mapped[dict | None] = mapped_column(JSONB)

-- =============================================================================
-- 010 - Indexes
-- =============================================================================
-- Every column used by an RLS policy or a common query is indexed.
-- =============================================================================

-- profiles
CREATE INDEX IF NOT EXISTS ix_profiles_email ON public.profiles (email);

-- investigations
CREATE INDEX IF NOT EXISTS ix_investigations_owner_id ON public.investigations (owner_id);
CREATE INDEX IF NOT EXISTS ix_investigations_status    ON public.investigations (status);
CREATE INDEX IF NOT EXISTS ix_investigations_priority  ON public.investigations (priority);
CREATE INDEX IF NOT EXISTS ix_investigations_category  ON public.investigations (category);
CREATE INDEX IF NOT EXISTS ix_investigations_created_at ON public.investigations (created_at DESC);

-- investigation_members
CREATE INDEX IF NOT EXISTS ix_investigation_members_user_id         ON public.investigation_members (user_id);
CREATE INDEX IF NOT EXISTS ix_investigation_members_investigation_id ON public.investigation_members (investigation_id);

-- evidence
CREATE INDEX IF NOT EXISTS ix_evidence_investigation_id ON public.evidence (investigation_id);
CREATE INDEX IF NOT EXISTS ix_evidence_sha256_hash     ON public.evidence (sha256_hash);
CREATE INDEX IF NOT EXISTS ix_evidence_status           ON public.evidence (status);
CREATE INDEX IF NOT EXISTS ix_evidence_uploaded_by      ON public.evidence (uploaded_by);
CREATE INDEX IF NOT EXISTS ix_evidence_uploaded_at      ON public.evidence (uploaded_at DESC);

-- analysis_results
CREATE INDEX IF NOT EXISTS ix_analysis_results_evidence_id ON public.analysis_results (evidence_id);
CREATE INDEX IF NOT EXISTS ix_analysis_results_module     ON public.analysis_results (module);
CREATE INDEX IF NOT EXISTS ix_analysis_results_created_at ON public.analysis_results (created_at DESC);

-- evidence_events
CREATE INDEX IF NOT EXISTS ix_evidence_events_evidence_id ON public.evidence_events (evidence_id);
CREATE INDEX IF NOT EXISTS ix_evidence_events_timestamp  ON public.evidence_events (timestamp DESC);

-- forensic_timelines
CREATE INDEX IF NOT EXISTS ix_forensic_timelines_investigation_id ON public.forensic_timelines (investigation_id);
CREATE INDEX IF NOT EXISTS ix_forensic_timelines_evidence_id      ON public.forensic_timelines (evidence_id);

-- chain_of_custody
CREATE INDEX IF NOT EXISTS ix_chain_of_custody_evidence_id ON public.chain_of_custody (evidence_id);
CREATE INDEX IF NOT EXISTS ix_chain_of_custody_timestamp  ON public.chain_of_custody (timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_chain_of_custody_event_hash  ON public.chain_of_custody (event_hash);

-- correlation_results
CREATE INDEX IF NOT EXISTS ix_correlation_results_investigation_id ON public.correlation_results (investigation_id);
CREATE INDEX IF NOT EXISTS ix_correlation_results_created_at     ON public.correlation_results (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_correlation_results_verified       ON public.correlation_results (verified);

-- generated_reports
CREATE INDEX IF NOT EXISTS ix_generated_reports_investigation_id ON public.generated_reports (investigation_id);
CREATE INDEX IF NOT EXISTS ix_generated_reports_generated_at     ON public.generated_reports (generated_at DESC);

-- audit_logs
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id    ON public.audit_logs (user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource   ON public.audit_logs (resource);
CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp  ON public.audit_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action     ON public.audit_logs (action);

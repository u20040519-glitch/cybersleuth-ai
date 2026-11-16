-- =============================================================================
-- 008 - Row Level Security
-- =============================================================================
-- RLS is enabled on every table. The API connects with a restricted,
-- non-superuser role (`cybersleuth_app`) so these policies are genuinely
-- enforced at the database layer, not just documented.
--
-- Identity comes from the GUCs set by `public.set_request_identity()`.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Evidence-scoped helpers
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.can_access_evidence(p_evidence_id uuid)
RETURNS boolean
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public, auth
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.evidence e
        WHERE e.id = p_evidence_id
          AND public.can_access_investigation(e.investigation_id)
    )
$$;

CREATE OR REPLACE FUNCTION public.can_access_investigation_evidence(p_investigation_id uuid)
RETURNS boolean
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public, auth
AS $$
    SELECT public.can_access_investigation(p_investigation_id)
$$;

-- -----------------------------------------------------------------------------
-- Enable RLS everywhere
-- -----------------------------------------------------------------------------
ALTER TABLE public.profiles             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigations       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigation_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_results     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_events      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forensic_timelines   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chain_of_custody     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.correlation_results  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_reports    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs           ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- profiles
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS profiles_select ON public.profiles;
CREATE POLICY profiles_select ON public.profiles
    FOR SELECT USING (id = public.current_user_id() OR public.is_supervisor());

DROP POLICY IF EXISTS profiles_insert ON public.profiles;
CREATE POLICY profiles_insert ON public.profiles
    FOR INSERT WITH CHECK (id = public.current_user_id());

DROP POLICY IF EXISTS profiles_update ON public.profiles;
CREATE POLICY profiles_update ON public.profiles
    FOR UPDATE USING (id = public.current_user_id())
                   WITH CHECK (id = public.current_user_id());

-- -----------------------------------------------------------------------------
-- investigations
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS investigations_select ON public.investigations;
CREATE POLICY investigations_select ON public.investigations
    FOR SELECT USING (public.can_access_investigation(id));

DROP POLICY IF EXISTS investigations_insert ON public.investigations;
CREATE POLICY investigations_insert ON public.investigations
    FOR INSERT WITH CHECK (owner_id = public.current_user_id());

DROP POLICY IF EXISTS investigations_update ON public.investigations;
CREATE POLICY investigations_update ON public.investigations
    FOR UPDATE USING (public.can_manage_investigation(id))
                   WITH CHECK (public.can_manage_investigation(id));

DROP POLICY IF EXISTS investigations_delete ON public.investigations;
CREATE POLICY investigations_delete ON public.investigations
    FOR DELETE USING (public.can_manage_investigation(id));

-- -----------------------------------------------------------------------------
-- investigation_members
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS members_select ON public.investigation_members;
CREATE POLICY members_select ON public.investigation_members
    FOR SELECT USING (public.can_access_investigation(investigation_id));

DROP POLICY IF EXISTS members_insert ON public.investigation_members;
CREATE POLICY members_insert ON public.investigation_members
    FOR INSERT WITH CHECK (public.can_manage_investigation(investigation_id));

DROP POLICY IF EXISTS members_update ON public.investigation_members;
CREATE POLICY members_update ON public.investigation_members
    FOR UPDATE USING (public.can_manage_investigation(investigation_id))
                   WITH CHECK (public.can_manage_investigation(investigation_id));

DROP POLICY IF EXISTS members_delete ON public.investigation_members;
CREATE POLICY members_delete ON public.investigation_members
    FOR DELETE USING (public.can_manage_investigation(investigation_id));

-- -----------------------------------------------------------------------------
-- evidence
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS evidence_select ON public.evidence;
CREATE POLICY evidence_select ON public.evidence
    FOR SELECT USING (public.can_access_investigation(investigation_id));

DROP POLICY IF EXISTS evidence_insert ON public.evidence;
CREATE POLICY evidence_insert ON public.evidence
    FOR INSERT WITH CHECK (public.can_access_investigation(investigation_id)
                          AND uploaded_by = public.current_user_id());

DROP POLICY IF EXISTS evidence_update ON public.evidence;
CREATE POLICY evidence_update ON public.evidence
    FOR UPDATE USING (public.can_access_investigation(investigation_id))
                   WITH CHECK (public.can_access_investigation(investigation_id));

DROP POLICY IF EXISTS evidence_delete ON public.evidence;
CREATE POLICY evidence_delete ON public.evidence
    FOR DELETE USING (public.can_manage_investigation(investigation_id));

-- -----------------------------------------------------------------------------
-- analysis_results
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS analysis_results_select ON public.analysis_results;
CREATE POLICY analysis_results_select ON public.analysis_results
    FOR SELECT USING (public.can_access_evidence(evidence_id));

DROP POLICY IF EXISTS analysis_results_insert ON public.analysis_results;
CREATE POLICY analysis_results_insert ON public.analysis_results
    FOR INSERT WITH CHECK (public.can_access_evidence(evidence_id));

DROP POLICY IF EXISTS analysis_results_update ON public.analysis_results;
CREATE POLICY analysis_results_update ON public.analysis_results
    FOR UPDATE USING (public.can_access_evidence(evidence_id))
                   WITH CHECK (public.can_access_evidence(evidence_id));

DROP POLICY IF EXISTS analysis_results_delete ON public.analysis_results;
CREATE POLICY analysis_results_delete ON public.analysis_results
    FOR DELETE USING (public.can_access_evidence(evidence_id));

-- -----------------------------------------------------------------------------
-- evidence_events
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS evidence_events_select ON public.evidence_events;
CREATE POLICY evidence_events_select ON public.evidence_events
    FOR SELECT USING (public.can_access_evidence(evidence_id));

-- The policy is created as `evidence_insert_events`, so that is the name that
-- has to be dropped. Dropping `evidence_events_insert` removed a policy that
-- never existed and left `evidence_insert_events` in place, so re-running
-- this file failed with "policy ... already exists".
DROP POLICY IF EXISTS evidence_insert_events ON public.evidence_events;
CREATE POLICY evidence_insert_events ON public.evidence_events
    FOR INSERT WITH CHECK (public.can_access_evidence(evidence_id));

DROP POLICY IF EXISTS evidence_events_update ON public.evidence_events;
CREATE POLICY evidence_events_update ON public.evidence_events
    FOR UPDATE USING (public.can_access_evidence(evidence_id))
                   WITH CHECK (public.can_access_evidence(evidence_id));

-- -----------------------------------------------------------------------------
-- forensic_timelines
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS forensic_timelines_select ON public.forensic_timelines;
CREATE POLICY forensic_timelines_select ON public.forensic_timelines
    FOR SELECT USING (public.can_access_investigation(investigation_id));

DROP POLICY IF EXISTS forensic_timelines_insert ON public.forensic_timelines;
CREATE POLICY forensic_timelines_insert ON public.forensic_timelines
    FOR INSERT WITH CHECK (public.can_access_investigation(investigation_id));

DROP POLICY IF EXISTS forensic_timelines_update ON public.forensic_timelines;
CREATE POLICY forensic_timelines_update ON public.forensic_timelines
    FOR UPDATE USING (public.can_access_investigation(investigation_id))
                   WITH CHECK (public.can_access_investigation(investigation_id));

-- -----------------------------------------------------------------------------
-- chain_of_custody
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS chain_of_custody_select ON public.chain_of_custody;
CREATE POLICY chain_of_custody_select ON public.chain_of_custody
    FOR SELECT USING (public.can_access_evidence(evidence_id));

DROP POLICY IF EXISTS chain_of_custody_insert ON public.chain_of_custody;
CREATE POLICY chain_of_custody_insert ON public.chain_of_custody
    FOR INSERT WITH CHECK (public.can_access_evidence(evidence_id));

-- No UPDATE or DELETE policy: the ledger is append-only.

-- -----------------------------------------------------------------------------
-- correlation_results
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS correlation_results_select ON public.correlation_results;
CREATE POLICY correlation_results_select ON public.correlation_results
    FOR SELECT USING (public.can_access_investigation(investigation_id));

DROP POLICY IF EXISTS correlation_results_insert ON public.correlation_results;
CREATE POLICY correlation_results_insert ON public.correlation_results
    FOR INSERT WITH CHECK (public.can_access_investigation(investigation_id));

DROP POLICY IF EXISTS correlation_results_update ON public.correlation_results;
CREATE POLICY correlation_results_update ON public.correlation_results
    FOR UPDATE USING (public.can_access_investigation(investigation_id))
                   WITH CHECK (public.can_access_investigation(investigation_id));

-- -----------------------------------------------------------------------------
-- generated_reports
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS generated_reports_select ON public.generated_reports;
CREATE POLICY generated_reports_select ON public.generated_reports
    FOR SELECT USING (public.can_access_investigation(investigation_id));

DROP POLICY IF EXISTS generated_reports_insert ON public.generated_reports;
CREATE POLICY generated_reports_insert ON public.generated_reports
    FOR INSERT WITH CHECK (public.can_access_investigation(investigation_id)
                          AND generated_by = public.current_user_id());

DROP POLICY IF EXISTS generated_reports_update ON public.generated_reports;
CREATE POLICY generated_reports_update ON public.generated_reports
    FOR UPDATE USING (public.can_access_investigation(investigation_id))
                   WITH CHECK (public.can_access_investigation(investigation_id));

-- -----------------------------------------------------------------------------
-- audit_logs
-- -----------------------------------------------------------------------------
-- Any authenticated user may append an entry (the application records its own
-- actions). Reading is restricted to the author, or to supervisors.
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS audit_logs_select ON public.audit_logs;
CREATE POLICY audit_logs_select ON public.audit_logs
    FOR SELECT USING (user_id = public.current_user_id() OR public.is_supervisor());

DROP POLICY IF EXISTS audit_logs_insert ON public.audit_logs;
CREATE POLICY audit_logs_insert ON public.audit_logs
    FOR INSERT WITH CHECK (public.current_user_id() IS NOT NULL);

-- No UPDATE or DELETE policy: the audit trail is append-only.

-- -----------------------------------------------------------------------------
-- Restricted application role
-- -----------------------------------------------------------------------------
-- The API authenticates as this role so that RLS is enforced. It owns no
-- tables and cannot bypass policies.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cybersleuth_app') THEN
        CREATE ROLE cybersleuth_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO cybersleuth_app;
GRANT USAGE ON SCHEMA auth TO cybersleuth_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cybersleuth_app;
GRANT SELECT, INSERT, UPDATE ON auth.users TO cybersleuth_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO cybersleuth_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cybersleuth_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO cybersleuth_app;

-- The restricted role may not mutate the append-only ledgers directly.
REVOKE UPDATE, DELETE ON public.chain_of_custody FROM cybersleuth_app;
REVOKE UPDATE, DELETE ON public.audit_logs FROM cybersleuth_app;

COMMENT ON ROLE cybersleuth_app IS
    'Application role used by the CyberSleuth AI API. Row Level Security is enforced for this role.';

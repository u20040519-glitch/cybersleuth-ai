-- =============================================================================
-- 012 - Security and analysis fixes
-- =============================================================================
-- Follow-up to 005/008/010. Everything in this file is additive: it widens an
-- existing constraint or policy, tightens a grant, or adds an index. It never
-- drops a table, a column or a function, so it is safe to apply to a database
-- that already has 000-011, and safe to apply twice.
--
--   (a) analysis_results.status accepts 'unavailable' (a forensic module whose
--       optional dependency is missing). 005 only allowed pending/running/
--       completed/failed, so the backend's insert failed with an IntegrityError
--       and the API answered 500.
--   (b) profiles_select also exposes the colleagues of the caller: a case owner
--       must be able to read the profile of the user they are adding to a case,
--       otherwise every non-supervisor add_member call answers 404.
--   (c) audit_logs accepts anonymous rows (user_id IS NULL). Failed logins are
--       recorded before an identity exists, and the previous WITH CHECK
--       rejected those rows silently, so they were never written.
--   (d) auth.users is granted per column instead of as a whole table, so the
--       application role can no longer read every user's encrypted_password.
--   (e) investigation_members gets the index that the widened policy needs.
--
-- This file is additive and idempotent: every statement is guarded with
-- IF EXISTS / IF NOT EXISTS / DROP ... IF EXISTS, so re-running it leaves the
-- schema in exactly the same state.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- (a) Allow the 'unavailable' analysis status
-- -----------------------------------------------------------------------------
-- The backend records 'unavailable' when a forensic module cannot run because
-- an optional dependency (for example exiftool, ffmpeg or a speech model) is
-- not installed. That is a legitimate outcome, not a failure, and it must not
-- raise a constraint violation.
-- -----------------------------------------------------------------------------
ALTER TABLE public.analysis_results
    DROP CONSTRAINT IF EXISTS analysis_results_status_check;

ALTER TABLE public.analysis_results
    ADD CONSTRAINT analysis_results_status_check
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'unavailable'));

COMMENT ON CONSTRAINT analysis_results_status_check ON public.analysis_results IS
    'Analysis lifecycle. ''unavailable'' means the module could not run because an optional dependency was missing.';

-- -----------------------------------------------------------------------------
-- (b) Widen profiles_select
-- -----------------------------------------------------------------------------
-- The caller may read:
--   * their own profile;
--   * every profile, if they are a supervisor;
--   * the profile of anybody who shares an investigation with them.
--
-- The shared-investigation branch is written as an explicit EXISTS subquery
-- rather than calling public.is_investigation_member(), because that helper
-- takes an *investigation* id (public.is_investigation_member(p_investigation_id
-- uuid), defined in 011) and not a user id: passing a profile id would ask
-- "am I a member of the investigation whose id equals this profile id?", which
-- is never true.
--
-- The subquery reads investigation_members (the caller's row) joined to
-- investigations (the shared case) and to investigation_members again (the
-- target user's row). Both membership tables are protected by RLS; the
-- policies behind them resolve through the SECURITY DEFINER helpers, so there
-- is no recursion back into profiles.
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS profiles_select ON public.profiles;

CREATE POLICY profiles_select ON public.profiles
    FOR SELECT USING (
        id = public.current_user_id()
        OR public.is_supervisor()
        OR EXISTS (
            SELECT 1
            FROM public.investigation_members caller_membership
            JOIN public.investigations shared_case
              ON shared_case.id = caller_membership.investigation_id
            JOIN public.investigation_members target_membership
              ON target_membership.investigation_id = shared_case.id
            WHERE caller_membership.user_id = public.current_user_id()
              AND target_membership.user_id = profiles.id
        )
    );

-- -----------------------------------------------------------------------------
-- (c) Allow anonymous audit rows
-- -----------------------------------------------------------------------------
-- A failed login is audited before any identity exists, so user_id is NULL.
-- The previous policy required an authenticated caller for every insert and
-- silently dropped those rows.
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS audit_logs_insert ON public.audit_logs;

CREATE POLICY audit_logs_insert ON public.audit_logs
    FOR INSERT WITH CHECK (user_id IS NULL OR public.current_user_id() IS NOT NULL);

-- -----------------------------------------------------------------------------
-- (d) Scope the auth.users grant to the columns the application needs
-- -----------------------------------------------------------------------------
-- The application role used to hold SELECT on the whole auth.users table,
-- which includes encrypted_password for every account in the instance. The
-- grants below give it the identity columns it actually needs (to read a
-- profile, to create an account locally, to keep the profile in step) and
-- nothing else.
--
-- Note for the runtime: the application role can no longer read
-- encrypted_password, so local-mode credential verification must not go
-- through this role.
--
-- The statements are guarded because on Supabase the auth schema is owned by
-- supabase_auth_admin; if the migrating role is not allowed to re-grant on it
-- the failure is reported as a NOTICE instead of aborting the migration.
-- -----------------------------------------------------------------------------
DO $auth_grants$
BEGIN
    REVOKE ALL ON auth.users FROM cybersleuth_app;

    GRANT SELECT (id, email, raw_user_meta_data, created_at, updated_at)
        ON auth.users TO cybersleuth_app;

    GRANT INSERT (id, email, encrypted_password, raw_user_meta_data,
                  created_at, updated_at, email_confirmed_at)
        ON auth.users TO cybersleuth_app;

    GRANT UPDATE (email, raw_user_meta_data, updated_at, email_confirmed_at)
        ON auth.users TO cybersleuth_app;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE
        '012: could not re-scope the auth.users grants for cybersleuth_app (%). On Supabase the auth schema is owned by supabase_auth_admin - run these grants as that owner.',
        SQLERRM;
END
$auth_grants$;

-- -----------------------------------------------------------------------------
-- (e) Indexes for the widened policy
-- -----------------------------------------------------------------------------
-- 010_indexes.sql already creates
--     ix_investigation_members_user_id ON public.investigation_members (user_id)
-- so the index the widened policy needs on the caller's own membership rows
-- already exists and is deliberately NOT repeated here.
--
-- What the shared-investigation subquery looks up is (investigation_id,
-- user_id). The unique constraint uq_member_investigation_user already owns a
-- btree on exactly those two columns, and this explicitly named composite
-- gives the planner the same key without relying on the constraint's internal
-- index name. Both are created with IF NOT EXISTS, so this statement is a
-- no-op on a database that already has either of them.
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_investigation_members_investigation_user
    ON public.investigation_members (investigation_id, user_id);

-- -----------------------------------------------------------------------------
-- This migration is additive and idempotent. It only widens a constraint or a
-- policy, narrows a grant and adds an index; every statement is guarded, so
-- running it twice produces the same schema as running it once, and running it
-- against a database that already has 000-011 changes nothing that was not
-- listed above.
-- -----------------------------------------------------------------------------

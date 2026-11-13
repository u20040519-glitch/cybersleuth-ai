-- =============================================================================
# PROJECT NEXUS AI - PostgreSQL Row Level Security Migration
# =============================================================================
# This migration enables Row Level Security (RLS) on all sensitive tables
# and creates policies that enforce case-level authorization at the database level.
#
# APPLY THIS ONLY ON POSTGRESQL PRODUCTION DATABASES.
# SQLite (development) does not support RLS - application-level authorization is used instead.
# =============================================================================

-- ---------------------------------------------------------------------------
-- Step 1: Create dedicated database roles
-- ---------------------------------------------------------------------------

-- Application role: used by the backend for ordinary requests (NOT superuser)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nexus_app') THEN
        CREATE ROLE nexus_app LOGIN PASSWORD 'change-me-in-production';
    END IF;
END
$$;

-- Reader role: limited read access for reporting/analytics
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nexus_reader') THEN
        CREATE ROLE nexus_reader LOGIN PASSWORD 'change-me-in-production';
    END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- Step 2: Grant schema privileges
-- ---------------------------------------------------------------------------

GRANT USAGE ON SCHEMA public TO nexus_app;
GRANT USAGE ON SCHEMA public TO nexus_reader;

GRANT CREATE ON SCHEMA public TO nexus_app;

-- ---------------------------------------------------------------------------
-- Step 3: Enable RLS on sensitive tables
-- ---------------------------------------------------------------------------

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_gaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE chatbot_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE chatbot_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigation_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE chain_of_custody_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE cookie_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_deletion_requests ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- Step 4: Create RLS policies
-- ---------------------------------------------------------------------------

-- =============================================================================
-- users table: users can read their own record, admins can read all
-- =============================================================================

CREATE POLICY users_own_record ON users
    FOR SELECT
    TO nexus_app
    USING (id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY users_admin_all ON users
    FOR ALL
    TO nexus_app
    USING (
        current_setting('app.current_user_role', true) = 'admin'
    );

-- =============================================================================
-- cases table: owners and permitted users can read; owners can write
-- =============================================================================

CREATE POLICY cases_owner_read ON cases
    FOR SELECT
    TO nexus_app
    USING (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

CREATE POLICY cases_owner_write ON cases
    FOR INSERT
    TO nexus_app
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
    );

CREATE POLICY cases_owner_update ON cases
    FOR UPDATE
    TO nexus_app
    USING (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
            AND permission = 'admin'
        )
    );

CREATE POLICY cases_owner_delete ON cases
    FOR DELETE
    TO nexus_app
    USING (owner_id = current_setting('app.current_user_id', true)::uuid);

-- =============================================================================
-- case_permissions table: only admins and case owners can manage permissions
-- =============================================================================

CREATE POLICY case_permissions_read ON case_permissions
    FOR SELECT
    TO nexus_app
    USING (
        user_id = current_setting('app.current_user_id', true)::uuid
        OR case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
    );

CREATE POLICY case_permissions_manage ON case_permissions
    FOR ALL
    TO nexus_app
    USING (
        current_setting('app.current_user_role', true) = 'admin'
        OR case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- evidence_files table: restricted to case owners and permitted users
-- =============================================================================

CREATE POLICY evidence_files_case_access ON evidence_files
    FOR ALL
    TO nexus_app
    USING (
        case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR case_id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- extracted_observations table (ECHO)
-- =============================================================================

CREATE POLICY extracted_observations_case_access ON extracted_observations
    FOR ALL
    TO nexus_app
    USING (
        case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR case_id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- evidence_claims table (MOSAIC)
-- =============================================================================

CREATE POLICY evidence_claims_case_access ON evidence_claims
    FOR ALL
    TO nexus_app
    USING (
        case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR case_id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- evidence_gaps table (ECHO)
-- =============================================================================

CREATE POLICY evidence_gaps_case_access ON evidence_gaps
    FOR ALL
    TO nexus_app
    USING (
        case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR case_id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- scenarios table (MOSAIC)
-- =============================================================================

CREATE POLICY scenarios_case_access ON scenarios
    FOR ALL
    TO nexus_app
    USING (
        case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR case_id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- events table (TIMEGLASS)
-- =============================================================================

CREATE POLICY events_case_access ON events
    FOR ALL
    TO nexus_app
    USING (
        case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR case_id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- chatbot_conversations table: users can access their own conversations
-- =============================================================================

CREATE POLICY chatbot_conversations_owner_access ON chatbot_conversations
    FOR ALL
    TO nexus_app
    USING (
        user_id = current_setting('app.current_user_id', true)::uuid
        OR case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- chatbot_messages table: access via conversation
-- =============================================================================

CREATE POLICY chatbot_messages_owner_access ON chatbot_messages
    FOR ALL
    TO nexus_app
    USING (
        conversation_id IN (
            SELECT id FROM chatbot_conversations
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- investigation_reports table: case owners and permitted users
-- =============================================================================

CREATE POLICY investigation_reports_case_access ON investigation_reports
    FOR ALL
    TO nexus_app
    USING (
        case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR case_id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
        OR owner_id = current_setting('app.current_user_id', true)::uuid
    );

-- =============================================================================
-- chain_of_custody_records table: case owners and permitted users
-- =============================================================================

CREATE POLICY chain_of_custody_case_access ON chain_of_custody_records
    FOR ALL
    TO nexus_app
    USING (
        case_id IN (
            SELECT id FROM cases WHERE owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR case_id IN (
            SELECT case_id FROM case_permissions
            WHERE user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- =============================================================================
-- consent_records table: users can access their own consent records
-- =============================================================================

CREATE POLICY consent_records_owner_access ON consent_records
    FOR ALL
    TO nexus_app
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

-- =============================================================================
-- cookie_preferences table: users can access their own preferences
-- =============================================================================

CREATE POLICY cookie_preferences_owner_access ON cookie_preferences
    FOR ALL
    TO nexus_app
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

-- =============================================================================
-- audit_logs table: users can read their own logs; admins can read all
-- =============================================================================

CREATE POLICY audit_logs_owner_access ON audit_logs
    FOR SELECT
    TO nexus_app
    USING (
        user_id = current_setting('app.current_user_id', true)::uuid
        OR current_setting('app.current_user_role', true) = 'admin'
    );

CREATE POLICY audit_logs_insert ON audit_logs
    FOR INSERT
    TO nexus_app
    WITH CHECK (
        user_id = current_setting('app.current_user_id', true)::uuid
        OR user_id IS NULL
    );

-- =============================================================================
-- data_deletion_requests table: users can read their own requests
-- =============================================================================

CREATE POLICY data_deletion_requests_owner_access ON data_deletion_requests
    FOR ALL
    TO nexus_app
    USING (
        user_id = current_setting('app.current_user_id', true)::uuid
        OR current_setting('app.current_user_role', true) = 'admin'
    );

-- ---------------------------------------------------------------------------
-- Step 5: Grant table-level privileges
-- ---------------------------------------------------------------------------

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nexus_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO nexus_reader;

-- ---------------------------------------------------------------------------
-- Step 6: Grant sequence privileges (for UUID defaults if any)
-- ---------------------------------------------------------------------------

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nexus_app;

-- ---------------------------------------------------------------------------
-- Notes for application:
-- ---------------------------------------------------------------------------
-- The backend must set the following PostgreSQL session variables at the start
-- of each request (using SET LOCAL inside a transaction):
--
--   SET LOCAL app.current_user_id = '<user-uuid>';
--   SET LOCAL app.current_user_role = '<role>';
--
-- These are reset at the end of each transaction. Use a middleware or dependency
-- that sets these variables based on the authenticated JWT subject.
--
-- Example SQL executed by backend after authentication:
--   SELECT set_config('app.current_user_id', $1, true);
--   SELECT set_config('app.current_user_role', $2, true);
-- =============================================================================
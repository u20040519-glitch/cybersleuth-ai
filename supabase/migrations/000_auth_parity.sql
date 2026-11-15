-- =============================================================================
-- 000 - Auth schema parity
-- =============================================================================
-- On Supabase the `auth` schema and `auth.users` table are owned by GoTrue and
-- are managed by the platform. On a standalone PostgreSQL instance they do not
-- exist, so this migration creates a compatible subset.
--
-- Everything below is guarded, so the file is safe to run against Supabase.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS auth;

DO $parity$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) THEN
        CREATE TABLE auth.users (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email               text NOT NULL UNIQUE,
            encrypted_password  text NOT NULL DEFAULT '',
            email_confirmed_at  timestamptz,
            raw_user_meta_data  jsonb NOT NULL DEFAULT '{}'::jsonb,
            is_active           boolean NOT NULL DEFAULT true,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now()
        );
        COMMENT ON TABLE auth.users IS
            'Local parity shim for Supabase Auth (GoTrue). On Supabase this table is platform-managed.';
    END IF;
END
$parity$;

-- Identity helpers. Supabase ships these already; locally we provide the same
-- call signature so that every RLS policy can be written once and run in both
-- environments.
DO $helpers$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'auth' AND p.proname = 'uid'
    ) THEN
        CREATE FUNCTION auth.uid() RETURNS uuid
            LANGUAGE sql STABLE
            AS $fn$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $fn$;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'auth' AND p.proname = 'role'
    ) THEN
        CREATE FUNCTION auth.role() RETURNS text
            LANGUAGE sql STABLE
            AS $fn$ SELECT nullif(current_setting('app.user_role', true), '') $fn$;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'auth' AND p.proname = 'email'
    ) THEN
        CREATE FUNCTION auth.email() RETURNS text
            LANGUAGE sql STABLE
            AS $fn$ SELECT nullif(current_setting('app.user_email', true), '') $fn$;
    END IF;
END
$helpers$;

GRANT USAGE ON SCHEMA auth TO PUBLIC;

-- =============================================================================
-- 001 - Extensions and helper functions
-- =============================================================================

-- These helpers are created before the tables they reference (profiles is
-- created in 002, investigations in 003). PostgreSQL validates SQL function
-- bodies at creation time unless told otherwise.
SET check_function_bodies = off;

-- Extensions are best-effort: managed Postgres (Supabase) ships them, but the
-- embedded portable PostgreSQL used for local development does not bundle
-- pgcrypto/uuid-ossp. Every migration only relies on gen_random_uuid(), which
-- is built into PostgreSQL 13+, so missing extensions are not fatal.
DO $ext$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pgcrypto') THEN
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'uuid-ossp') THEN
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    END IF;
END
$ext$;

-- -----------------------------------------------------------------------------
-- Request identity
-- -----------------------------------------------------------------------------
-- The API sets these three GUCs once per transaction, before any query runs.
-- `SET LOCAL` semantics mean the values cannot leak between pooled
-- connections, and every RLS policy reads the identity from here.
--
-- Supabase populates the same identity through `request.jwt.claims`; the
-- helper below understands both, so identical policies work in both places.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.request_claims()
RETURNS jsonb
LANGUAGE sql STABLE
AS $$
    SELECT coalesce(
        nullif(current_setting('request.jwt.claims', true), '')::jsonb,
        '{}'::jsonb
    )
$$;

CREATE OR REPLACE FUNCTION public.set_request_identity(
    p_user_id   uuid,
    p_user_role text,
    p_user_email text
)
RETURNS void
LANGUAGE sql
AS $$
    SELECT set_config('app.user_id',     coalesce(p_user_id::text, ''),   true),
           set_config('app.user_role',   coalesce(p_user_role, ''),         true),
           set_config('app.user_email',  coalesce(p_user_email, ''),        true)
$$;

CREATE OR REPLACE FUNCTION public.current_user_id()
RETURNS uuid
LANGUAGE sql STABLE
AS $$
    SELECT coalesce(
        auth.uid(),
        nullif(public.request_claims() ->> 'sub', '')::uuid
    )
$$;

CREATE OR REPLACE FUNCTION public.current_user_role()
RETURNS text
LANGUAGE sql STABLE
AS $$
    SELECT coalesce(
        auth.role(),
        public.request_claims() ->> 'role'
    )
$$;

CREATE OR REPLACE FUNCTION public.is_supervisor()
RETURNS boolean
LANGUAGE sql STABLE
AS $$
    SELECT coalesce(public.current_user_role() = 'supervisor', false)
$$;

-- -----------------------------------------------------------------------------
-- Investigation access
-- -----------------------------------------------------------------------------
-- SECURITY DEFINER so that the check can read `investigations` and
-- `investigation_members` without re-entering the RLS policies that call it
-- (which would otherwise recurse).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.can_access_investigation(p_investigation_id uuid)
RETURNS boolean
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public, auth
AS $$
    SELECT
        public.current_user_id() IS NOT NULL
        AND (
            EXISTS (
                SELECT 1 FROM public.investigations i
                WHERE i.id = p_investigation_id
                  AND i.owner_id = public.current_user_id()
            )
            OR EXISTS (
                SELECT 1 FROM public.investigation_members m
                WHERE m.investigation_id = p_investigation_id
                  AND m.user_id = public.current_user_id()
            )
        )
$$;

CREATE OR REPLACE FUNCTION public.can_manage_investigation(p_investigation_id uuid)
RETURNS boolean
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public, auth
AS $$
    SELECT
        public.current_user_id() IS NOT NULL
        AND (
            public.is_supervisor()
            OR EXISTS (
                SELECT 1 FROM public.investigations i
                WHERE i.id = p_investigation_id
                  AND i.owner_id = public.current_user_id()
            )
        )
$$;

COMMENT ON FUNCTION public.can_access_investigation(uuid) IS
    'Returns true when the caller is the investigation owner or a listed member.';
COMMENT ON FUNCTION public.can_manage_investigation(uuid) IS
    'Returns true for supervisors and for the investigation owner.';

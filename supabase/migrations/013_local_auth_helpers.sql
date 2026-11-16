-- =============================================================================
-- 013 - Local authentication helpers
--
-- Follow-up to 012. Migration 012 re-scoped the grants on `auth.users` so that
-- the application role can no longer read `encrypted_password` (or any other
-- column it does not need) for every account in the instance. That is the
-- right hardening, but it also removed the only path the LOCAL (non-Supabase)
-- authentication provider had: the backend verifies Argon2 hashes itself, so
-- it has to read the hash of the account that is signing in.
--
-- The two helper functions below close that gap without giving the grant back:
--
--   public.local_auth_credentials(email)
--       SECURITY DEFINER. Returns the single credential row for one address.
--       The application role gets EXECUTE, not SELECT: it can no longer list
--       or bulk-read the table, only look up the account that is signing in.
--
--   public.local_auth_create_user(id, email, password, metadata)
--       SECURITY DEFINER. Creates the identity row. The application role has
--       no INSERT privilege on the table itself, so the row can only be
--       created through this function.
--
-- On Supabase neither function is needed: GoTrue owns the identities and the
-- backend authenticates through the Auth API, and `auth.users` is owned by
-- `supabase_auth_admin`, so the creating role is not allowed to define
-- functions over it. The whole block is therefore guarded - if the functions
-- cannot be created, the failure is reported as a NOTICE and the backend
-- keeps using the table-level grants from migration 008.
-- =============================================================================

DO $helpers$
BEGIN
    CREATE OR REPLACE FUNCTION public.local_auth_credentials(p_email text)
    RETURNS TABLE (
        id                 uuid,
        email              text,
        encrypted_password text,
        raw_user_meta_data jsonb,
        is_active          boolean
    )
    LANGUAGE sql
    SECURITY DEFINER
    SET search_path = public, auth
    AS $fn$
        SELECT u.id,
               u.email,
               u.encrypted_password,
               u.raw_user_meta_data,
               u.is_active
        FROM auth.users u
        WHERE lower(u.email) = lower(p_email)
        LIMIT 1;
    $fn$;

    CREATE OR REPLACE FUNCTION public.local_auth_create_user(
        p_id       uuid,
        p_email    text,
        p_password text,
        p_metadata jsonb
    )
    RETURNS uuid
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public, auth
    AS $fn$
    DECLARE
        v_id uuid;
    BEGIN
        INSERT INTO auth.users (
            id,
            email,
            encrypted_password,
            email_confirmed_at,
            raw_user_meta_data,
            is_active
        )
        VALUES (
            p_id,
            lower(p_email),
            p_password,
            now(),
            coalesce(p_metadata, '{}'::jsonb),
            true
        )
        RETURNING id INTO v_id;

        RETURN v_id;
    END;
    $fn$;

    -- The functions are for the application role only: PUBLIC gets nothing.
    REVOKE ALL ON FUNCTION public.local_auth_credentials(text) FROM PUBLIC;
    REVOKE ALL ON FUNCTION public.local_auth_create_user(uuid, text, text, jsonb) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION public.local_auth_credentials(text) TO cybersleuth_app;
    GRANT EXECUTE ON FUNCTION public.local_auth_create_user(uuid, text, text, jsonb) TO cybersleuth_app;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE
        '013: could not create the local authentication helpers (%). On Supabase the auth schema is owned by supabase_auth_admin - the backend uses the Auth API there instead.',
        SQLERRM;
END
$helpers$;

COMMENT ON FUNCTION public.local_auth_credentials(text) IS
    'SECURITY DEFINER helper: returns the credential row of a single account so the backend can verify a password without holding SELECT on auth.users.';

COMMENT ON FUNCTION public.local_auth_create_user(uuid, text, text, jsonb) IS
    'SECURITY DEFINER helper: creates a local identity row (the application role has no INSERT privilege on auth.users).';

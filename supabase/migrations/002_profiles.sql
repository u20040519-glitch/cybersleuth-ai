-- =============================================================================
-- 002 - profiles
-- =============================================================================
-- One row per authenticated user, created automatically on sign-up by the
-- `handle_new_user` trigger so that identities can never exist without a
-- profile.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.profiles (
    id            uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    email         text NOT NULL,
    full_name     text NOT NULL,
    role          text NOT NULL DEFAULT 'investigator'
                  CHECK (role IN ('investigator', 'supervisor')),
    avatar_url    text,
    organization  text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.profiles IS
    'Public profile for each authenticated identity. Mirrors auth.users with application metadata.';

-- -----------------------------------------------------------------------------
-- handle_new_user trigger
-- -----------------------------------------------------------------------------
-- Fires on INSERT into auth.users on both Supabase (GoTrue) and the local
-- parity table. It derives the role from the signup metadata so a supervisor
-- can be provisioned at registration time.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
    v_full_name text;
    v_role      text;
BEGIN
    v_full_name := coalesce(
        NEW.raw_user_meta_data ->> 'full_name',
        NEW.raw_user_meta_data ->> 'name',
        split_part(NEW.email, '@', 1)
    );

    v_role := CASE
        WHEN NEW.raw_user_meta_data ->> 'role' = 'supervisor' THEN 'supervisor'
        ELSE 'investigator'
    END;

    INSERT INTO public.profiles (id, email, full_name, role, avatar_url, organization)
    VALUES (
        NEW.id,
        NEW.email,
        v_full_name,
        v_role,
        NEW.raw_user_meta_data ->> 'avatar_url',
        NEW.raw_user_meta_data ->> 'organization'
    )
    ON CONFLICT (id) DO UPDATE
        SET email      = EXCLUDED.email,
            full_name  = EXCLUDED.full_name,
            updated_at = now();

    RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Keep the profile in step with a role change.
CREATE OR REPLACE FUNCTION public.handle_user_update()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
BEGIN
    UPDATE public.profiles
    SET email      = NEW.email,
        full_name  = coalesce(NEW.raw_user_meta_data ->> 'full_name',
                               NEW.raw_user_meta_data ->> 'name',
                               split_part(NEW.email, '@', 1)),
        role       = CASE WHEN NEW.raw_user_meta_data ->> 'role' = 'supervisor'
                          THEN 'supervisor' ELSE role END,
        updated_at = now()
    WHERE id = NEW.id;
    RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS on_auth_user_updated ON auth.users;
CREATE TRIGGER on_auth_user_updated
    AFTER UPDATE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_user_update();

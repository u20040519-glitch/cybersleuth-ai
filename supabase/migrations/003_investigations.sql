-- =============================================================================
-- 003 - investigations and investigation_members
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.investigations (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     text NOT NULL UNIQUE,
    title       text NOT NULL,
    description text,
    category    text NOT NULL DEFAULT 'general',
    priority    text NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status      text NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'active', 'review', 'closed', 'archived')),
    owner_id    uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,
    notes       text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.investigations IS
    'A forensic investigation case. Access is restricted to the owner and listed members.';

CREATE TABLE IF NOT EXISTS public.investigation_members (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id uuid NOT NULL REFERENCES public.investigations (id) ON DELETE CASCADE,
    user_id         uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,
    member_role     text NOT NULL DEFAULT 'member'
                    CHECK (member_role IN ('member', 'reviewer', 'lead')),
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_member_investigation_user UNIQUE (investigation_id, user_id)
);

COMMENT ON TABLE public.investigation_members IS
    'Explicit per-investigation access grants, in addition to the owner.';

-- The owner is always a member, so membership checks never depend on two
-- different tables agreeing with each other.
CREATE OR REPLACE FUNCTION public.add_investigation_owner_as_member()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.investigation_members (investigation_id, user_id, member_role)
    VALUES (NEW.id, NEW.owner_id, 'lead')
    ON CONFLICT (investigation_id, user_id) DO NOTHING;
    RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS on_investigation_created ON public.investigations;
CREATE TRIGGER on_investigation_created
    AFTER INSERT ON public.investigations
    FOR EACH ROW EXECUTE FUNCTION public.add_investigation_owner_as_member();

-- Keep `updated_at` honest without relying on every client to set it.
CREATE OR REPLACE FUNCTION public.touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS on_investigations_updated_at ON public.investigations;
CREATE TRIGGER on_investigations_updated_at
    BEFORE UPDATE ON public.investigations
    FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();

DROP TRIGGER IF EXISTS on_profiles_updated_at ON public.profiles;
CREATE TRIGGER on_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();

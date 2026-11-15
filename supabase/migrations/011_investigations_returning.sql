-- =============================================================================
-- 011 - Insert/RETURNING-friendly SELECT policy for investigations
-- =============================================================================
-- PostgreSQL applies the SELECT row-level policy to rows returned by
-- INSERT ... RETURNING (as a WITH CHECK option). That check ran before the
-- freshly inserted investigation row was visible to the policy's EXISTS
-- sub-select (the command snapshot predates the insert), so
--   INSERT INTO investigations ... RETURNING ...
-- was rejected even though the caller was the owner. The INSERT's own
-- WITH CHECK passed, but the SELECT policy's self-referencing EXISTS did not.
--
-- Fix: let the owner branch compare against a direct column of the row
-- (`owner_id = current_user_id()`), which needs no table read, and move the
-- membership sub-select into a dedicated helper shared with the access check.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.is_investigation_member(p_investigation_id uuid)
RETURNS boolean
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public, auth
AS $$
    SELECT public.current_user_id() IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM public.investigation_members m
           WHERE m.investigation_id = p_investigation_id
             AND m.user_id = public.current_user_id()
       )
$$;

COMMENT ON FUNCTION public.is_investigation_member(uuid) IS
    'True when the caller is a listed member of the investigation.';

-- Rewrite the shared access helper on top of the membership helper so the
-- owner lookup is the only table read performed here.
CREATE OR REPLACE FUNCTION public.can_access_investigation(p_investigation_id uuid)
RETURNS boolean
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public, auth
AS $$
    SELECT public.current_user_id() IS NOT NULL
       AND (
           EXISTS (
               SELECT 1
               FROM public.investigations i
               WHERE i.id = p_investigation_id
                 AND i.owner_id = public.current_user_id()
           )
           OR public.is_investigation_member(p_investigation_id)
       )
$$;

-- Owner branch is a direct column comparison, so INSERT ... RETURNING works.
DROP POLICY IF EXISTS investigations_select ON public.investigations;
CREATE POLICY investigations_select ON public.investigations
    FOR SELECT USING (
        owner_id = public.current_user_id()
        OR public.is_investigation_member(id)
    );

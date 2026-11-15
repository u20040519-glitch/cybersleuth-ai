-- =============================================================================
-- 007 - audit_logs (write-once)
-- =============================================================================
-- The audit trail records who did what. It may be appended to but never
-- edited or removed: the same immutability guarantee as the custody ledger.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.audit_logs (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid REFERENCES public.profiles (id) ON DELETE SET NULL,
    user_name   text NOT NULL DEFAULT 'system',
    action      text NOT NULL,
    resource    text NOT NULL,
    resource_id text,
    ip_address  text,
    details     jsonb,
    timestamp   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.audit_logs IS
    'Append-only audit trail. Every privileged action is recorded with actor, resource and timestamp.';

CREATE OR REPLACE FUNCTION public.prevent_audit_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only; % is not permitted', TG_OP
        USING ERRCODE = '42501';
END
$$;

DROP TRIGGER IF EXISTS audit_logs_no_update ON public.audit_logs;
CREATE TRIGGER audit_logs_no_update
    BEFORE UPDATE OR DELETE ON public.audit_logs
    FOR EACH ROW EXECUTE FUNCTION public.prevent_audit_mutation();

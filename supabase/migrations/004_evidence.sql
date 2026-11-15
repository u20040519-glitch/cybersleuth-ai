-- =============================================================================
-- 004 - evidence, evidence_events and chain_of_custody
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.evidence (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id   uuid NOT NULL REFERENCES public.investigations (id) ON DELETE CASCADE,
    original_filename  text NOT NULL,
    file_size          bigint NOT NULL DEFAULT 0,
    mime_type          text NOT NULL DEFAULT 'application/octet-stream',
    sha256_hash        text NOT NULL,
    storage_path       text NOT NULL,
    status             text NOT NULL DEFAULT 'uploaded'
                       CHECK (status IN ('uploaded', 'processing', 'analyzed', 'error')),
    uploaded_by        uuid NOT NULL REFERENCES public.profiles (id) ON DELETE RESTRICT,
    uploaded_at        timestamptz NOT NULL DEFAULT now(),
    processed_at       timestamptz,
    thumbnail_path     text,
    metadata           jsonb NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE public.evidence IS
    'Original evidence files. storage_path points at an immutable object; the sha256_hash is the integrity anchor.';
COMMENT ON COLUMN public.evidence.metadata IS
    'Original file metadata extracted at upload time (EXIF, mime, size, upload source).';

CREATE TABLE IF NOT EXISTS public.evidence_events (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id uuid NOT NULL REFERENCES public.evidence (id) ON DELETE CASCADE,
    event_type  text NOT NULL
                CHECK (event_type IN ('upload', 'access', 'process', 'export', 'share')),
    actor_id    uuid REFERENCES public.profiles (id) ON DELETE SET NULL,
    actor_name  text NOT NULL DEFAULT 'system',
    timestamp   timestamptz NOT NULL DEFAULT now(),
    details     text
);

COMMENT ON TABLE public.evidence_events IS
    'Chronological log of every action taken against an evidence item.';

-- -----------------------------------------------------------------------------
-- chain_of_custody
-- -----------------------------------------------------------------------------
-- Append-only. Each row hashes the previous row so that any tampering with
-- the history invalidates every subsequent link.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.chain_of_custody (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id   uuid NOT NULL REFERENCES public.evidence (id) ON DELETE CASCADE,
    event_type    text NOT NULL
                  CHECK (event_type IN ('upload', 'access', 'process', 'export', 'share')),
    actor_id      uuid REFERENCES public.profiles (id) ON DELETE SET NULL,
    actor_name    text NOT NULL DEFAULT 'system',
    timestamp     timestamptz NOT NULL DEFAULT now(),
    details       text,
    previous_hash text NOT NULL DEFAULT '',
    event_hash    text NOT NULL
);

COMMENT ON TABLE public.chain_of_custody IS
    'Tamper-evident custody ledger. event_hash = sha256(previous_hash || canonical row payload).';

CREATE OR REPLACE FUNCTION public.prevent_custody_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'chain_of_custody is append-only; % is not permitted', TG_OP
        USING ERRCODE = '42501';
END
$$;

DROP TRIGGER IF EXISTS chain_of_custody_no_update ON public.chain_of_custody;
CREATE TRIGGER chain_of_custody_no_update
    BEFORE UPDATE OR DELETE ON public.chain_of_custody
    FOR EACH ROW EXECUTE FUNCTION public.prevent_custody_mutation();

-- -----------------------------------------------------------------------------
-- Immutability of the original
-- -----------------------------------------------------------------------------
-- The storage path and the hash of an evidence item are fixed at upload time.
-- Repointing an original at a different object would break the chain of
-- custody, so the database refuses it.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.protect_evidence_original()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.sha256_hash IS DISTINCT FROM OLD.sha256_hash
       OR NEW.storage_path IS DISTINCT FROM OLD.storage_path
       OR NEW.original_filename IS DISTINCT FROM OLD.original_filename
       OR NEW.file_size IS DISTINCT FROM OLD.file_size THEN
        RAISE EXCEPTION
            'evidence originals are immutable: sha256_hash, storage_path, original_filename and file_size cannot change'
            USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS evidence_protect_original ON public.evidence;
CREATE TRIGGER evidence_protect_original
    BEFORE UPDATE ON public.evidence
    FOR EACH ROW EXECUTE FUNCTION public.protect_evidence_original();

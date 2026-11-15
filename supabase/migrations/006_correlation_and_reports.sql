-- =============================================================================
-- 006 - correlation_results and generated_reports
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.correlation_results (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id   uuid NOT NULL REFERENCES public.investigations (id) ON DELETE CASCADE,
    source_evidence_id uuid REFERENCES public.evidence (id) ON DELETE SET NULL,
    finding_id         text,
    correlation_type   text NOT NULL,
    description        text NOT NULL,
    confidence         double precision,
    timestamp          timestamptz,
    verified           boolean NOT NULL DEFAULT false,
    created_at         timestamptz NOT NULL DEFAULT now(),
    result_data        jsonb
);

COMMENT ON TABLE public.correlation_results IS
    'A single correlation finding: a link between two or more evidence items, with an optional AI explanation.';

CREATE TABLE IF NOT EXISTS public.generated_reports (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id uuid NOT NULL REFERENCES public.investigations (id) ON DELETE CASCADE,
    title            text NOT NULL,
    status           text NOT NULL DEFAULT 'generating'
                     CHECK (status IN ('generating', 'ready', 'failed')),
    storage_path     text,
    file_size        bigint NOT NULL DEFAULT 0,
    sha256_hash      text,
    generated_by     uuid NOT NULL REFERENCES public.profiles (id) ON DELETE RESTRICT,
    generated_at     timestamptz NOT NULL DEFAULT now(),
    metadata         jsonb NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE public.generated_reports IS
    'Rendered PDF reports. The rendered artefact is stored immutably alongside its hash.';

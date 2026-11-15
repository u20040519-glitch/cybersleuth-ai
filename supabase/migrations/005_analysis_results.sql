-- =============================================================================
-- 005 - analysis_results and forensic_timelines
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.analysis_results (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id      uuid NOT NULL REFERENCES public.evidence (id) ON DELETE CASCADE,
    module           text NOT NULL
                     CHECK (module IN ('deeptrace', 'spytrace', 'voiceproof', 'cybersleuth')),
    status           text NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    result_data      jsonb,
    confidence_score double precision,
    created_at       timestamptz NOT NULL DEFAULT now(),
    completed_at     timestamptz
);

COMMENT ON TABLE public.analysis_results IS
    'Structured output of one forensic module run against one evidence item.';

CREATE TABLE IF NOT EXISTS public.forensic_timelines (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id uuid NOT NULL REFERENCES public.investigations (id) ON DELETE CASCADE,
    evidence_id      uuid REFERENCES public.evidence (id) ON DELETE CASCADE,
    module           text NOT NULL
                     CHECK (module IN ('deeptrace', 'spytrace', 'voiceproof', 'cybersleuth')),
    events           jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.forensic_timelines IS
    'Timestamped event stream extracted by a forensic module, used by the correlation engine.';

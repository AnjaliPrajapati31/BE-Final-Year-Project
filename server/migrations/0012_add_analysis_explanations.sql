ALTER TABLE analysis_result_payloads DROP CONSTRAINT IF EXISTS analysis_result_payloads_result_type_check;
ALTER TABLE analysis_result_payloads ADD CONSTRAINT analysis_result_payloads_result_type_check CHECK (
    result_type IN (
        'crop','growth_stage','moisture_stress','weather','water_balance',
        'irrigation_advisory','charts','ai_explanation'
    )
);

CREATE TABLE IF NOT EXISTS analysis_explanations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    language TEXT NOT NULL CHECK (language IN ('en', 'ta')),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    authoritative BOOLEAN NOT NULL DEFAULT FALSE CHECK (authoritative = FALSE),
    context_sha256 TEXT NOT NULL CHECK (length(context_sha256) = 64),
    explanation JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (request_id, language, provider, model, prompt_version, context_sha256)
);

CREATE INDEX IF NOT EXISTS analysis_explanations_request_idx
    ON analysis_explanations(request_id, created_at DESC);

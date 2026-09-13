-- Canonical response payloads preserve immediate/stored response parity while
-- normalized weather and ledger tables remain available for querying/charts.
CREATE TABLE analysis_result_payloads (
    request_id UUID NOT NULL REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    result_type TEXT NOT NULL CHECK (result_type IN ('weather','water_balance','irrigation_advisory')),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (request_id, result_type)
);

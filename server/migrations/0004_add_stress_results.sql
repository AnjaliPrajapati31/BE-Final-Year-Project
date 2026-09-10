-- Migration 0004: Add moisture-stress risk results table and extend analysis_runs status

-- 1. Extend the status check constraint to include the new running_stress_rules step
ALTER TABLE analysis_runs DROP CONSTRAINT analysis_runs_status_check;
ALTER TABLE analysis_runs ADD CONSTRAINT analysis_runs_status_check
    CHECK (status IN (
        'pending',
        'fetching_crop_data',
        'running_crop_model',
        'fetching_stage_data',
        'running_stage_rules',
        'running_stress_rules',
        'completed',
        'partial',
        'failed'
    ));

-- 2. Add stress_rule_version to analysis_runs provenance
ALTER TABLE analysis_runs
    ADD COLUMN IF NOT EXISTS stress_rule_version TEXT NOT NULL DEFAULT 'provisional-cauvery-v1';

-- 3. New table: stress_results
CREATE TABLE stress_results (
    request_id                UUID        PRIMARY KEY REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    status                    TEXT        NOT NULL,
    reason_code               TEXT,
    provisional               BOOLEAN     NOT NULL DEFAULT TRUE,
    stress_risk               TEXT        CHECK (stress_risk IN (
                                              'No stress evidence',
                                              'Possible stress',
                                              'Moderate stress risk',
                                              'High stress risk'
                                          )),
    stress_score              DOUBLE PRECISION,
    latest_observation_date   DATE,
    persistence_observations  INTEGER,
    stage_context             TEXT,
    stage_evidence            TEXT,
    evidence                  JSONB       NOT NULL DEFAULT '[]'::jsonb,
    counter_evidence          JSONB       NOT NULL DEFAULT '[]'::jsonb,
    warning                   TEXT,
    stress_rule_version       TEXT        NOT NULL DEFAULT 'provisional-cauvery-v1',
    result_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

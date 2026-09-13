-- Backend-first weather, water-balance, irrigation and module-run persistence.

ALTER TABLE analysis_runs DROP CONSTRAINT IF EXISTS analysis_runs_status_check;
ALTER TABLE analysis_runs ADD CONSTRAINT analysis_runs_status_check CHECK (status IN (
    'pending','fetching_crop_data','running_crop_model','fetching_stage_data',
    'running_stage_rules','running_stress_rules','fetching_weather',
    'running_water_balance','running_irrigation_advisory','completed','partial','failed'
));

CREATE TABLE analysis_module_runs (
    request_id UUID NOT NULL REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    module TEXT NOT NULL CHECK (module IN (
        'crop','growth_stage','moisture_stress','weather','water_balance','irrigation_advisory'
    )),
    status TEXT NOT NULL CHECK (status IN ('completed','skipped','insufficient_data','failed')),
    provisional BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_level TEXT CHECK (evidence_level IN ('high','medium','low')),
    reason_code TEXT,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    input_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    rule_version TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (request_id, module)
);

CREATE TABLE field_water_profiles (
    field_id UUID PRIMARY KEY REFERENCES fields(id) ON DELETE CASCADE,
    profile_version TEXT NOT NULL,
    overrides JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT NOT NULL CHECK (source IN ('default','user','imported','measured')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE irrigation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    field_revision_id UUID NOT NULL REFERENCES field_revisions(id),
    event_date DATE NOT NULL,
    original_amount DOUBLE PRECISION NOT NULL CHECK (original_amount > 0),
    original_unit TEXT NOT NULL CHECK (original_unit IN ('mm','m3')),
    gross_depth_mm DOUBLE PRECISION NOT NULL CHECK (gross_depth_mm > 0),
    irrigation_method TEXT NOT NULL,
    application_efficiency DOUBLE PRECISION NOT NULL CHECK (application_efficiency > 0 AND application_efficiency <= 1),
    net_depth_mm DOUBLE PRECISION NOT NULL CHECK (net_depth_mm > 0),
    source TEXT NOT NULL CHECK (source IN ('user','imported','default')),
    client_event_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','voided')),
    supersedes_event_id UUID REFERENCES irrigation_events(id),
    correction_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    voided_at TIMESTAMPTZ,
    UNIQUE (field_id, client_event_id)
);
CREATE INDEX irrigation_events_field_date ON irrigation_events(field_id, event_date);

CREATE TABLE weather_daily (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID NOT NULL REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    weather_date DATE NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('historical','forecast')),
    source TEXT NOT NULL,
    rainfall_mm DOUBLE PRECISION NOT NULL CHECK (rainfall_mm >= 0),
    et0_mm DOUBLE PRECISION NOT NULL CHECK (et0_mm >= 0),
    quality TEXT,
    raw_variables JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_creation_time TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (request_id, weather_date, kind)
);

CREATE TABLE water_balance_results (
    request_id UUID PRIMARY KEY REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    reason_code TEXT,
    provisional BOOLEAN NOT NULL DEFAULT TRUE,
    evidence_level TEXT,
    rule_version TEXT NOT NULL,
    profile_version TEXT NOT NULL,
    cycle_start DATE,
    cycle_start_source TEXT,
    initial_state_source TEXT,
    as_of_date DATE,
    water_deficit_mm DOUBLE PRECISION,
    water_deficit_low_mm DOUBLE PRECISION,
    water_deficit_high_mm DOUBLE PRECISION,
    root_depletion_mm DOUBLE PRECISION,
    ponded_water_mm DOUBLE PRECISION,
    total_available_water_mm DOUBLE PRECISION,
    readily_available_water_mm DOUBLE PRECISION,
    cumulative_etc_mm DOUBLE PRECISION,
    cumulative_rainfall_mm DOUBLE PRECISION,
    cumulative_irrigation_mm DOUBLE PRECISION,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    assumptions JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE water_balance_daily (
    request_id UUID NOT NULL REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    balance_date DATE NOT NULL,
    kind TEXT NOT NULL,
    values JSONB NOT NULL,
    PRIMARY KEY (request_id, balance_date, kind)
);

CREATE TABLE irrigation_advisory_results (
    request_id UUID PRIMARY KEY REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    action TEXT NOT NULL,
    reason_code TEXT,
    provisional BOOLEAN NOT NULL DEFAULT TRUE,
    evidence_level TEXT,
    rule_version TEXT NOT NULL,
    urgency TEXT,
    reason TEXT,
    net_depth_mm DOUBLE PRECISION,
    gross_depth_mm DOUBLE PRECISION,
    volume_m3 DOUBLE PRECISION,
    irrigation_efficiency DOUBLE PRECISION,
    forecast_rainfall_credited_mm DOUBLE PRECISION,
    trigger_crossing_date DATE,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    result_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

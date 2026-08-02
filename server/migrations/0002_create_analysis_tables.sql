CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE supported_regions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    geometry geometry(MultiPolygon, 4326) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    source TEXT NOT NULL,
    source_checksum TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (NOT ST_IsEmpty(geometry)),
    CHECK (ST_SRID(geometry) = 4326),
    CHECK (ST_IsValid(geometry)),
    UNIQUE (code, version)
);
CREATE UNIQUE INDEX one_active_cauvery_delta_pilot ON supported_regions(code) WHERE code='cauvery_delta_pilot' AND active;
CREATE INDEX supported_regions_geometry_gist ON supported_regions USING GIST(geometry);

CREATE TABLE fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_code TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE field_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_id UUID NOT NULL REFERENCES fields(id),
    revision_number INTEGER NOT NULL CHECK (revision_number > 0),
    geometry geometry(MultiPolygon, 4326) NOT NULL,
    geometry_hash TEXT NOT NULL,
    patch_footprint geometry(Polygon, 4326) NOT NULL,
    area_m2 DOUBLE PRECISION NOT NULL CHECK (area_m2 > 0),
    width_m DOUBLE PRECISION NOT NULL CHECK (width_m > 0),
    height_m DOUBLE PRECISION NOT NULL CHECK (height_m > 0),
    field_pixel_count INTEGER NOT NULL CHECK (field_pixel_count > 0),
    roi_id UUID NOT NULL REFERENCES supported_regions(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(field_id, revision_number),
    UNIQUE(field_id, geometry_hash),
    CHECK (ST_IsValid(geometry)),
    CHECK (ST_IsValid(patch_footprint))
);
CREATE INDEX field_revisions_geometry_gist ON field_revisions USING GIST(geometry);

CREATE TABLE analysis_runs (
    request_id UUID PRIMARY KEY,
    field_revision_id UUID NOT NULL REFERENCES field_revisions(id),
    status TEXT NOT NULL CHECK (status IN ('pending','fetching_crop_data','running_crop_model','fetching_stage_data','running_stage_rules','completed','partial','failed')),
    provider TEXT NOT NULL,
    provider_live_data BOOLEAN NOT NULL,
    provider_cached BOOLEAN NOT NULL,
    year INTEGER NOT NULL,
    season TEXT NOT NULL,
    model_name TEXT NOT NULL,
    checkpoint_sha256 TEXT NOT NULL,
    preprocessing_version TEXT NOT NULL,
    stage_rule_version TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    error_code TEXT,
    error_message TEXT,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    quality_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE crop_results (
    request_id UUID PRIMARY KEY REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    class_code INTEGER NOT NULL CHECK (class_code IN (0,1)),
    class_label TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    paddy_probability DOUBLE PRECISION NOT NULL CHECK (paddy_probability BETWEEN 0 AND 1),
    non_paddy_probability DOUBLE PRECISION NOT NULL CHECK (non_paddy_probability BETWEEN 0 AND 1),
    paddy_pixel_fraction DOUBLE PRECISION NOT NULL CHECK (paddy_pixel_fraction BETWEEN 0 AND 1),
    non_paddy_pixel_fraction DOUBLE PRECISION NOT NULL CHECK (non_paddy_pixel_fraction BETWEEN 0 AND 1),
    field_pixel_count INTEGER NOT NULL,
    s1_observation_count INTEGER NOT NULL,
    s2_observation_count INTEGER NOT NULL,
    used_months JSONB NOT NULL,
    rejected_months JSONB NOT NULL,
    experimental BOOLEAN NOT NULL DEFAULT TRUE,
    result_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE stage_results (
    request_id UUID PRIMARY KEY REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    reason_code TEXT,
    provisional BOOLEAN NOT NULL DEFAULT TRUE,
    stage TEXT,
    evidence TEXT,
    cycle_start DATE,
    latest_observation DATE,
    current_cycle_count INTEGER,
    current_cycle_span_days INTEGER,
    latest_ndvi DOUBLE PRECISION,
    latest_ndmi DOUBLE PRECISION,
    peak_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    maximum_interpretation TEXT,
    selected_s1_orbit_pass TEXT,
    selected_s1_orbit_number INTEGER,
    clean_s1_observation_count INTEGER NOT NULL DEFAULT 0,
    clean_s2_observation_count INTEGER NOT NULL DEFAULT 0,
    warning TEXT
);

CREATE TABLE satellite_observations (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID NOT NULL REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    sensor TEXT NOT NULL CHECK (sensor IN ('S1','S2')),
    observation_date DATE,
    observation_month TEXT,
    source_image_id TEXT,
    purpose TEXT NOT NULL CHECK (purpose IN ('crop','stage','both')),
    accepted BOOLEAN NOT NULL,
    rejection_reason TEXT,
    valid_pixel_count INTEGER,
    valid_pixel_fraction DOUBLE PRECISION,
    zero_fraction DOUBLE PRECISION,
    vv DOUBLE PRECISION,
    vh DOUBLE PRECISION,
    vv_minus_vh DOUBLE PRECISION,
    ndvi DOUBLE PRECISION,
    ndmi DOUBLE PRECISION,
    ndwi DOUBLE PRECISION,
    orbit_pass TEXT,
    orbit_number INTEGER,
    scene_cloud_percentage DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX satellite_observations_request_id ON satellite_observations(request_id);

CREATE TABLE analysis_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES analysis_runs(request_id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(request_id, artifact_type)
);

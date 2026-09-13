-- Audited field-water measurements and irrigation-history coverage declarations.

CREATE TABLE field_water_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    field_revision_id UUID NOT NULL REFERENCES field_revisions(id),
    observed_at TIMESTAMPTZ NOT NULL,
    observation_type TEXT NOT NULL CHECK (observation_type IN (
        'ponded_depth','water_table_depth','volumetric_soil_water'
    )),
    original_value DOUBLE PRECISION NOT NULL CHECK (original_value >= 0),
    original_unit TEXT NOT NULL CHECK (original_unit IN ('mm','m3/m3')),
    ponded_depth_mm DOUBLE PRECISION CHECK (ponded_depth_mm >= 0),
    water_table_depth_mm DOUBLE PRECISION CHECK (water_table_depth_mm >= 0),
    volumetric_soil_water DOUBLE PRECISION CHECK (
        volumetric_soil_water >= 0 AND volumetric_soil_water <= 1
    ),
    measurement_depth_m DOUBLE PRECISION CHECK (
        measurement_depth_m > 0 AND measurement_depth_m <= 3
    ),
    method TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('user','imported','sensor')),
    reliability TEXT NOT NULL CHECK (reliability IN ('high','medium','low')),
    client_observation_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','voided')),
    supersedes_observation_id UUID REFERENCES field_water_observations(id),
    correction_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    voided_at TIMESTAMPTZ,
    UNIQUE (field_id, client_observation_id),
    CHECK (
        (observation_type = 'ponded_depth' AND original_unit = 'mm' AND ponded_depth_mm IS NOT NULL
            AND water_table_depth_mm IS NULL AND volumetric_soil_water IS NULL)
        OR
        (observation_type = 'water_table_depth' AND original_unit = 'mm' AND water_table_depth_mm IS NOT NULL
            AND ponded_depth_mm IS NULL AND volumetric_soil_water IS NULL)
        OR
        (observation_type = 'volumetric_soil_water' AND original_unit = 'm3/m3'
            AND volumetric_soil_water IS NOT NULL AND measurement_depth_m IS NOT NULL
            AND ponded_depth_mm IS NULL AND water_table_depth_mm IS NULL)
    )
);
CREATE INDEX field_water_observations_field_time
    ON field_water_observations(field_id, observed_at);

CREATE TABLE irrigation_history_coverage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    field_revision_id UUID NOT NULL REFERENCES field_revisions(id),
    coverage_start DATE,
    coverage_end DATE,
    coverage_status TEXT NOT NULL CHECK (coverage_status IN ('complete','partial','unknown')),
    source TEXT NOT NULL CHECK (source IN ('user','imported','measured')),
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','superseded')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_at TIMESTAMPTZ,
    CHECK (coverage_end IS NULL OR coverage_start IS NULL OR coverage_end >= coverage_start),
    CHECK (
        (coverage_status = 'unknown')
        OR (coverage_start IS NOT NULL AND coverage_end IS NOT NULL)
    )
);
CREATE UNIQUE INDEX irrigation_history_coverage_one_active
    ON irrigation_history_coverage(field_id) WHERE status = 'active';

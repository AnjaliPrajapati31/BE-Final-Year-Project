-- Preserve the spatial scale associated with each weather estimate.

ALTER TABLE weather_daily
    ADD COLUMN spatial_resolution_m DOUBLE PRECISION
    CHECK (spatial_resolution_m IS NULL OR spatial_resolution_m > 0);

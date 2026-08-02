# Live verification — 2026-08-02

The original public `Cauvery2025` S2 GeoTIFFs were accessed with HTTP byte
ranges; the full multi-gigabyte dataset was not downloaded. PILOT_001 source
blocks reproduced the supplied NPZ exactly. The reconstructed crop rule is a
monthly median after `CLOUDY_PIXEL_PERCENTAGE < 15` for Sentinel-2.

The live Earth Engine PILOT_001 characterization then matched the fixture with
identical grid, 87-pixel field mask, S1 arrays, S2 arrays, retained months, and
Paddy probability `0.7029252052307129` (delta `0.0`).

Two production API analyses were subsequently persisted for the current 2026
season. Both used live, uncached Earth Engine data. Available inputs were June
and July S1 plus June S2; unavailable future/current months were explicitly
reported. Both fields classified Non-Paddy (`0.0465678461` and
`0.0418882295` Paddy probability), so growth-stage inference was correctly
skipped. These are in-season experimental results, not accuracy claims.

ROI version 2 was then frozen from the exact common original S1/S2 raster
coverage and seeded while retaining version-1 provenance. A bounded live search
found a model-predicted Paddy candidate on its fifth attempt near
`79.364111, 10.588068`. The persisted analysis request is
`86cdf71a-e09a-44fc-b1c6-327c9ad34eac`: Paddy probability `0.6469895`, Paddy
pixel fraction `0.8571429`, and provisional stage
`Reproductive / Grain formation` using observations through `2026-07-28`.
The candidate is a generated 70 m square prioritized by live NDVI, not a
surveyed field boundary or independently validated crop label.

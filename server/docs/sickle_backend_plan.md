# Backend implementation status

Implemented:

- Approved disease/soil removal.
- Direct psycopg pool, migrations, PostGIS schema, repositories, and ROI seeding tool.
- Python and PostGIS field/patch containment gates.
- Exact namespaced U-TAE fusion model and strict reusable runtime.
- Crop input contract and field-mask summarization.
- Test-only local fixture provider.
- Live Earth Engine monthly and detailed providers with successful-response cache.
- Provisional stage cleaning/detection/assignment.
- Persistent orchestration, analysis/retrieval/history routes, liveness/readiness, and safe optional JSON artifact writing.

Completed external gates:

- Conservative PILOT_001 coverage boundary frozen, checksummed, and seeded.
- PostgreSQL/PostGIS migrations and authoritative containment verified.
- Earth Engine project and local ADC verified.
- PILOT_001 GeoJSON, NPZ, and raw S1/S2 detailed CSVs installed.
- Drive TIFF extraction and live Earth Engine arrays match the original NPZ exactly.

The original crop NPZ is present under `tests/fixtures/sickle/pilot_001`; strict checkpoint crop parity and raw time-series stage parity pass.

Production readiness returns HTTP 200 when the configured database, PostGIS ROI, Earth Engine ADC, checkpoint, model, and artifact dependencies are usable; otherwise it degrades safely to HTTP 503.

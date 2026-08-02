# Cauvery Field Analysis

FastAPI, PostGIS, Google Earth Engine, and SICKLE-based field analysis for the
verified Cauvery raster coverage. Production requests use live Earth Engine
data; the local PILOT_001 fixture is only a known-answer regression test.

## What is included

- Live Sentinel-1 and Sentinel-2 retrieval from Earth Engine.
- Frozen 32 × 32 preprocessing and strict SICKLE checkpoint loading.
- Paddy/Non-Paddy field-mask summaries.
- Provisional, rule-based growth-stage estimation for Paddy results.
- Python and authoritative PostGIS containment gates.
- Persistent analyses, observations, quality metadata, stages, and artifacts.
- FastAPI analysis, retrieval, history, liveness, and readiness routes.
- A small frontend shell; map integration remains a later frontend task.

The deployable checkpoint is
`server/ml_models/sickle/checkpoint_best.pt` (approximately 14.43 MiB). Local
research notebooks, upstream references, and historical training experiments
are intentionally Git-ignored and are not required at runtime.

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/).
- PostgreSQL with PostGIS.
- Node.js and npm for the frontend.
- Google Cloud CLI, an Earth Engine-enabled project, and local Application
  Default Credentials (ADC).

## Backend setup

```powershell
cd server
uv sync --group dev
Copy-Item .env.example .env
```

Configure `server/.env` with the PostgreSQL URL and Earth Engine project ID.
Do not put a Google password, OAuth token, private key, or service-account JSON
contents in `.env`.

For local Earth Engine authentication:

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

ADC is sufficient locally; no service-account JSON is needed. In production,
attach a service account/workload identity to the runtime. If a key file is
unavoidable, mount it outside the repository and set
`GOOGLE_APPLICATION_CREDENTIALS` to its absolute path.

Apply the database schema and seed the configured ROI:

```powershell
cd server
uv run python scripts/migrate.py
uv run python scripts/seed_cauvery_roi.py
uv run python scripts/verify_readiness.py
```

Start the API:

```powershell
cd server
uv run uvicorn app.main:app --reload
```

Useful endpoints:

- `GET /health`
- `GET /health/ready`
- `POST /api/v1/fields/analyze`
- `GET /api/v1/analyses/{request_id}`
- `GET /api/v1/fields/{field_id}/analyses`
- `GET /api/v1/analyses/{request_id}/artifacts/{artifact_type}`

Example request body:

```json
{
  "field_id": "FIELD_001",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[79.3166, 10.8672], [79.3175, 10.8675], [79.3173, 10.8682], [79.3165, 10.8681], [79.3166, 10.8672]]]
  },
  "year": 2026,
  "season": "june_october",
  "generate_artifacts": false
}
```

The current year is allowed, but future years are rejected. In-season results
use only observations already available; future months are never fabricated.

## Scientific and live commands

Run the separate local 2025 known-answer gate:

```powershell
cd server
uv run python scripts/run_pilot.py
```

It verifies the supplied local NPZ/CSVs, exact checkpoint, Paddy probability,
field mask, and corrected stage result. This provider cannot be selected from
the public API.

Verify the original public Drive S2 TIFF blocks against the local fixture:

```powershell
cd server
uv run python scripts/verify_drive_s2.py
```

This uses HTTP byte ranges rather than downloading the full TIFF collection.
It requires the referenced Drive files to remain publicly readable.

Compare live 2025 Earth Engine arrays with the golden fixture:

```powershell
cd server
uv run python scripts/characterize_live_pilot.py
```

Run two current-season analyses through the production API lifecycle:

```powershell
cd server
uv run python scripts/run_live_current.py
```

Run the bounded diagnostic Paddy search:

```powershell
cd server
uv run python scripts/find_live_paddy.py
```

The search uses live NDVI only to prioritize candidates. Every candidate still
passes Python and PostGIS containment and the unchanged checkpoint. A result is
a model prediction over a generated square—not field-survey ground truth—and
must not be presented as validated crop truth.

## Tests

```powershell
cd server
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m golden
uv run pytest -m gee_live
uv run pytest -q
```

Frontend verification:

```powershell
cd client
npm install
npm run lint
npm run build
npm run dev
```

## ROI versions

- Version 1 preserves the original PILOT_001 patch boundary for stored-analysis
  provenance.
- Version 2 is the exact common EPSG:4326 coverage/grid of the original S1/S2
  exports and is the active operational ROI.

Version 2 is verified raster coverage, not a claim that the rectangle is an
official administrative Cauvery Delta boundary. Submitted fields and their
complete 32 × 32 footprints must be covered by the active ROI before Earth
Engine is called.

## Repository hygiene

Committed/runtime material includes application code, migrations, ROI
resources, the compact golden fixtures, and the deployable checkpoint.

The following remain untracked:

- `.env` and credentials.
- Earth Engine cache and generated artifacts.
- Full TIFF collections.
- Research notebooks and upstream reference source.
- Historical S1/S2 training experiments and duplicate checkpoints.
- Python, test, Node, and frontend build caches.

Never commit credentials or claim model confidence as measured accuracy. Crop
and stage outputs remain experimental; growth stage is provisional and is
skipped for Non-Paddy results.

# Cauvery SICKLE API

FastAPI backend for Cauvery-only field validation, live Earth Engine retrieval, SICKLE paddy classification, provisional growth-stage and moisture-stress estimation, FAO-56 weather/ET0 processing, provisional paddy water balance, irrigation advisory, and PostGIS persistence.

Moisture stress is implemented and integrated but remains provisional. It is supporting evidence only: its score is never converted into millimetres and never determines irrigation quantity. Water balance and irrigation advice are also provisional until field validation is completed.

## Local setup

```powershell
uv sync --group dev
Copy-Item .env.example .env
uv run python scripts/migrate.py
uv run python scripts/seed_cauvery_roi.py
uv run uvicorn app.main:app --reload
```

The versioned operational ROI resources and matching manifests are included and must be seeded before startup. Version 1 preserves PILOT_001 provenance; active version 2 is the exact common original S1/S2 raster coverage. Earth Engine authentication must be completed outside the application; see `docs/earth_engine_setup.md`.

## Verification

```powershell
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m golden
uv run pytest -m gee_live
uv run python scripts/verify_readiness.py
uv run python scripts/characterize_live_pilot.py
uv run python scripts/run_live_current.py
```

`scripts/run_pilot.py` is the only fixture-backed end-to-end path. Public FastAPI requests cannot select it.

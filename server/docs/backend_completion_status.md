# Backend completion status

Updated: 2026-09-13

## Stage 0 — Existing scientific baseline

Complete. Crop/stage PILOT_001 parity remains intact. Moisture stress is integrated, explicitly provisional, covered by direct rule tests, and included in the golden gate. Migration 0004 drift is safely adopted when the verified schema already exists. Artifact generation, frontend lint, and immediate/stored canonical payload handling are repaired.

## Stage 1 — Module and evidence contracts

Complete. Crop, growth stage, moisture stress, weather, water balance, and irrigation advisory have independent `completed`, `skipped`, `insufficient_data`, or `failed` outcomes with provisional/evidence/reason/warning/source/version fields. Crop failure is terminal; independent downstream failures preserve earlier results.

## Stage 2 — Field water profile and irrigation history

Complete for backend operation. `cauvery-paddy-v1` is machine-readable and includes units, ranges, sources, stage Kc values, ponding targets, seepage sensitivity, and irrigation efficiency. Water-profile and audited irrigation-event APIs persist geometry revision, original amount/unit, normalized gross/net depth, source, corrections, and void history.

## Stage 3 — Historical and forecast weather

Complete and live-tested. Historical rainfall uses GPM IMERG, meteorology uses ERA5-Land, and ET0 is computed in the backend with FAO-56 Penman–Monteith. GFS uses one complete model run, local-day aggregation, and disjoint six-hour precipitation steps. Cache keys include geometry, dates/horizon, collections, ET0 version, mode, timezone, and GFS creation time. Coarse resolution and data lag are explicit.

## Stage 4 — Paddy water balance

Complete as a pure deterministic module. The daily ledger covers rainfall, recorded net irrigation, ETc, seepage/percolation, ponding, root depletion, runoff, deficit, sensitivity range, triggers, and mass-conservation residual. Maturity/post-harvest does not trigger ordinary refill.

## Stage 5 — Scientific field validation

Infrastructure complete; measured validation data pending. The validation harness computes paired bias/MAE/RMSE and fails closed unless at least five unique known-Paddy fields, crop-cycle dates, soil descriptions, dry-down/refill events, rainfall/ET0 pairs, field-water observations, and conservation evidence are present. No water-deficit accuracy claim is currently publishable.

## Stage 6 — Orchestrator, database, API, artifacts

Complete. Migrations 0005–0009 persist module runs, profiles, irrigation history, weather, full balance ledgers, summaries, advisories, canonical result/chart payloads, and ROI-versioned field revisions. JSON/CSV water artifacts are supported. Real current-season API analyses now enforce exact immediate/stored response parity.

## Stage 7 — Irrigation advisory

Complete as a provisional rules engine. It returns action, depth, volume, urgency, trigger/crossing information, credited forecast rainfall, reasons, assumptions, and evidence. Missing forecasts degrade to current-state monitoring; stale historical state blocks advice entirely.

## Stage 8 — Operational hardening

Automated and live software gates complete. Failure isolation, Non-Paddy skipping, missing stage/weather, stale historical data, invalid profiles, database-write failure, cache behavior, correction history, and artifacts are tested. Readiness reports ROI, checkpoint, database, schema, satellite, historical weather, forecast weather, and artifact storage independently.

Remaining external gate: ingest measured observations for the five-field validation set and freeze any scientifically justified parameter changes as a new profile version.

## Stage 9 — Frontend

Intentionally deferred. The existing frontend only received lint/build compatibility fixes. Water-profile editing, irrigation-event entry, water charts, and advisory display must not be prioritized until Stage 5 measured validation is complete.

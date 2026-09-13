# Scientific validation status

## Operational interpretation

Crop inference retains the PILOT_001 checkpoint/preprocessing regression gate. Growth stage, satellite moisture-stress risk, paddy water balance, and irrigation advice are provisional research outputs. Moisture-stress score is supporting evidence only and is never converted to water deficit or irrigation depth.

## Computational gates completed

- Crop, stage, and stress PILOT_001 known-answer assertions.
- Stress skip, exclusion, insufficient-observation, persistence, corroboration, cloud, optional-radar, and malformed-value rules.
- FAO-56 Penman–Monteith deterministic fixture and unit validation.
- GFS six-hour precipitation aggregation without overlapping-step double counting.
- Paddy daily mass-conservation residual below `1e-6 mm` in fixtures.
- ET0/Kc, rain, irrigation, seepage, overflow, dry-down, maturity, and sensitivity behavior.
- Exact depth/area/volume and application-efficiency conversion.
- Non-Paddy skip and module failure-isolation orchestration.
- Authenticated Earth Engine initialization, historical GPM/ERA5-Land retrieval, and GFS forecast retrieval.

## Field validation still required

PILOT_001 has no measured irrigation quantities or field-water-depth record and is not water-balance truth. Before removing the provisional label, collect at least five Paddy fields with known crop-cycle dates, irrigation dates and quantities, local rain-gauge data, soil description, and periodic ponded/root-zone water observations. The set must include a dry-down and a rainfall/refill event.

Report rainfall bias/error, ET0 agreement, cumulative closure, ponding/depletion error, and sensitivity to seepage, soil, initial state, and unrecorded irrigation. Freeze any changed parameter values as a new profile version; never edit `cauvery-paddy-v1` silently.

## Validation harness

Copy `resources/validation/water-field-validation-template.json`, populate its `fields` array from measured records, and run:

```powershell
uv run python scripts/validate_water_fields.py path\to\measured-fields.json --output artifacts\validation\water-validation-report.json
```

The command exits unsuccessfully and sets `water_deficit_accuracy_publishable` to `false` until every field-count, event, paired-measurement, and conservation gate passes. Missing measurements must remain `null`; they must not be entered as zero.

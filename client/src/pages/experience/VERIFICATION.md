# Three-step journey verification

Date: 2026-09-21

## Executed checks

- Client: `node --test src/lib/journey.test.js` — 5 tests passed (circle coverage, supported GeoJSON normalization, invalid geometry shapes/values, approximate area, stale field/run rejection, explicit daily gaps).
- Client: `npm run lint` — passed.
- Client: `npm run build` — passed. Vite reports large chunks; this is not a runtime performance measurement.
- Server: `.venv\\Scripts\\python.exe -m pytest tests/unit/test_coverage.py tests/unit/test_api_contract.py -q -p no:cacheprovider` — 10 passed. Existing Starlette/httpx deprecation warning remains.
- Coverage tests assert loaded geometry/checksum and reject absent or unverified coverage.

## Production bundle sample

Before the final small cleanup, build reported: home UI 2.60 kB (1.15 kB gzip), lazy map 161.55 kB (48.08 kB gzip), lazy renderer 576.50 kB (148.36 kB gzip), main application 848.55 kB (263.52 kB gzip). These are JavaScript bundle sizes, not total network payload or graphics performance.

## Not performed

No servers or browser sessions were started, as requested. No new comparison screenshots, runtime console inspection, network capture, frame-time measurement or GPU profiling was performed. Historical screenshots and frame rates do not validate this revision.

Pending browser/device acceptance:

- Ground composition against the supplied dense-field screenshot; light, canopy continuity, bank/farmer grounding and tree placement.
- Pointer/keyboard transition, focus, rapid activation, slow route load, Back and route exit.
- Empty map, drawing/undo/finish/clear/upload, coverage failure/retry, tile errors and preserved drafts.
- Complete Paddy, Non-Paddy, missing weather, forecast-only weather, missing advice and partial failures.
- Direct links, refresh, changing stored runs and consistent field identity across every tab.
- Record saving followed by a new analysis; disabled AI staying unavailable.
- Mobile panels/touch/orientation, reduced motion, forced WebGL failure and repeated route disposal.
- Network check for absence of analysis/field writes until explicit submission.
- Actual desktop/mobile frame times, hardware/GPU, viewport and resource cleanup.

Visual acceptance remains pending; do not describe the revised landscape as screenshot-matched or performance-certified.

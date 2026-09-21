# CropSense three-step journey — v3

The application has three workflow steps: home `/`, field selection `/fields`, and stored results `/dashboard?requestId=…&fieldId=…`. The old eight-chapter story has been removed. `/experience` redirects home; `/analytics` remains supported.

## Architecture

- Experience.jsx renders one living-field viewport with ambient movement, pause, reduced-motion behavior and a lightweight illustration if graphics fail.
- world/renderer.js owns one static home camera, shared wind, scene lifecycle and adaptive quality. No scroll ascent or scientific overlays remain.
- RouteTransition.jsx preloads the map, covers the viewport with a GSAP circle from the pointer (button centre for keyboard), navigates, fades out and transfers focus. Loading has a bounded timeout; remote tiles do not block revealing the map shell.
- MyFields.jsx starts without a sample polygon, preserves a session draft, supports drawing and a single Polygon GeoJSON upload, and retrieves the approved coverage geometry.
- GET /api/v1/coverage exposes the verified ROI already loaded by the backend. It does not replace server geometry, patch or satellite validation.
- useCurrentAnalysis.js validates request and field identity before showing results and deduplicates simultaneous reads.
- ResultsShell.jsx supplies contextual result tabs. Existing record, history and analysis APIs remain unchanged.
- Optional AI explanation is hidden unless readiness explicitly enables it.

## Boundaries

The home landscape is illustrative, not a georeferenced field or scientific result. Scientific models, irrigation calculations and database schemas are unchanged. The home itself does not trigger analysis. An explicit Run analysis submits the selected boundary; timed-out requests are never automatically resubmitted.

See STORYBOARD.md for the visual contract and asset origins, and VERIFICATION.md for measured versus pending checks.

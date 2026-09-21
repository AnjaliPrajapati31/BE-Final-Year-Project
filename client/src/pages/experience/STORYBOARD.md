# CropSense visual contract — v3

## 1. Living field

Match the user's older ground-level screenshot in composition: dense overlapping green rice leaves with modest gold heads in the foreground, continuous middle-distance canopy, a shallow canal toward the horizon, a small grounded farmer, margin palms and layered distant trees under a bright hazy sky.

The implementation adds local dense rice infill rather than uniformly increasing the entire valley, strengthens the distant tree line, fixes the home camera, and reduces the text shading. These are implemented changes, not a claim that visual matching has passed.

Only brand, My fields, heading, short supporting copy, Analyze field and a discreet motion control belong on this screen. No chapter explanations, aerial destination, diagrams or simulated results.

Reject sparse foreground gaps, floating banks/farmer, tree obstructions, excessive dark gradients, abrupt vegetation detail changes, or a canal that looks like an ocean.

## 2. Map workspace

Use a real interactive basemap with accurately named street/satellite layers. Start without a selected example. Draw approved coverage only from the backend response. Keep the boundary visible while submitting and preserve the draft on failure.

Desktop: map and approximately 360 px review panel. Mobile: map above collapsible tools, with a reachable submit action. Coverage is advisory; server validation remains authoritative.

Reject fabricated coverage, blocked drawing surfaces, loss of the boundary on error, automatic timeout resubmission, or technical exception text as the main explanation.

## 3. Stored results

Lead with field identity/freshness and the actual irrigation action or missing-information explanation, followed by crop/stage/stress/deficit summaries, evidence, warnings and expandable diagnostics.

Contextual tabs keep the same request and field IDs. Loading another run must not show the preceding run's figures. Missing values are not zero. Saved records require a new analysis to affect results.

## Transition acceptance

The green reveal originates at the click position or keyboard button centre, covers the farthest corner, blocks repeated activation, then reveals the map shell without waiting for tiles. Reduced motion skips camera/text movement and uses immediate route transition. Back, route interruptions and failure recovery must not leave an overlay behind.

## Asset-origin manifest

| Asset | Origin | License / attribution |
|---|---|---|
| Rice, terrain, trees, farmer and canal geometry | Existing project procedural code plus local revisions | Repository ownership/license; no downloaded models |
| Procedural canopy and environment materials | Project shader/code assets | Repository ownership/license |
| Water rendering helper | Three.js dependency | MIT; retain dependency license |
| UI icons | Existing Lucide dependency | ISC; retain dependency license |
| GSAP transition | Installed GSAP dependency | Retain installed package license and applicable GSAP terms |
| Reference screenshot | User-provided older project screenshot | Visual reference only; not embedded as a background |

No game assets, stock video, generated raster artwork or new external models were introduced. Existing basemap providers retain their on-map attribution. Reference imagery establishes visual intent, not verification of the revised renderer.

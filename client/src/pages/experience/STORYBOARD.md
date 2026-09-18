# CropSense Landscape Storyboard v2

## Visual contract

The experience follows one illustrative paddy parcel through the CropSense decision flow. It uses a level cultivated valley, gently rising margins, and distant ridges for atmospheric depth. The scene is not a reconstruction of a real location and never displays invented analysis results.

References are used for technique only: Anime.js for scroll-synchronised progression and restrained typography; Ghost of Tsushima's published environmental-effects discussion for coordinated wind; Three.js terrain, water, instancing, and level-of-detail examples for rendering structure. No third-party visual assets are included.

## Composition frames

| Frame | Camera and composition | Required visual reading | Reject when |
|---|---|---|---|
| Ground | Low among detailed rice, canal leading into depth, farmer in middle distance | Rice, shallow water, connected bunds, valley and distant ridge layers | Nearby trees block the story, water reads as ocean, or field paths float |
| Mid-rise | Hero parcel remains central while the camera clears the canopy | Connected unequal parcels, canal hierarchy, retained crop coverage | Crop vanishes into a smooth plane or chapter overlays hide the field |
| Direct overhead QA | Temporary inspection pose, independent of final camera | Shared edges, no overlaps, no crossing or unconnected paths | Repeating square wallpaper, loose diagonal strokes, or material bleed |
| Final aerial | Broad oblique view with the hero outline and complete valley | One readable landscape, real field-tool action, illustrative disclosure | Hero field disappears, parcel edges become wires, or hills imply actual geography |

## Chapters

| Chapter | Camera | Scene layer | Copy purpose | Failure condition |
|---|---|---|---|---|
| Cover | Ground | Living rice, farmer, water and wind | Invite native scrolling | Timed autoplay begins without input |
| Crop | Canopy | Hero outline and sensing ring | Explain Paddy / Non-Paddy gate | Suggests a real result for this scene |
| Growth | Low rise | Seasonal context motif | Explain stage-dependent interpretation | Claims exact stage truth |
| Stress | Held rise | Local amber evidence area | Explain persistent corroborated risk | Converts stress to deficit or irrigation |
| Weather | Valley reveal | Rain points and atmospheric motion | Explain rainfall, ET0 and forecast | Presents coarse weather as a field gauge |
| Water balance | Medium aerial | Water-accounting ring | Explain ponding, depletion and deficit | Hides missing irrigation or assumptions |
| Irrigation | Wider aerial | Decision marker | Explain timing, depth, efficiency and volume | Implies AI sets water quantity |
| Evidence | Stable aerial | Provenance graphic | Explain charts, warnings and evidence | Treats AI explanation as calculation |
| Your field | Complete aerial | Persistent hero boundary | Move to the operational field tool | Displays invented selectable coordinates |

## Interaction acceptance

- Scroll position is the single narrative clock; stopping holds camera and overlays.
- Reverse scrolling restores every prior state without replay artifacts.
- Explore, chapter navigation, and Skip move to real semantic sections.
- The page does not intercept the wheel or force snap positions.
- Reduced motion preserves readable sections and removes animated transitions.
- The story performs no backend reads, field writes, model execution, or chatbot calls.

## Asset manifest

All landscape geometry, materials, shaders, typography layouts, diagrams, and icons are locally authored or use existing project dependencies. Lucide icons are covered by its ISC license. No photographs, videos, game assets, downloaded models, audio, or generated raster images are included.

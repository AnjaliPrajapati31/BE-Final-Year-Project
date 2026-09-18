# Cinematic Farm Experience

`/experience` is a lazy-loaded, scroll-controlled design preview. Native page scroll drives one deterministic story position from zero to one. The Three.js renderer derives camera, fog, vegetation detail, hero-field emphasis, and explanatory scene layers from that value; it owns no competing travel timer.

## Architecture

- `story.js` is the source of truth for the eight chapters and their scientifically qualified copy.
- `Experience.jsx` provides semantic sections, chapter navigation, reduced-motion behavior, and Anime.js ScrollObserver synchronization.
- `world/landscape.js` owns the fixed parcel topology, point-in-polygon checks, boundary distance, terrain height, hero parcel, and chapter camera poses.
- The renderer exposes `setStoryProgress`, `setQuality`, `setAmbientMotion`, `resize`, and `dispose`.
- Parcel surfaces, physical bunds, crop placement, and the hero outline all derive from the same 48 polygons.

## Product boundary

The final chapter links to `/fields`. The preview does not read an operational ROI, claim selectable coordinates, call an analysis API, save a field, or invoke the chatbot. A later real-map integration must retrieve the active coverage boundary and retain server-side geometry and patch validation.

## Rendering and fallback

The scene uses procedural terrain, a mostly level cultivated valley, rising margins, distant ridges, shallow canal water, instanced rice, bank-aligned palms, atmospheric haze, and a shared wind field. Pixel ratio is capped and quality reduces progressively when measured performance is low. A renderer failure leaves the complete HTML story and field-tool navigation available.

See `STORYBOARD.md` for chapter compositions, visual references, rejection criteria, and the asset manifest.

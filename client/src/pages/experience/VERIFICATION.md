# CropSense experience verification

Date: 2026-09-18

## Measured configuration

- Browser: Chromium in the Codex in-app browser (development build).
- Viewport: 1280 x 720 CSS pixels.
- Device pixel ratio: 2; renderer cap: 1.5.
- Hardware/GPU identity: unavailable from the test surface.
- Scene sample after warm-up: 64.5 fps, 60 draw calls, 510,984 triangles, 12,090 rice instances.
- Production chunks: experience UI 52.40 kB / 19.92 kB gzip; lazy renderer 582.61 kB / 149.39 kB gzip.

The measured frame rate is above both the automatic quality-reduction threshold of 30 fps and the 60 fps target on this test surface. It is a development-browser measurement, not a guarantee for other hardware.

## Verified

- Direct navigation and refresh at `/experience`.
- Native scroll moves the camera and story; stopping scroll holds scene progress.
- Programmatic chapter jumps and restored scroll position derive the same scene state from document progress.
- Reverse movement is stateless; no accumulated camera animation is used.
- Opening, crop chapter, final aerial, and direct-overhead compositions were inspected.
- The direct-overhead view contains 48 reproducible parcels with exclusive centroid ownership and a valid hero parcel.
- The cultivated world continues beyond the final camera view; there is no exposed rectangular landscape plate.
- Shared parcel edges generate both surfaces and low earthen bunds; the canal is recessed and banked.
- Rice placement is constrained to parcel interiors and excludes bund/canal margins.
- Aerial rice uses deterministic strata across the full valley instead of random thinning or the former partial bounds.
- Palms use deterministic ecological clusters distributed over the canal range, with deliberate gaps and a protected foreground camera area.
- Every chapter has a distinct reversible scene treatment and a feature-specific explanatory diagram.
- Reduced-motion emulation reports the expected media query and zero-second text transitions.
- No analysis or field-write request is initiated by the route.
- ESLint and production build pass.
- Runtime console inspection found no application errors.

## Not claimed as tested

- A physical touch device and orientation sensor.
- Forced WebGL context creation failure (the HTML fallback path exists but was not fault-injected).
- GPU memory profiling across long repeated-route sessions.
- Safari or Firefox rendering parity.

These checks should remain explicit rather than being marked complete without a real device or fault-injection run.

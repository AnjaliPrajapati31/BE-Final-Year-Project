# Frozen scientific contract

The crop-composite contract uses monthly medians. Sentinel-2 scenes are
filtered with `CLOUDY_PIXEL_PERCENTAGE < 15` before compositing. This rule was
reconstructed from the original `Cauvery2025` exports and verified
pixel-for-pixel for PILOT_001: June, July, and October match exactly, while
August and September reproduce the original nodata rejection. Detailed stage
time series remain acquisition-level and do not apply this crop-composite
scene filter.

Crop inference uses S1 bands `VV,VH`; S2 bands `B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B11,B12`; monthly midpoint day positions `15,45,76,107,137`; float32 arrays; native S1 dB-style values; and S2 0–10000-style values without division by 10,000. A monthly patch is accepted only when the zero fraction of its first selected band is strictly below 0.25. No temporal interpolation or month substitution is permitted.

The model is the original two-satellite U-TAE fusion graph, including its unused primary branch. Startup strips only `module.` and `_orig_mod.` prefixes, loads the `model` state strictly, requires 1,597,010 parameters, calls `eval()`, and reuses one concurrency-limited runtime under `torch.inference_mode()`.

Class 0 is Paddy and class 1 is Non-Paddy. Probabilities and pixel fractions are summarized only inside the field mask. Reported confidence is model probability, not measured accuracy.

Growth stage is provisional and runs only for Paddy. It requires detailed optical acquisitions, never the three/five monthly crop composites. A maximum is confirmed as a peak only after a later NDVI decline of at least 0.15.

The supplied original PILOT_001 NPZ passes the actual CPU checkpoint gate: Paddy probability `0.7029250264` (tolerance `1e-4`), Paddy pixel fraction `1.0`, and 87 field pixels. The processed optical reference separately reproduces the corrected provisional stage. No synthetic or hard-coded crop result substitutes for checkpoint inference.

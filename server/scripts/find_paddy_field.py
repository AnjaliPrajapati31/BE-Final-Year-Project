"""
find_paddy_field.py — tries several candidate polygons in the Cauvery Delta
paddy belt and prints the first one classified as Paddy.

Run from server/:
  uv run python scripts/find_paddy_field.py
"""
import json, time
import httpx

API = "http://localhost:8000/api/v1/fields/analyze"

# 0.002° × 0.002° boxes (~200 m × 200 m) centred on known paddy zones.
# Each box is expressed as [lng, lat] corners (GeoJSON order).
CANDIDATES = [
    {
        "name": "Papanasam paddy belt",
        "field_id": "TEST_PAPANASAM_01",
        "center": (10.9346, 79.2756),
    },
    {
        "name": "Kumbakonam canal zone",
        "field_id": "TEST_KUMBAKONAM_01",
        "center": (10.9624, 79.3897),
    },
    {
        "name": "Tiruvarur delta core",
        "field_id": "TEST_TIRUVARUR_01",
        "center": (10.7673, 79.6347),
    },
    {
        "name": "Nagapattinam coast belt",
        "field_id": "TEST_NAGAPATTINAM_01",
        "center": (10.7630, 79.8449),
    },
    {
        "name": "Thanjavur east fringe",
        "field_id": "TEST_THANJAVUR_E_01",
        "center": (10.7932, 79.2456),
    },
    {
        "name": "Needamangalam area",
        "field_id": "TEST_NEEDAMANGALAM_01",
        "center": (10.8053, 79.5012),
    },
    {
        "name": "Peravurani paddy",
        "field_id": "TEST_PERAVURANI_01",
        "center": (10.2900, 79.6100),  # slightly south
    },
    {
        "name": "Sirkazhi zone",
        "field_id": "TEST_SIRKAZHI_01",
        "center": (11.2337, 79.7444),
    },
    {
        "name": "Mayiladuthurai",
        "field_id": "TEST_MAYILADUTHURAI_01",
        "center": (11.1024, 79.6516),
    },
    {
        "name": "Sethubavachatram",
        "field_id": "TEST_SETHU_01",
        "center": (10.8800, 79.4500),
    },
]


def make_polygon(lat_center: float, lng_center: float, half: float = 0.001):
    """Return a tiny square GeoJSON Polygon around (lat, lng)."""
    w, e = lng_center - half, lng_center + half
    s, n = lat_center - half, lat_center + half
    coords = [[w, s], [e, s], [e, n], [w, n], [w, s]]
    return {"type": "Polygon", "coordinates": [coords]}


def analyze(candidate: dict) -> dict | None:
    lat, lng = candidate["center"]
    payload = {
        "field_id": candidate["field_id"],
        "geometry": make_polygon(lat, lng),
        "year": 2025,
        "season": "june_october",
        "generate_artifacts": False,
    }
    try:
        print(f"\n→ Testing: {candidate['name']}  ({lat:.4f}°N, {lng:.4f}°E)")
        t0 = time.time()
        resp = httpx.post(API, json=payload, timeout=120)
        elapsed = time.time() - t0
        if resp.status_code != 200:
            print(f"  ✗ HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json().get("data", {})
        crop = data.get("crop") or {}
        label = crop.get("class_label", "?")
        conf = crop.get("confidence", 0)
        print(f"  ✓ {label}  confidence={conf:.1%}  ({elapsed:.1f}s)")
        if label == "Paddy":
            return {
                "candidate": candidate,
                "request_id": data.get("request_id"),
                "crop": crop,
                "growth_stage": data.get("growth_stage"),
                "moisture_stress": data.get("moisture_stress"),
                "payload": payload,
            }
        return None
    except Exception as exc:
        print(f"  ✗ Error: {exc}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("Cauvery Delta Paddy Field Finder")
    print("Trying candidate locations until a Paddy field is found…")
    print("=" * 60)

    found = None
    for candidate in CANDIDATES:
        result = analyze(candidate)
        if result:
            found = result
            break

    print("\n" + "=" * 60)
    if found:
        c = found["candidate"]
        lat, lng = c["center"]
        stress = found.get("moisture_stress") or {}
        print(f"✅ PADDY FIELD FOUND: {c['name']}")
        print(f"   Center:     {lat:.4f}°N, {lng:.4f}°E")
        print(f"   Field ID:   {c['field_id']}")
        print(f"   Request ID: {found['request_id']}")
        print(f"   Confidence: {found['crop'].get('confidence', 0):.1%}")
        print(f"   Stage:      {(found.get('growth_stage') or {}).get('stage', 'N/A')}")
        print(f"   Stress:     {stress.get('stress_risk', 'N/A')}")
        print()
        print("── Polygon to paste into My Fields ──────────────────────")
        coords = found["payload"]["geometry"]["coordinates"][0][:-1]
        for lng2, lat2 in coords:
            print(f"   {lat2:.4f}, {lng2:.4f}")
        print()
        print("── Or open Dashboard directly ───────────────────────────")
        print(f"   http://localhost:5173/dashboard?requestId={found['request_id']}")
        print()
        print("── Full moisture stress result ───────────────────────────")
        print(json.dumps(stress, indent=2, default=str))
    else:
        print("❌ No Paddy field found in any candidate location.")
        print("   Try drawing a field manually in a different area of the Cauvery Delta.")
    print("=" * 60)

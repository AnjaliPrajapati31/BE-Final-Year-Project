from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from shapely.affinity import scale
from shapely.geometry import mapping, shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


def assert_stored_parity(client: TestClient, immediate: dict) -> None:
    response = client.get(f"/api/v1/analyses/{immediate['request_id']}")
    if response.status_code != 200:
        raise SystemExit(f"Stored analysis retrieval failed: {response.json()}")
    stored = response.json()["data"]
    comparable_keys = (
        "status", "provider", "data_quality", "crop", "growth_stage", "moisture_stress",
        "modules", "weather", "water_balance", "irrigation_advisory", "charts",
        "warnings", "artifacts", "provenance",
    )
    differences = [key for key in comparable_keys if immediate.get(key) != stored.get(key)]
    if differences:
        details = {key: {"immediate": immediate.get(key), "stored": stored.get(key)} for key in differences}
        raise SystemExit(f"Immediate/stored response parity failed: {json.dumps(details, default=str)}")


def main() -> None:
    fixture = json.loads(Path("tests/fixtures/sickle/pilot_001/pilot_001.geojson").read_text(encoding="utf-8"))
    pilot = shape(fixture["features"][0]["geometry"])
    fields = {
        "LIVE_CURRENT_PILOT_A": pilot,
        "LIVE_CURRENT_PILOT_B": scale(pilot, xfact=0.65, yfact=0.65, origin="centroid"),
    }
    summaries = []
    with TestClient(app) as client:
        readiness = client.get("/health/ready")
        if readiness.status_code != 200:
            raise SystemExit(f"Production readiness failed: {readiness.json()}")
        for field_id, geometry in fields.items():
            response = client.post(
                "/api/v1/fields/analyze",
                json={
                    "field_id": field_id,
                    "geometry": mapping(geometry),
                    "year": date.today().year,
                    "season": "june_october",
                    "generate_artifacts": False,
                },
            )
            payload = response.json()
            if response.status_code != 200 or not payload.get("success"):
                raise SystemExit(f"Live API analysis failed for {field_id}: {payload}")
            data = payload["data"]
            assert_stored_parity(client, data)
            summaries.append(
                {
                    "field_id": field_id,
                    "request_id": data["request_id"],
                    "status": data["status"],
                    "provider": data["provider"],
                    "field_pixel_count": data["geometry"]["field_pixel_count"],
                    "crop": data["crop"]["class_label"],
                    "paddy_probability": data["crop"]["paddy_probability"],
                    "s1_months": data["crop"]["s1_months_used"],
                    "s2_months": data["crop"]["s2_months_used"],
                    "stage": data["growth_stage"].get("stage"),
                    "stage_status": data["growth_stage"].get("status"),
                    "latest_stage_observation": data["growth_stage"].get("latest_observation"),
                    "warnings": data["warnings"],
                }
            )
    print(json.dumps({"query_date": date.today().isoformat(), "analyses": summaries}, indent=2))


if __name__ == "__main__":
    main()

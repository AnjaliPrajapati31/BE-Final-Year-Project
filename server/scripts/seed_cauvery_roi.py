from __future__ import annotations

import json
import sys
from pathlib import Path

import psycopg
from shapely.geometry import mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services.sickle.geometry import load_roi


def main() -> None:
    if not settings.DATABASE_URL:
        raise SystemExit("DATABASE_URL is required")
    path = settings.path(settings.CAUVERY_ROI_PATH)
    roi, checksum = load_roi(path)
    geojson = json.dumps(mapping(roi), separators=(",", ":"))
    manifest_path = path.with_name("manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("sha256") != checksum:
        raise RuntimeError("ROI manifest checksum does not match the GeoJSON")
    with psycopg.connect(settings.DATABASE_URL) as connection, connection.transaction():
        connection.execute("UPDATE supported_regions SET active=FALSE WHERE code=%s", (settings.CAUVERY_ROI_CODE,))
        connection.execute(
            """INSERT INTO supported_regions(code,name,version,geometry,active,source,source_checksum,metadata)
            VALUES (%s,%s,%s,ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)),TRUE,%s,%s,%s::jsonb)
            ON CONFLICT(code,version) DO UPDATE SET geometry=excluded.geometry,active=TRUE,source=excluded.source,source_checksum=excluded.source_checksum,metadata=excluded.metadata""",
            (settings.CAUVERY_ROI_CODE, manifest["name"], settings.CAUVERY_ROI_VERSION, geojson, manifest["source"], checksum, json.dumps(manifest)),
        )
    print(f"seeded {settings.CAUVERY_ROI_CODE} v{settings.CAUVERY_ROI_VERSION} ({checksum})")


if __name__ == "__main__":
    main()

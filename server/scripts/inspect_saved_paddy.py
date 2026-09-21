"""Find the best existing stored Paddy analysis without writing to PostGIS.

Run from the server directory:
    uv run python scripts/inspect_saved_paddy.py

The script deliberately creates nothing. It tells you whether a usable Paddy
run already exists and prints the exact dashboard path for opening its saved
charts and details.
"""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings


QUERY = """
    SELECT ar.request_id, f.field_code, ar.status, ar.started_at,
           cr.confidence, sr.stage,
           wb.water_deficit_mm, ia.action AS irrigation_action
    FROM analysis_runs ar
    JOIN field_revisions fr ON fr.id = ar.field_revision_id
    JOIN fields f ON f.id = fr.field_id
    JOIN crop_results cr ON cr.request_id = ar.request_id
    LEFT JOIN stage_results sr ON sr.request_id = ar.request_id
    LEFT JOIN water_balance_results wb ON wb.request_id = ar.request_id
    LEFT JOIN irrigation_advisory_results ia ON ia.request_id = ar.request_id
    WHERE ar.status IN ('completed', 'partial')
      AND cr.class_label = 'Paddy'
    ORDER BY
      (ia.action IS NOT NULL) DESC,
      (wb.water_deficit_mm IS NOT NULL) DESC,
      cr.confidence DESC NULLS LAST,
      ar.started_at DESC
    LIMIT 1
"""


def main() -> None:
    if not settings.DATABASE_URL:
        raise SystemExit("DATABASE_URL is not configured. Set it in server/.env first.")
    try:
        with psycopg.connect(settings.DATABASE_URL, connect_timeout=settings.DATABASE_CONNECT_TIMEOUT_SECONDS, row_factory=dict_row) as connection:
            row = connection.execute(QUERY).fetchone()
    except psycopg.Error as exc:
        raise SystemExit(f"Could not inspect saved analyses: {exc.__class__.__name__}.") from exc

    if row is None:
        print("No completed or partial Paddy analysis is stored yet.")
        print("Run one real Paddy field analysis; this script does not generate placeholder scientific results.")
        return

    print("Best available stored Paddy analysis")
    print(f"Field: {row['field_code']}")
    print(f"Run: {row['request_id']}")
    print(f"Status: {row['status']}")
    print(f"Started: {row['started_at']}")
    print(f"Crop confidence: {row['confidence']}")
    print(f"Growth stage: {row['stage'] or 'Not available'}")
    print(f"Water deficit: {row['water_deficit_mm'] if row['water_deficit_mm'] is not None else 'Not available'} mm")
    print(f"Irrigation action: {row['irrigation_action'] or 'Not available'}")
    print("Open in the frontend:")
    print(f"/dashboard?requestId={row['request_id']}&fieldId={row['field_code']}")


if __name__ == "__main__":
    main()

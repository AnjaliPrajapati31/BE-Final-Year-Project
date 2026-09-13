from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import BASE_DIR, settings


def _can_adopt_stress_migration(connection, filename: str) -> bool:
    """Recognize a verified 0004 schema that predates the migration ledger row."""
    if filename != "0004_add_stress_results.sql":
        return False
    table_exists = connection.execute(
        "SELECT to_regclass('public.stress_results') IS NOT NULL"
    ).fetchone()[0]
    column_exists = connection.execute(
        """SELECT EXISTS (
               SELECT 1 FROM information_schema.columns
               WHERE table_schema='public' AND table_name='analysis_runs'
                 AND column_name='stress_rule_version'
           )"""
    ).fetchone()[0]
    constraint = connection.execute(
        """SELECT pg_get_constraintdef(oid) FROM pg_constraint
           WHERE conrelid='analysis_runs'::regclass
             AND conname='analysis_runs_status_check'"""
    ).fetchone()
    return bool(table_exists and column_exists and constraint and "running_stress_rules" in constraint[0])


def main() -> None:
    if not settings.DATABASE_URL:
        raise SystemExit("DATABASE_URL is required")
    migration_dir = BASE_DIR / "migrations"
    with psycopg.connect(settings.DATABASE_URL, autocommit=True) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations(filename TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        for path in sorted(migration_dir.glob("*.sql")):
            raw = path.read_bytes()
            checksum = hashlib.sha256(raw).hexdigest()
            row = connection.execute("SELECT checksum FROM schema_migrations WHERE filename=%s", (path.name,)).fetchone()
            if row:
                if row[0] != checksum:
                    raise RuntimeError(f"Applied migration checksum changed: {path.name}")
                continue
            if _can_adopt_stress_migration(connection, path.name):
                connection.execute(
                    "INSERT INTO schema_migrations(filename,checksum) VALUES (%s,%s)",
                    (path.name, checksum),
                )
                print(f"adopted {path.name} (verified existing schema)")
                continue
            with connection.transaction():
                connection.execute(raw.decode("utf-8"))
                connection.execute("INSERT INTO schema_migrations(filename,checksum) VALUES (%s,%s)", (path.name, checksum))
            print(f"applied {path.name}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import BASE_DIR, settings


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
            with connection.transaction():
                connection.execute(raw.decode("utf-8"))
                connection.execute("INSERT INTO schema_migrations(filename,checksum) VALUES (%s,%s)", (path.name, checksum))
            print(f"applied {path.name}")


if __name__ == "__main__":
    main()

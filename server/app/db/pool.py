from __future__ import annotations

from psycopg_pool import ConnectionPool


class Database:
    def __init__(self, url: str, min_size: int, max_size: int, timeout: int):
        self.timeout = timeout
        self.pool = ConnectionPool(
            conninfo=url,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            open=False,
            kwargs={"autocommit": False, "connect_timeout": timeout},
        )

    def open(self) -> None:
        self.pool.open(wait=True, timeout=self.timeout)

    def close(self) -> None:
        self.pool.close()

    def check(self) -> dict:
        with self.pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_Version()")
            return {"postgis_version": cursor.fetchone()[0]}

import os

import psycopg
import pytest

from app.config import settings

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def connection():
    url = os.getenv("TEST_DATABASE_URL") or settings.DATABASE_URL
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    with psycopg.connect(url) as value:
        yield value


def test_postgis_covers_boundary_but_rejects_outside(connection):
    row = connection.execute(
        """WITH roi AS (SELECT ST_MakeEnvelope(78,10,80,12,4326) AS g)
        SELECT ST_Covers(g,ST_MakeEnvelope(78,10,78.1,10.1,4326)),
               ST_Covers(g,ST_MakeEnvelope(79,11,79.1,11.1,4326)),
               ST_Covers(g,ST_MakeEnvelope(79.9,11.9,80.1,12.1,4326)) FROM roi"""
    ).fetchone()
    assert row == (True, True, False)


def test_required_gist_index_exists_after_migration(connection):
    row = connection.execute("SELECT 1 FROM pg_indexes WHERE indexname='supported_regions_geometry_gist'").fetchone()
    assert row == (1,)

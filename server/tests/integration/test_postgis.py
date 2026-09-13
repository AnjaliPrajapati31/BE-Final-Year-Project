import os
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from app.config import settings
from app.core.exceptions import DomainError
from app.db.repositories import AnalysisRepository

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


def test_water_migrations_are_recorded_and_tables_exist(connection):
    names = {row[0] for row in connection.execute("SELECT filename FROM schema_migrations").fetchall()}
    assert {
        "0004_add_stress_results.sql", "0005_add_water_platform.sql",
        "0006_add_analysis_payloads.sql", "0007_extend_canonical_payloads.sql",
        "0008_version_field_revision_by_roi.sql",
        "0009_add_canonical_chart_payload.sql",
        "0010_add_field_water_observations.sql", "0011_extend_weather_provenance.sql",
        "0012_add_analysis_explanations.sql",
    } <= names
    for table in ("analysis_module_runs", "irrigation_events", "weather_daily", "water_balance_results",
                  "irrigation_advisory_results", "field_water_observations", "irrigation_history_coverage",
                  "analysis_explanations"):
        assert connection.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[0] == table


def test_irrigation_events_are_geometry_bound_auditable_and_deduplicated(connection):
    class RollbackFixture(Exception):
        pass

    class SameConnectionPool:
        @contextmanager
        def connection(self):
            yield connection

    field_code = f"IRR_TEST_{uuid4().hex[:10]}"
    try:
        try:
            with connection.transaction():
                roi_id = connection.execute("SELECT id FROM supported_regions WHERE active=TRUE LIMIT 1").fetchone()[0]
                field_id = connection.execute("INSERT INTO fields(field_code) VALUES (%s) RETURNING id", (field_code,)).fetchone()[0]
                revision_id = connection.execute(
                    """INSERT INTO field_revisions(field_id,revision_number,geometry,geometry_hash,patch_footprint,
                       area_m2,width_m,height_m,field_pixel_count,roi_id)
                       VALUES (%s,1,ST_Multi(ST_MakeEnvelope(79.3,10.8,79.301,10.801,4326)),%s,
                       ST_MakeEnvelope(79.2995,10.7995,79.3015,10.8015,4326),10000,110,110,100,%s) RETURNING id""",
                    (field_id, uuid4().hex, roi_id),
                ).fetchone()[0]
                repository = AnalysisRepository(SameConnectionPool(), settings.CAUVERY_ROI_CODE)
                event = {
                    "event_date": date(2025, 7, 1), "amount": 10.0, "unit": "m3",
                    "irrigation_method": "surface", "application_efficiency": 0.6, "source": "user",
                    "client_event_id": "submission-1", "supersedes_event_id": None, "correction_reason": None,
                }
                created = repository.create_irrigation_event(field_code, event)
                assert created["field_revision_id"] == revision_id
                assert created["gross_depth_mm"] == pytest.approx(1.0)
                assert created["net_depth_mm"] == pytest.approx(0.6)
                with pytest.raises(DomainError) as duplicate:
                    repository.create_irrigation_event(field_code, event)
                assert duplicate.value.code == "DUPLICATE_IRRIGATION_EVENT"
                second_revision = connection.execute(
                    """INSERT INTO field_revisions(field_id,revision_number,geometry,geometry_hash,patch_footprint,
                       area_m2,width_m,height_m,field_pixel_count,roi_id)
                       VALUES (%s,2,ST_Multi(ST_MakeEnvelope(79.3,10.8,79.301,10.801,4326)),%s,
                       ST_MakeEnvelope(79.2995,10.7995,79.3015,10.8015,4326),10000,110,110,100,%s) RETURNING id""",
                    (field_id, uuid4().hex, roi_id),
                ).fetchone()[0]
                before_correction = repository.list_irrigation_events(field_code)
                assert before_correction[0]["field_revision_id"] == revision_id
                correction = repository.create_irrigation_event(field_code, {
                    **event, "amount": 20.0, "client_event_id": "submission-2",
                    "supersedes_event_id": created["id"], "correction_reason": "meter reading corrected",
                })
                assert correction["field_revision_id"] == second_revision
                history = repository.list_irrigation_events(field_code)
                assert [item["status"] for item in history] == ["voided", "active"]
                repository.void_irrigation_event(field_code, correction["id"], "entry withdrawn")
                assert repository.list_irrigation_events(field_code)[-1]["status"] == "voided"
                raise RollbackFixture()
        except RollbackFixture:
            pass
    finally:
        connection.rollback()


def test_water_observations_and_history_coverage_are_audited(connection):
    class RollbackFixture(Exception):
        pass

    class SameConnectionPool:
        @contextmanager
        def connection(self):
            yield connection

    field_code = f"WATER_OBS_{uuid4().hex[:10]}"
    try:
        try:
            with connection.transaction():
                roi_id = connection.execute("SELECT id FROM supported_regions WHERE active=TRUE LIMIT 1").fetchone()[0]
                field_id = connection.execute("INSERT INTO fields(field_code) VALUES (%s) RETURNING id", (field_code,)).fetchone()[0]
                revision_id = connection.execute(
                    """INSERT INTO field_revisions(field_id,revision_number,geometry,geometry_hash,patch_footprint,
                       area_m2,width_m,height_m,field_pixel_count,roi_id)
                       VALUES (%s,1,ST_Multi(ST_MakeEnvelope(79.3,10.8,79.301,10.801,4326)),%s,
                       ST_MakeEnvelope(79.2995,10.7995,79.3015,10.8015,4326),10000,110,110,100,%s) RETURNING id""",
                    (field_id, uuid4().hex, roi_id),
                ).fetchone()[0]
                repository = AnalysisRepository(SameConnectionPool(), settings.CAUVERY_ROI_CODE)
                observed_at = datetime(2025, 7, 1, 3, tzinfo=timezone.utc)
                observation = {
                    "observed_at": observed_at, "observation_type": "ponded_depth", "value": 25.0,
                    "unit": "mm", "measurement_depth_m": None, "method": "field ruler", "source": "user",
                    "reliability": "high", "client_observation_id": "obs-1",
                    "supersedes_observation_id": None, "correction_reason": None,
                }
                created = repository.create_water_observation(field_code, observation)
                assert created["field_revision_id"] == revision_id
                assert created["ponded_depth_mm"] == 25
                with pytest.raises(DomainError) as duplicate:
                    repository.create_water_observation(field_code, observation)
                assert duplicate.value.code == "DUPLICATE_WATER_OBSERVATION"
                corrected = repository.create_water_observation(field_code, {
                    **observation, "value": 20.0, "client_observation_id": "obs-2",
                    "supersedes_observation_id": created["id"], "correction_reason": "ruler reread",
                })
                assert [row["status"] for row in repository.list_water_observations(field_code)] == ["voided", "active"]
                repository.void_water_observation(field_code, corrected["id"], "measurement withdrawn")
                coverage = repository.save_irrigation_history_coverage(field_code, {
                    "coverage_start": date(2025, 6, 1), "coverage_end": date(2025, 7, 31),
                    "coverage_status": "complete", "source": "measured", "notes": "field log checked",
                })
                assert coverage["field_revision_id"] == revision_id
                assert repository.irrigation_history_complete(field_code, date(2025, 6, 1), date(2025, 7, 1))
                repository.save_irrigation_history_coverage(field_code, {
                    "coverage_start": None, "coverage_end": None, "coverage_status": "unknown",
                    "source": "user", "notes": None,
                })
                assert not repository.irrigation_history_complete(field_code, date(2025, 6, 1), date(2025, 7, 1))
                raise RollbackFixture()
        except RollbackFixture:
            pass
    finally:
        connection.rollback()


def test_all_migrations_build_a_fresh_schema_transactionally(connection):
    class RollbackFixture(Exception):
        pass

    schema_name = f"migration_test_{uuid4().hex[:12]}"
    migration_root = Path(__file__).parents[2] / "migrations"
    try:
        try:
            with connection.transaction():
                connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
                connection.execute(sql.SQL("SET LOCAL search_path TO {}, public").format(sql.Identifier(schema_name)))
                for migration in sorted(migration_root.glob("*.sql")):
                    connection.execute(migration.read_text(encoding="utf-8"))
                expected = {
                    "supported_regions", "fields", "field_revisions", "analysis_runs", "crop_results",
                    "stage_results", "stress_results", "analysis_module_runs", "irrigation_events",
                    "weather_daily", "water_balance_results", "water_balance_daily",
                    "irrigation_advisory_results", "analysis_result_payloads",
                    "field_water_observations", "irrigation_history_coverage", "analysis_explanations",
                }
                rows = connection.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema=%s", (schema_name,)
                ).fetchall()
                assert expected <= {row[0] for row in rows}
                raise RollbackFixture()
        except RollbackFixture:
            pass
    finally:
        connection.rollback()

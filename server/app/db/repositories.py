from __future__ import annotations

import json
from uuid import UUID

from psycopg.rows import dict_row

from app.core.exceptions import DomainError
from app.services.sickle.geometry import ValidatedGeometry
from app.services.water.contracts import IrrigationDepth
from app.services.water.irrigation import normalize_irrigation


class AnalysisRepository:
    def __init__(self, pool, roi_code: str):
        self.pool = pool
        self.roi_code = roi_code

    def verify_roi(self, field_json: str, patch_json: str) -> UUID:
        sql = """
            SELECT id FROM supported_regions
            WHERE code = %s AND active = TRUE AND ST_IsValid(geometry)
              AND ST_Covers(geometry, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
              AND ST_Covers(geometry, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
        """
        with self.pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(sql, (self.roi_code, field_json, patch_json))
            row = cursor.fetchone()
        if not row:
            raise DomainError("OUTSIDE_SUPPORTED_ROI", "This field is outside the supported Cauvery Delta pilot region.")
        return row[0]

    def active_roi(self) -> dict | None:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT id, code, version, source_checksum FROM supported_regions WHERE code=%s AND active=TRUE", (self.roi_code,))
            return cursor.fetchone()

    def schema_readiness(self) -> dict:
        required_tables = (
            "analysis_runs", "stress_results", "analysis_module_runs", "irrigation_events",
            "weather_daily", "water_balance_results", "water_balance_daily",
            "irrigation_advisory_results", "analysis_result_payloads",
        )
        with self.pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT filename FROM schema_migrations WHERE filename IN (%s,%s,%s,%s,%s,%s)",
                ("0004_add_stress_results.sql", "0005_add_water_platform.sql",
                 "0006_add_analysis_payloads.sql", "0007_extend_canonical_payloads.sql",
                 "0008_version_field_revision_by_roi.sql", "0009_add_canonical_chart_payload.sql"),
            )
            migrations = {row[0] for row in cursor.fetchall()}
            cursor.execute(
                "SELECT to_regclass('public.' || name) FROM unnest(%s::text[]) AS name",
                (list(required_tables),),
            )
            existing = {str(row[0]) for row in cursor.fetchall() if row[0] is not None}
        missing_tables = sorted(set(required_tables) - existing)
        missing_migrations = sorted({
            "0004_add_stress_results.sql", "0005_add_water_platform.sql",
            "0006_add_analysis_payloads.sql", "0007_extend_canonical_payloads.sql",
            "0008_version_field_revision_by_roi.sql",
            "0009_add_canonical_chart_payload.sql",
        } - migrations)
        return {
            "ready": not missing_tables and not missing_migrations,
            "missing_tables": missing_tables,
            "missing_migrations": missing_migrations,
        }

    def create_revision_and_run(self, field_code: str, geometry: ValidatedGeometry, roi_id: UUID, run: dict) -> tuple[UUID, UUID]:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO fields(field_code) VALUES (%s) ON CONFLICT(field_code) DO UPDATE SET updated_at=now() RETURNING id",
                (field_code,),
            )
            field_id = cursor.fetchone()[0]
            cursor.execute(
                "SELECT id FROM field_revisions WHERE field_id=%s AND geometry_hash=%s AND roi_id=%s",
                (field_id, geometry.geometry_hash, roi_id),
            )
            row = cursor.fetchone()
            if row:
                revision_id = row[0]
            else:
                cursor.execute("SELECT COALESCE(MAX(revision_number),0)+1 FROM field_revisions WHERE field_id=%s", (field_id,))
                revision_number = cursor.fetchone()[0]
                cursor.execute(
                    """INSERT INTO field_revisions(field_id,revision_number,geometry,geometry_hash,patch_footprint,area_m2,width_m,height_m,field_pixel_count,roi_id)
                    VALUES (%s,%s,ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)),%s,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s,%s,%s,%s,%s) RETURNING id""",
                    (field_id, revision_number, geometry.geometry_json, geometry.geometry_hash, geometry.patch_json, geometry.area_m2, geometry.width_m, geometry.height_m, run["field_pixel_count"], roi_id),
                )
                revision_id = cursor.fetchone()[0]
            cursor.execute(
                """INSERT INTO analysis_runs(request_id,field_revision_id,status,provider,provider_live_data,provider_cached,year,season,model_name,checkpoint_sha256,preprocessing_version,stage_rule_version,stress_rule_version)
                VALUES (%s,%s,'pending',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (run["request_id"], revision_id, run["provider"], run["live_data"], run["cached"], run["year"], run["season"], run["model_name"], run["checkpoint_sha256"], run["preprocessing_version"], run["stage_rule_version"], run.get("stress_rule_version", "provisional-cauvery-v1")),
            )
        return field_id, revision_id

    def set_status(self, request_id: UUID, status: str, *, error_code: str | None = None, error_message: str | None = None, warnings: list | None = None, quality: dict | None = None) -> None:
        completed = status in {"completed", "partial", "failed"}
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                "UPDATE analysis_runs SET status=%s,error_code=%s,error_message=%s,warnings=%s::jsonb,quality_metadata=%s::jsonb,completed_at=CASE WHEN %s THEN now() ELSE completed_at END WHERE request_id=%s",
                (status, error_code, error_message, json.dumps(warnings or []), json.dumps(quality or {}), completed, request_id),
            )

    def set_provider_cached(self, request_id: UUID, cached: bool) -> None:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("UPDATE analysis_runs SET provider_cached=%s WHERE request_id=%s", (cached, request_id))

    def save_crop(self, request_id: UUID, result: dict) -> None:
        values = (request_id,result["class_code"],result["class_label"],result["confidence"],result["paddy_probability"],result["non_paddy_probability"],result["paddy_pixel_fraction"],result["non_paddy_pixel_fraction"],result["field_pixel_count"],result["s1_observation_count"],result["s2_observation_count"],json.dumps({"S1":result["s1_months_used"],"S2":result["s2_months_used"]}),json.dumps(result.get("rejected_months",{})),True)
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("""INSERT INTO crop_results(request_id,class_code,class_label,confidence,paddy_probability,non_paddy_probability,paddy_pixel_fraction,non_paddy_pixel_fraction,field_pixel_count,s1_observation_count,s2_observation_count,used_months,rejected_months,experimental)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)""", values)

    def save_observations(self, request_id: UUID, observations: list, purpose: str) -> None:
        sql = """INSERT INTO satellite_observations(request_id,sensor,observation_date,source_image_id,purpose,accepted,valid_pixel_count,valid_pixel_fraction,zero_fraction,vv,vh,vv_minus_vh,ndvi,ndmi,ndwi,orbit_pass,orbit_number,scene_cloud_percentage,metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)"""
        rows = []
        for item in observations:
            values = item.values
            rows.append((request_id,item.sensor,item.date,item.source_image_id,purpose,True,values.get("valid_pixel_count") or values.get("VV_count") or values.get("NDVI_count"),values.get("valid_pixel_fraction"),values.get("zero_fraction"),values.get("VV_median"),values.get("VH_median"),values.get("VV_minus_VH_median"),values.get("NDVI_median"),values.get("NDMI_median"),values.get("NDWI_median"),values.get("orbit_pass") or values.get("orbitProperties_pass"),values.get("orbit_number") or values.get("relativeOrbitNumber_start"),values.get("scene_cloud_percentage"),json.dumps(values)))
        if rows:
            with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
                cursor.executemany(sql, rows)

    def save_crop_quality(self, request_id: UUID, quality: list) -> None:
        rows = [(request_id,item.sensor,item.month,"crop",item.accepted,item.rejection_reason,item.valid_pixel_count,item.valid_pixel_fraction,item.zero_fraction,json.dumps({"day_position":item.day_position,"source_ids":item.source_ids})) for item in quality]
        if rows:
            with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO satellite_observations(request_id,sensor,observation_month,purpose,accepted,rejection_reason,valid_pixel_count,valid_pixel_fraction,zero_fraction,metadata)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                    rows,
                )

    def save_artifact(self, request_id: UUID, artifact: dict) -> None:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO analysis_artifacts(request_id,artifact_type,relative_path,mime_type,size_bytes,sha256) VALUES (%s,%s,%s,%s,%s,%s)",
                (request_id, artifact["type"], artifact["relative_path"], artifact["mime_type"], artifact["size"], artifact["sha256"]),
            )

    def get_artifact(self, request_id: UUID, artifact_type: str) -> dict | None:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT artifact_type,relative_path,mime_type,size_bytes,sha256 FROM analysis_artifacts WHERE request_id=%s AND artifact_type=%s", (request_id, artifact_type))
            return cursor.fetchone()

    def save_stage(self, request_id: UUID, result: dict) -> None:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO stage_results(request_id,status,reason_code,provisional,stage,evidence,cycle_start,latest_observation,current_cycle_count,current_cycle_span_days,latest_ndvi,latest_ndmi,peak_confirmed,maximum_interpretation,selected_s1_orbit_pass,selected_s1_orbit_number,clean_s1_observation_count,clean_s2_observation_count,warning)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (request_id,result.get("status"),result.get("reason_code"),result.get("provisional",True),result.get("stage"),result.get("evidence"),result.get("cycle_start"),result.get("latest_observation"),result.get("current_cycle_count"),result.get("current_cycle_span_days"),result.get("latest_ndvi"),result.get("latest_ndmi"),result.get("peak_confirmed",False),result.get("maximum_interpretation"),result.get("selected_s1_orbit_pass"),result.get("selected_s1_orbit_number"),result.get("clean_s1_observation_count",0),result.get("clean_s2_observation_count",0),result.get("warning")),
            )

    def save_stress(self, request_id: UUID, result: dict) -> None:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO stress_results(
                    request_id,status,reason_code,provisional,
                    stress_risk,stress_score,latest_observation_date,persistence_observations,
                    stage_context,stage_evidence,evidence,counter_evidence,warning,stress_rule_version
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)""",
                (
                    request_id,
                    result.get("status"),
                    result.get("reason_code"),
                    result.get("provisional", True),
                    result.get("stress_risk"),
                    result.get("stress_score"),
                    result.get("latest_observation_date"),
                    result.get("persistence_observations"),
                    result.get("stage_context"),
                    result.get("stage_evidence"),
                    json.dumps(result.get("evidence", [])),
                    json.dumps(result.get("counter_evidence", [])),
                    result.get("warning"),
                    result.get("stress_rule_version", "provisional-cauvery-v1"),
                ),
            )
            marker_dates = [
                row["date"] for row in result.get("chart_data", {}).get("optical", [])
                if row.get("stress_marker")
            ]
            if marker_dates:
                cursor.execute(
                    """UPDATE satellite_observations
                       SET metadata = metadata || '{\"stress_marker\": true}'::jsonb
                       WHERE request_id=%s AND sensor='S2'
                         AND observation_date = ANY(%s::date[])""",
                    (request_id, marker_dates),
                )

    def get_analysis(self, request_id: UUID) -> dict | None:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    ar.*,
                    f.field_code,
                    fr.revision_number, fr.geometry_hash, fr.area_m2, fr.width_m, fr.height_m,
                    ST_AsGeoJSON(fr.geometry)::jsonb AS geometry,
                    roi.version AS roi_version,
                    cr.class_code, cr.class_label, cr.confidence,
                    cr.paddy_probability, cr.non_paddy_probability,
                    cr.paddy_pixel_fraction, cr.non_paddy_pixel_fraction,
                    cr.field_pixel_count, cr.s1_observation_count, cr.s2_observation_count,
                    cr.used_months, cr.rejected_months, cr.experimental,
                    sr.status         AS stage_status,
                    sr.reason_code,
                    sr.provisional     AS stage_provisional,
                    sr.stage,
                    sr.evidence,
                    sr.cycle_start,
                    sr.latest_observation,
                    sr.current_cycle_count,
                    sr.current_cycle_span_days,
                    sr.latest_ndvi,
                    sr.latest_ndmi,
                    sr.peak_confirmed,
                    sr.maximum_interpretation,
                    sr.selected_s1_orbit_pass,
                    sr.selected_s1_orbit_number,
                    sr.clean_s1_observation_count,
                    sr.clean_s2_observation_count,
                    sr.warning        AS stage_warning,
                    stx.status        AS stress_status,
                    stx.reason_code   AS stress_reason_code,
                    stx.provisional   AS stress_provisional,
                    stx.stress_risk,
                    stx.stress_score,
                    stx.latest_observation_date AS stress_latest_obs,
                    stx.persistence_observations,
                    stx.stage_context,
                    stx.stage_evidence AS stress_stage_evidence,
                    stx.evidence      AS stress_evidence,
                    stx.counter_evidence AS stress_counter_evidence,
                    stx.warning       AS stress_warning,
                    stx.stress_rule_version
                FROM analysis_runs ar
                JOIN field_revisions fr ON fr.id = ar.field_revision_id
                JOIN fields f          ON f.id  = fr.field_id
                JOIN supported_regions roi ON roi.id = fr.roi_id
                LEFT JOIN crop_results  cr  ON cr.request_id  = ar.request_id
                LEFT JOIN stage_results sr  ON sr.request_id  = ar.request_id
                LEFT JOIN stress_results stx ON stx.request_id = ar.request_id
                WHERE ar.request_id = %s
                """,
                (request_id,),
            )
            return cursor.fetchone()

    def get_stage_chart(self, request_id: UUID) -> list[dict]:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT observation_date AS date,ndvi,ndmi,ndwi FROM satellite_observations WHERE request_id=%s AND sensor='S2' AND purpose IN ('stage','both') AND accepted=TRUE ORDER BY observation_date", (request_id,))
            return list(cursor.fetchall())

    def get_stress_chart(self, request_id: UUID) -> dict:
        """Return optical and radar time-series arrays for the stress chart on stored-retrieval."""
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """SELECT observation_date AS date,ndvi,ndmi,ndwi,
                          COALESCE((metadata->>'stress_marker')::boolean,FALSE) AS stress_marker
                   FROM satellite_observations
                   WHERE request_id=%s AND sensor='S2' AND purpose IN ('stage','both') AND accepted=TRUE
                   ORDER BY observation_date""",
                (request_id,),
            )
            optical = list(cursor.fetchall())
            cursor.execute(
                """SELECT observation_date AS date,vv,vh,vv_minus_vh
                   FROM satellite_observations
                   WHERE request_id=%s AND sensor='S1' AND purpose IN ('stage','both') AND accepted=TRUE
                   ORDER BY observation_date""",
                (request_id,),
            )
            radar = list(cursor.fetchall())
        return {"optical": optical, "radar": radar}

    def list_artifacts(self, request_id: UUID) -> list[dict]:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT artifact_type,mime_type,size_bytes,sha256 FROM analysis_artifacts WHERE request_id=%s ORDER BY artifact_type", (request_id,))
            return list(cursor.fetchall())

    def history(self, field_code: str, limit: int, offset: int) -> list[dict]:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""SELECT ar.request_id,ar.status,ar.started_at,ar.completed_at,fr.revision_number,cr.class_label,cr.confidence,sr.stage,sr.evidence FROM fields f JOIN field_revisions fr ON fr.field_id=f.id JOIN analysis_runs ar ON ar.field_revision_id=fr.id LEFT JOIN crop_results cr ON cr.request_id=ar.request_id LEFT JOIN stage_results sr ON sr.request_id=ar.request_id WHERE f.field_code=%s AND ar.status IN ('completed','partial') ORDER BY ar.started_at DESC LIMIT %s OFFSET %s""", (field_code, limit, offset))
            return list(cursor.fetchall())

    def save_module_run(self, request_id: UUID, module: str, result: dict) -> None:
        warnings = result.get("warnings") or ([result["warning"]] if result.get("warning") else [])
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO analysis_module_runs(request_id,module,status,provisional,evidence_level,reason_code,warnings,input_sources,rule_version,metadata)
                   VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s::jsonb)
                   ON CONFLICT(request_id,module) DO UPDATE SET status=EXCLUDED.status,
                   provisional=EXCLUDED.provisional,evidence_level=EXCLUDED.evidence_level,
                   reason_code=EXCLUDED.reason_code,warnings=EXCLUDED.warnings,
                   input_sources=EXCLUDED.input_sources,rule_version=EXCLUDED.rule_version,
                   metadata=EXCLUDED.metadata,completed_at=now()""",
                (request_id, module, result["status"], result.get("provisional", False),
                 result.get("evidence_level"), result.get("reason_code"), json.dumps(warnings),
                 json.dumps(result.get("input_sources", [])), result.get("rule_version"),
                 json.dumps(result.get("metadata", {}))),
            )

    def get_module_runs(self, request_id: UUID) -> dict[str, dict]:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """SELECT module,status,provisional,evidence_level,reason_code,warnings,input_sources,rule_version
                   FROM analysis_module_runs WHERE request_id=%s ORDER BY module""", (request_id,)
            )
            return {row["module"]: {key: value for key, value in row.items() if key != "module"} for row in cursor.fetchall()}

    def _current_field_revision(self, cursor, field_code: str) -> dict | None:
        cursor.execute(
            """SELECT f.id AS field_id,fr.id AS revision_id,fr.area_m2,fr.revision_number
               FROM fields f JOIN field_revisions fr ON fr.field_id=f.id
               WHERE f.field_code=%s ORDER BY fr.revision_number DESC LIMIT 1""", (field_code,)
        )
        row = cursor.fetchone()
        return None if row is None else dict(row)

    def save_water_profile(self, field_code: str, profile_version: str, overrides: dict, source: str) -> dict:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor(row_factory=dict_row) as cursor:
            field = self._current_field_revision(cursor, field_code)
            if field is None:
                raise DomainError("FIELD_NOT_FOUND", "Field has no accepted geometry revision.", 404)
            cursor.execute(
                """INSERT INTO field_water_profiles(field_id,profile_version,overrides,source)
                   VALUES (%s,%s,%s::jsonb,%s) ON CONFLICT(field_id) DO UPDATE SET
                   profile_version=EXCLUDED.profile_version,overrides=EXCLUDED.overrides,
                   source=EXCLUDED.source,updated_at=now() RETURNING *""",
                (field["field_id"], profile_version, json.dumps(overrides), source),
            )
            return dict(cursor.fetchone())

    def get_water_profile(self, field_code: str) -> dict | None:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """SELECT p.* FROM fields f JOIN field_water_profiles p ON p.field_id=f.id
                   WHERE f.field_code=%s""", (field_code,)
            )
            row = cursor.fetchone()
            return None if row is None else dict(row)

    def create_irrigation_event(self, field_code: str, event: dict) -> dict:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor(row_factory=dict_row) as cursor:
            field = self._current_field_revision(cursor, field_code)
            if field is None:
                raise DomainError("FIELD_NOT_FOUND", "Field has no accepted geometry revision.", 404)
            if event.get("client_event_id"):
                cursor.execute("SELECT id FROM irrigation_events WHERE field_id=%s AND client_event_id=%s", (field["field_id"], event["client_event_id"]))
                if cursor.fetchone():
                    raise DomainError("DUPLICATE_IRRIGATION_EVENT", "This irrigation submission already exists.", 409)
            cursor.execute(
                """SELECT id FROM irrigation_events WHERE field_id=%s AND event_date=%s AND original_amount=%s
                   AND original_unit=%s AND irrigation_method=%s AND status='active'""",
                (field["field_id"], event["event_date"], event["amount"], event["unit"], event["irrigation_method"]),
            )
            if cursor.fetchone():
                raise DomainError("DUPLICATE_IRRIGATION_EVENT", "An identical active irrigation event already exists.", 409)
            amount = float(event["amount"])
            gross_depth, net_depth = normalize_irrigation(amount, event["unit"], field["area_m2"], event["application_efficiency"])
            supersedes = event.get("supersedes_event_id")
            if supersedes:
                cursor.execute("SELECT id,status FROM irrigation_events WHERE id=%s AND field_id=%s FOR UPDATE", (supersedes, field["field_id"]))
                prior = cursor.fetchone()
                if prior is None or prior["status"] != "active":
                    raise DomainError("IRRIGATION_EVENT_NOT_CORRECTABLE", "The referenced active irrigation event was not found.", 409)
                cursor.execute("UPDATE irrigation_events SET status='voided',voided_at=now(),correction_reason=%s WHERE id=%s", (event["correction_reason"], supersedes))
            cursor.execute(
                """INSERT INTO irrigation_events(field_id,field_revision_id,event_date,original_amount,original_unit,
                   gross_depth_mm,irrigation_method,application_efficiency,net_depth_mm,source,client_event_id,
                   supersedes_event_id,correction_reason) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   RETURNING *,%s::double precision AS field_area_m2,%s::integer AS field_revision_number""",
                (field["field_id"], field["revision_id"], event["event_date"], amount, event["unit"], gross_depth,
                 event["irrigation_method"], event["application_efficiency"], net_depth,
                 event["source"], event.get("client_event_id"), supersedes, event.get("correction_reason"),
                 field["area_m2"], field["revision_number"]),
            )
            return dict(cursor.fetchone())

    def list_irrigation_events(self, field_code: str, *, active_only: bool = False) -> list[dict]:
        suffix = " AND ie.status='active'" if active_only else ""
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """SELECT ie.*,fr.revision_number AS field_revision_number,fr.area_m2 AS field_area_m2
                   FROM fields f JOIN irrigation_events ie ON ie.field_id=f.id
                   JOIN field_revisions fr ON fr.id=ie.field_revision_id
                   WHERE f.field_code=%s""" + suffix + " ORDER BY ie.event_date,ie.created_at", (field_code,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def void_irrigation_event(self, field_code: str, event_id: UUID, reason: str) -> dict:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """UPDATE irrigation_events ie SET status='voided',voided_at=now(),correction_reason=%s
                   FROM fields f WHERE ie.id=%s AND ie.field_id=f.id AND f.field_code=%s AND ie.status='active'
                   RETURNING ie.*""", (reason, event_id, field_code),
            )
            row = cursor.fetchone()
            if row is None:
                raise DomainError("IRRIGATION_EVENT_NOT_FOUND", "Active irrigation event was not found.", 404)
            return dict(row)

    def irrigation_depths(self, field_code: str, start, end) -> list[IrrigationDepth]:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """SELECT ie.event_date,ie.net_depth_mm FROM fields f JOIN irrigation_events ie ON ie.field_id=f.id
                   WHERE f.field_code=%s AND ie.status='active' AND ie.event_date BETWEEN %s AND %s
                   ORDER BY ie.event_date""", (field_code, start, end),
            )
            return [IrrigationDepth(row["event_date"], row["net_depth_mm"]) for row in cursor.fetchall()]

    def save_weather(self, request_id: UUID, rows: list) -> None:
        values = [(request_id,row.date,row.kind,row.source,row.rainfall_mm,row.et0_mm,row.quality) for row in rows]
        if values:
            with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO weather_daily(request_id,weather_date,kind,source,rainfall_mm,et0_mm,quality)
                       VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(request_id,weather_date,kind) DO UPDATE SET
                       source=EXCLUDED.source,rainfall_mm=EXCLUDED.rainfall_mm,et0_mm=EXCLUDED.et0_mm,quality=EXCLUDED.quality""", values,
                )

    def save_water_balance(self, request_id: UUID, result: dict) -> None:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO water_balance_results(request_id,status,reason_code,provisional,evidence_level,rule_version,
                   profile_version,cycle_start,cycle_start_source,initial_state_source,as_of_date,water_deficit_mm,
                   water_deficit_low_mm,water_deficit_high_mm,root_depletion_mm,ponded_water_mm,total_available_water_mm,
                   readily_available_water_mm,cumulative_etc_mm,cumulative_rainfall_mm,cumulative_irrigation_mm,warnings,assumptions)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)""",
                (request_id,result["status"],result.get("reason_code"),result.get("provisional",True),result.get("evidence_level"),
                 result.get("rule_version"),result.get("profile_version"),result.get("cycle_start"),result.get("cycle_start_source"),
                 result.get("initial_state_source"),result.get("as_of_date"),result.get("water_deficit_mm"),result.get("water_deficit_low_mm"),
                 result.get("water_deficit_high_mm"),result.get("root_depletion_mm"),result.get("ponded_water_mm"),
                 result.get("total_available_water_mm"),result.get("readily_available_water_mm"),result.get("cumulative_etc_mm"),
                 result.get("cumulative_rainfall_mm"),result.get("cumulative_irrigation_mm"),json.dumps(result.get("warnings",[])),
                 json.dumps(result.get("assumptions",{}))),
            )
            cursor.executemany(
                "INSERT INTO water_balance_daily(request_id,balance_date,kind,values) VALUES (%s,%s,%s,%s::jsonb)",
                [(request_id,row["date"],row["kind"],json.dumps(row)) for row in result.get("daily",[])],
            )

    def save_advisory(self, request_id: UUID, result: dict) -> None:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO irrigation_advisory_results(request_id,status,action,reason_code,provisional,evidence_level,
                   rule_version,urgency,reason,net_depth_mm,gross_depth_mm,volume_m3,irrigation_efficiency,
                   forecast_rainfall_credited_mm,trigger_crossing_date,warnings)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                (request_id,result["status"],result["action"],result.get("reason_code"),result.get("provisional",True),
                 result.get("evidence_level"),result.get("rule_version"),result.get("urgency"),result.get("reason"),
                 result.get("net_depth_mm"),result.get("gross_depth_mm"),result.get("volume_m3"),result.get("irrigation_efficiency"),
                result.get("forecast_rainfall_credited_mm"),result.get("trigger_crossing_date"),json.dumps(result.get("warnings",[]))),
            )

    def save_result_payload(self, request_id: UUID, result_type: str, payload: dict) -> None:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO analysis_result_payloads(request_id,result_type,payload) VALUES (%s,%s,%s::jsonb)
                   ON CONFLICT(request_id,result_type) DO UPDATE SET payload=EXCLUDED.payload""",
                (request_id, result_type, json.dumps(payload, default=str)),
            )

    def get_result_payloads(self, request_id: UUID) -> dict[str, dict]:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT result_type,payload FROM analysis_result_payloads WHERE request_id=%s", (request_id,))
            return {row["result_type"]: row["payload"] for row in cursor.fetchall()}

    def get_water_results(self, request_id: UUID) -> dict:
        with self.pool.connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT result_type,payload FROM analysis_result_payloads WHERE request_id=%s", (request_id,))
            payloads = {row["result_type"]: row["payload"] for row in cursor.fetchall()}
            cursor.execute("SELECT * FROM weather_daily WHERE request_id=%s ORDER BY weather_date,kind", (request_id,))
            weather = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT * FROM water_balance_results WHERE request_id=%s", (request_id,))
            balance_row = cursor.fetchone()
            cursor.execute("SELECT values FROM water_balance_daily WHERE request_id=%s ORDER BY balance_date,kind", (request_id,))
            daily = [row["values"] for row in cursor.fetchall()]
            balance = None if balance_row is None else {**dict(balance_row), "daily": daily}
            cursor.execute("SELECT * FROM irrigation_advisory_results WHERE request_id=%s", (request_id,))
            advisory_row = cursor.fetchone()
        return {
            "weather": payloads.get("weather", weather or None),
            "water_balance": payloads.get("water_balance", balance),
            "irrigation_advisory": payloads.get("irrigation_advisory", None if advisory_row is None else dict(advisory_row)),
            "water_balance_daily": daily,
        }

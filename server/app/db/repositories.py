from __future__ import annotations

import json
from uuid import UUID

from psycopg.rows import dict_row

from app.core.exceptions import DomainError
from app.services.sickle.geometry import ValidatedGeometry


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

    def create_revision_and_run(self, field_code: str, geometry: ValidatedGeometry, roi_id: UUID, run: dict) -> tuple[UUID, UUID]:
        with self.pool.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO fields(field_code) VALUES (%s) ON CONFLICT(field_code) DO UPDATE SET updated_at=now() RETURNING id",
                (field_code,),
            )
            field_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM field_revisions WHERE field_id=%s AND geometry_hash=%s", (field_id, geometry.geometry_hash))
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
                    sr.provisional,
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
                """SELECT observation_date AS date,ndvi,ndmi,ndwi
                   FROM satellite_observations
                   WHERE request_id=%s AND sensor='S2' AND purpose IN ('stage','both') AND accepted=TRUE
                   ORDER BY observation_date""",
                (request_id,),
            )
            optical = [{**row, "stress_marker": False} for row in cursor.fetchall()]
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

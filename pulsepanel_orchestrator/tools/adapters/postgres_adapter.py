"""PostgreSQL Adapter — structured clinical data store.

Maps the orchestration layer's Python models to the PostgreSQL schema
defined in docker/postgres/init.sql. All 12 tables are supported.

Operations:
  - store_clinical_record(ClinicalRecord) → persists patient, visit, symptoms, vitals
  - store_labels(ClinicalLabel[], patient_id, visit_id) → persists labels, facts, risk_concepts
  - get_patient_history(patient_id) → loads historical visits, symptoms, vitals, labels
  - store_canonical_record(ClinicalRecord, labels) → persists the full JSON record
  - audit_log(...) → writes to the audit_log table
  - health_check()
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from ...errors import DbConnectionError
from ...models import ClinicalLabel, ClinicalRecord, Symptom, VitalSigns
from .base_adapter import BaseAdapter


class PostgresAdapter(BaseAdapter):
    """Read/write structured clinical data from PostgreSQL."""

    def __init__(self, dsn: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._dsn = dsn or self._settings.postgres_dsn
        self._conn = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        import psycopg

        try:
            self._conn = psycopg.connect(self._dsn)
            self._connected = True
        except Exception as exc:
            raise DbConnectionError(
                f"Cannot connect to PostgreSQL at {self._dsn}: {exc}",
                tool="PostgresAdapter",
                service="postgresql",
            ) from exc

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()
        self._conn = None
        self._connected = False

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def store_clinical_record(
        self, record: ClinicalRecord, patient_name: str | None = None
    ) -> dict[str, str]:
        """Persist a ClinicalRecord across patients, visits, symptoms, and vitals tables.

        Returns a dict of {table_name: inserted_uuid} for audit tracing.
        """
        self._require_connected()
        assert self._conn is not None

        ids: dict[str, str] = {}
        cursor = self._conn.cursor()

        try:
            # 1. Patient (upsert by external_id — record_id serves as external_id)
            cursor.execute(
                """
                INSERT INTO patients (external_id, name)
                VALUES (%s, %s)
                ON CONFLICT (external_id) DO UPDATE SET name = EXCLUDED.name
                RETURNING patient_id
                """,
                (record.record_id, patient_name or f"Patient_{record.patient_id}"),
            )
            patient_id = cursor.fetchone()[0]
            ids["patients"] = str(patient_id)

            # 2. Visit
            cursor.execute(
                """
                INSERT INTO visits (patient_id, notes, source)
                VALUES (%s, %s, %s)
                RETURNING visit_id
                """,
                (patient_id, record.query, record.source),
            )
            visit_id = cursor.fetchone()[0]
            ids["visits"] = str(visit_id)

            # 3. Symptoms
            for symptom in record.symptoms:
                cursor.execute(
                    """
                    INSERT INTO symptoms (visit_id, patient_id, name, duration, severity, source)
                    VALUES (%s, %s, %s, %s, %s, 'patient')
                    """,
                    (visit_id, patient_id, symptom.name, symptom.duration, symptom.severity),
                )

            # 4. Vitals
            vitals = record.vitals
            if vitals:
                self._store_vital(cursor, visit_id, patient_id, "SpO2", vitals.spo2, "%")
                self._store_vital(cursor, visit_id, patient_id, "HR", vitals.heart_rate, "bpm")
                self._store_vital(
                    cursor, visit_id, patient_id, "Temperature", vitals.temperature_c, "°C"
                )
                self._store_vital(
                    cursor, visit_id, patient_id, "BP_systolic", vitals.systolic_bp, "mmHg"
                )
                self._store_vital(
                    cursor, visit_id, patient_id, "BP_diastolic", vitals.diastolic_bp, "mmHg"
                )
                self._store_vital(
                    cursor, visit_id, patient_id, "RR", vitals.respiratory_rate, "breaths/min"
                )

            self._conn.commit()
        except Exception as exc:
            self._conn.rollback()
            raise DbConnectionError(
                f"Failed to store ClinicalRecord: {exc}",
                tool="PostgresAdapter",
                service="postgresql",
            ) from exc
        finally:
            cursor.close()

        ids["visit_id"] = str(visit_id)
        ids["patient_id"] = str(patient_id)
        return ids

    def store_labels(
        self,
        labels: list[ClinicalLabel],
        patient_id: str,
        visit_id: str,
    ) -> None:
        """Persist derived clinical labels, facts, and risk concepts."""
        self._require_connected()
        assert self._conn is not None

        cursor = self._conn.cursor()
        try:
            for lbl in labels:
                # Clinical label
                cursor.execute(
                    """
                    INSERT INTO clinical_labels
                        (patient_id, visit_id, label_name, source, rule_name, evidence)
                    VALUES (%s, %s, %s, 'clinical_rule', %s, %s)
                    RETURNING label_id
                    """,
                    (patient_id, visit_id, lbl.label, lbl.rule, json.dumps(lbl.evidence)),
                )
                label_id = cursor.fetchone()[0]

                # Clinical fact
                cursor.execute(
                    """
                    INSERT INTO clinical_facts (patient_id, visit_id, fact_text, source_label_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (patient_id, visit_id, lbl.fact, label_id),
                )

                # Risk concept
                cursor.execute(
                    """
                    INSERT INTO risk_concepts
                        (patient_id, visit_id, concept_name, risk_level, evidence)
                    VALUES (%s, %s, %s, 'moderate', %s)
                    """,
                    (patient_id, visit_id, lbl.risk_concept, json.dumps(lbl.evidence)),
                )

            self._conn.commit()
        except Exception as exc:
            self._conn.rollback()
            raise DbConnectionError(
                f"Failed to store labels: {exc}", tool="PostgresAdapter", service="postgresql"
            ) from exc
        finally:
            cursor.close()

    def store_canonical_record(
        self,
        record: ClinicalRecord,
        labels: list[ClinicalLabel],
        patient_id: str,
        visit_id: str,
    ) -> None:
        """Persist the full normalised record as JSON."""
        self._require_connected()
        assert self._conn is not None

        record_data = {
            "record_id": record.record_id,
            "patient_id": record.patient_id,
            "visit_id": record.visit_id,
            "query": record.query,
            "symptoms": [{"name": s.name, "severity": s.severity, "duration": s.duration} for s in record.symptoms],
            "vitals": {
                "spo2": record.vitals.spo2 if record.vitals else None,
                "heart_rate": record.vitals.heart_rate if record.vitals else None,
                "temperature_c": record.vitals.temperature_c if record.vitals else None,
                "systolic_bp": record.vitals.systolic_bp if record.vitals else None,
                "diastolic_bp": record.vitals.diastolic_bp if record.vitals else None,
            } if record.vitals else None,
            "source": record.source,
            "labels": [
                {"label": l.label, "fact": l.fact, "risk_concept": l.risk_concept, "rule": l.rule, "evidence": l.evidence}
                for l in labels
            ],
        }

        cursor = self._conn.cursor()
        try:
            # record_id is auto-generated UUID; store the string record_id in the JSON data
            cursor.execute(
                """
                INSERT INTO canonical_records (patient_id, visit_id, record_data)
                VALUES (%s, %s, %s)
                """,
                (patient_id, visit_id, json.dumps(record_data)),
            )
            self._conn.commit()
        except Exception as exc:
            self._conn.rollback()
            raise DbConnectionError(
                f"Failed to store canonical record: {exc}",
                tool="PostgresAdapter",
                service="postgresql",
            ) from exc
        finally:
            cursor.close()

    def write_audit_log(
        self,
        action: str,
        table_name: str | None = None,
        record_id: str | None = None,
        patient_id: str | None = None,
        description: str | None = None,
    ) -> None:
        """Write an entry to the audit_log table (best-effort, no crash if table missing)."""
        self._require_connected()
        assert self._conn is not None

        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO audit_log (action, table_name, record_id, patient_id, description)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (action, table_name, record_id, patient_id, description),
            )
            self._conn.commit()
        except Exception as exc:
            self._conn.rollback()
            logger = logging.getLogger("pulsepanel.orchestrator")
            logger.warning("Audit log write failed (table may not exist): %s", exc)
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_patient_history(
        self, patient_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Load recent visits for a patient with symptoms and vitals."""
        self._require_connected()
        assert self._conn is not None

        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                SELECT v.visit_id, v.visit_date, v.notes, v.source,
                       json_agg(DISTINCT jsonb_build_object(
                           'name', s.name, 'severity', s.severity, 'duration', s.duration
                       )) FILTER (WHERE s.symptom_id IS NOT NULL) as symptoms,
                       json_agg(DISTINCT jsonb_build_object(
                           'vital_name', vt.vital_name, 'value', vt.value_numeric, 'unit', vt.unit
                       )) FILTER (WHERE vt.vital_id IS NOT NULL) as vitals
                FROM visits v
                LEFT JOIN symptoms s ON s.visit_id = v.visit_id
                LEFT JOIN vitals vt ON vt.visit_id = v.visit_id
                WHERE v.patient_id = %s
                GROUP BY v.visit_id
                ORDER BY v.visit_date DESC
                LIMIT %s
                """,
                (patient_id, limit),
            )
            rows = cursor.fetchall()
            return [
                {
                    "visit_id": str(r[0]),
                    "visit_date": r[1].isoformat() if r[1] else None,
                    "notes": r[2],
                    "source": r[3],
                    "symptoms": r[4] or [],
                    "vitals": r[5] or [],
                }
                for r in rows
            ]
        except Exception as exc:
            raise DbConnectionError(
                f"Failed to query patient history: {exc}",
                tool="PostgresAdapter",
                service="postgresql",
            ) from exc
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        started = time.monotonic()
        try:
            if not self._connected or not self._conn or self._conn.closed:
                return {
                    "status": "error",
                    "latency_ms": 0,
                    "detail": "not connected",
                }
            cursor = self._conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            latency = (time.monotonic() - started) * 1000
            return {
                "status": "ok",
                "latency_ms": round(latency, 2),
                "detail": "connected",
            }
        except Exception as exc:
            return {
                "status": "error",
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
                "detail": str(exc),
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _store_vital(cursor: Any, visit_id: str, patient_id: str, name: str, value: float | None, unit: str) -> None:
        if value is not None:
            cursor.execute(
                """
                INSERT INTO vitals (visit_id, patient_id, vital_name, value_numeric, unit, source)
                VALUES (%s, %s, %s, %s, %s, 'pipeline')
                """,
                (visit_id, patient_id, name, value, unit),
            )

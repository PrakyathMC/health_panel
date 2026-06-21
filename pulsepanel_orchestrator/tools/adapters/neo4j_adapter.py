"""Neo4j Adapter — clinical knowledge graph storage and traversal.

Manages Neo4j nodes and relationships for the clinical knowledge graph:
- Nodes: Patient, Symptom, Vital, ClinicalLabel, RiskConcept, Condition, Visit
- Relationships: HAS_SYMPTOM, HAS_VITAL, TRIGGERS, IMPLIES, SUGGESTS, INDICATES

Phase 2 adapter — designed to replace the in-memory GraphRetriever
when the Neo4j service is available.
"""

from __future__ import annotations

import time
from typing import Any

from ...errors import DbConnectionError
from ...models import ClinicalLabel, ClinicalRecord
from .base_adapter import BaseAdapter


class Neo4jAdapter(BaseAdapter):
    """Graph storage and traversal for clinical relationships."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._uri = uri or self._settings.neo4j_uri
        self._user = user or self._settings.neo4j_user
        self._password = password or self._settings.neo4j_password
        self._driver = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        from neo4j import GraphDatabase
        from neo4j.exceptions import ServiceUnavailable

        try:
            self._driver = GraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
            # Verify connection
            self._driver.verify_connectivity()
            self._connected = True
        except ServiceUnavailable as exc:
            raise DbConnectionError(
                f"Cannot connect to Neo4j at {self._uri}: {exc}",
                tool="Neo4jAdapter",
                service="neo4j",
            ) from exc
        except Exception as exc:
            raise DbConnectionError(
                f"Cannot connect to Neo4j at {self._uri}: {exc}",
                tool="Neo4jAdapter",
                service="neo4j",
            ) from exc

    def close(self) -> None:
        if self._driver:
            self._driver.close()
        self._driver = None
        self._connected = False

    # ------------------------------------------------------------------
    # Write — store clinical encounter as a graph
    # ------------------------------------------------------------------

    def store_clinical_encounter(
        self,
        record: ClinicalRecord,
        labels: list[ClinicalLabel],
        visit_id: str | None = None,
    ) -> None:
        """Create nodes and relationships for an entire clinical encounter.

        All writes happen inside a single transaction for consistency.
        Creates: Patient, Symptom(s), Vital(s), Visit, ClinicalLabel(s),
                 RiskConcept(s) and relationships between them.
        """
        self._require_connected()
        assert self._driver is not None

        def _write_all(tx: Any) -> None:
            _visit_id = visit_id or record.visit_id or record.record_id

            # Patient + Visit
            tx.run(
                """
                MERGE (p:Patient {patient_id: $patient_id})
                MERGE (v:Visit {visit_id: $visit_id})
                ON CREATE SET v.date = timestamp(), v.source = $source
                MERGE (p)-[:RECORDED_AT]->(v)
                """,
                patient_id=record.patient_id,
                visit_id=_visit_id,
                source=record.source,
            )

            # Symptoms
            for symptom in record.symptoms:
                tx.run(
                    """
                    MATCH (p:Patient {patient_id: $patient_id})
                    MERGE (s:Symptom {name: $name})
                    ON CREATE SET s.severity = $severity, s.duration = $duration
                    MERGE (p)-[:HAS_SYMPTOM]->(s)
                    """,
                    patient_id=record.patient_id, name=symptom.name,
                    severity=symptom.severity, duration=symptom.duration,
                )

            # Vitals
            if record.vitals:
                vitals_map = {
                    "SpO2": record.vitals.spo2,
                    "HR": record.vitals.heart_rate,
                    "Temperature": record.vitals.temperature_c,
                    "BP_systolic": record.vitals.systolic_bp,
                    "BP_diastolic": record.vitals.diastolic_bp,
                    "RR": record.vitals.respiratory_rate,
                }
                for vname, vvalue in vitals_map.items():
                    if vvalue is not None:
                        tx.run(
                            """
                            MATCH (p:Patient {patient_id: $patient_id})
                            MERGE (v:Vital {vital_name: $vital_name, value: $value})
                            MERGE (p)-[:HAS_VITAL]->(v)
                            """,
                            patient_id=record.patient_id,
                            vital_name=vname, value=vvalue,
                        )

            # Labels + Risk concepts
            for lbl in labels:
                tx.run(
                    """
                    MATCH (p:Patient {patient_id: $patient_id})
                    MERGE (l:ClinicalLabel {label: $label, rule: $rule})
                    ON CREATE SET l.evidence = $evidence
                    MERGE (p)-[:HAS_LABEL]->(l)
                    """,
                    patient_id=record.patient_id,
                    label=lbl.label, rule=lbl.rule,
                    evidence=str(lbl.evidence),
                )
                tx.run(
                    """
                    MATCH (l:ClinicalLabel {label: $label})
                    MERGE (r:RiskConcept {concept: $risk_concept})
                    MERGE (l)-[:IMPLIES]->(r)
                    """,
                    label=lbl.label,
                    risk_concept=lbl.risk_concept,
                )

        with self._driver.session() as session:
            try:
                session.execute_write(_write_all)
            except Exception as exc:
                raise DbConnectionError(
                    f"Failed to store clinical encounter in Neo4j: {exc}",
                    tool="Neo4jAdapter",
                    service="neo4j",
                ) from exc

    # ------------------------------------------------------------------
    # Write — seed knowledge base conditions
    # ------------------------------------------------------------------

    def seed_conditions(self, conditions: list[dict[str, Any]]) -> None:
        """Seed the knowledge base conditions into the graph.

        Args:
            conditions: List of dicts with keys:
                condition, title, doc_id, labels[], risk_concepts[], keywords[]
        """
        self._require_connected()
        assert self._driver is not None

        with self._driver.session() as session:
            try:
                for cond in conditions:
                    session.execute_write(self._merge_condition, cond)
            except Exception as exc:
                raise DbConnectionError(
                    f"Failed to seed conditions in Neo4j: {exc}",
                    tool="Neo4jAdapter",
                    service="neo4j",
                ) from exc

    @staticmethod
    def _merge_condition(tx: Any, cond: dict[str, Any]) -> None:
        tx.run(
            """
            MERGE (c:Condition {condition: $condition, title: $title, doc_id: $doc_id})
            """,
            condition=cond.get("condition"),
            title=cond.get("title"),
            doc_id=cond.get("doc_id"),
        )

        # Create INDICATES edges: Symptom → Condition
        for keyword in cond.get("keywords", []):
            tx.run(
                """
                MATCH (s:Symptom {name: $keyword})
                MATCH (c:Condition {condition: $condition})
                MERGE (s)-[:INDICATES]->(c)
                """,
                keyword=keyword, condition=cond.get("condition"),
            )

        # Create SUGGESTS edges: RiskConcept → Condition
        for risk in cond.get("risk_concepts", []):
            tx.run(
                """
                MATCH (r:RiskConcept {concept: $risk})
                MATCH (c:Condition {condition: $condition})
                MERGE (r)-[:SUGGESTS]->(c)
                """,
                risk=risk, condition=cond.get("condition"),
            )

    # ------------------------------------------------------------------
    # Read — graph traversal
    # ------------------------------------------------------------------

    def traverse_from_labels(
        self, patient_id: str, labels: list[ClinicalLabel], top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Traverse the graph from patient labels to find relevant conditions.

        Path: Patient → ClinicalLabel → RiskConcept → Condition

        Args:
            patient_id: The patient to traverse from.
            labels: Clinical labels to match against.
            top_k: Maximum results.

        Returns:
            List of dicts with keys: condition, title, doc_id, score, path.
        """
        self._require_connected()
        assert self._driver is not None
        label_names = [lbl.label for lbl in labels]

        with self._driver.session() as session:
            try:
                result = session.execute_read(
                    self._traverse_query, patient_id, label_names, top_k
                )
                return result
            except Exception as exc:
                raise DbConnectionError(
                    f"Failed to traverse Neo4j graph: {exc}",
                    tool="Neo4jAdapter",
                    service="neo4j",
                ) from exc

    @staticmethod
    def _traverse_query(
        tx: Any, patient_id: str, label_names: list[str], top_k: int
    ) -> list[dict[str, Any]]:
        query = """
        MATCH (p:Patient {patient_id: $patient_id})
              -[:HAS_LABEL]->(l:ClinicalLabel)
              -[:IMPLIES]->(r:RiskConcept)
              -[:SUGGESTS]->(c:Condition)
        WHERE l.label IN $label_names
        RETURN c.condition AS condition,
               c.title AS title,
               c.doc_id AS doc_id,
               count(*) AS path_count,
               collect(DISTINCT l.label) AS matched_labels,
               collect(DISTINCT r.concept) AS matched_risks
        ORDER BY path_count DESC
        LIMIT $top_k
        """
        result = tx.run(query, patient_id=patient_id, label_names=label_names, top_k=top_k)
        return [
            {
                "condition": record["condition"],
                "title": record["title"],
                "doc_id": record["doc_id"],
                "score": record["path_count"],
                "matched_labels": record["matched_labels"],
                "matched_risks": record["matched_risks"],
            }
            for record in result
        ]

    def traverse_from_symptoms(
        self, patient_id: str, symptoms: list[str], top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Traverse from patient symptoms to conditions.

        Path: Patient → Symptom → Condition
        """
        self._require_connected()
        assert self._driver is not None

        with self._driver.session() as session:
            try:
                result = session.execute_read(
                    self._symptom_traverse_query, patient_id, symptoms, top_k
                )
                return result
            except Exception as exc:
                raise DbConnectionError(
                    f"Failed to traverse symptoms in Neo4j: {exc}",
                    tool="Neo4jAdapter",
                    service="neo4j",
                ) from exc

    @staticmethod
    def _symptom_traverse_query(
        tx: Any, patient_id: str, symptoms: list[str], top_k: int
    ) -> list[dict[str, Any]]:
        query = """
        MATCH (p:Patient {patient_id: $patient_id})
              -[:HAS_SYMPTOM]->(s:Symptom)
              -[:INDICATES]->(c:Condition)
        WHERE s.name IN $symptoms
        RETURN c.condition AS condition,
               c.title AS title,
               c.doc_id AS doc_id,
               count(*) AS path_count,
               collect(DISTINCT s.name) AS matched_symptoms
        ORDER BY path_count DESC
        LIMIT $top_k
        """
        result = tx.run(query, patient_id=patient_id, symptoms=symptoms, top_k=top_k)
        return [
            {
                "condition": record["condition"],
                "title": record["title"],
                "doc_id": record["doc_id"],
                "score": record["path_count"],
                "matched_symptoms": record["matched_symptoms"],
            }
            for record in result
        ]

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        started = time.monotonic()
        try:
            if not self._connected or self._driver is None:
                return {"status": "error", "latency_ms": 0, "detail": "not connected"}
            self._driver.verify_connectivity()
            latency = (time.monotonic() - started) * 1000
            return {
                "status": "ok",
                "latency_ms": round(latency, 2),
                "detail": f"connected to {self._uri}",
            }
        except Exception as exc:
            return {
                "status": "error",
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
                "detail": str(exc),
            }

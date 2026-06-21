"""Tool 3 — EmbeddingTextBuilder.

Builds rich clinical text from the normalised record and derived labels,
optimised for semantic vector search. The generated text combines patient
narrative, symptoms, clinical findings, facts, and risk concepts into a
single natural-language string.
"""

from __future__ import annotations

from ..base import BaseTool
from ..context import OrchestrationContext
from ..errors import ToolExecutionError
from ..models import ClinicalLabel, ClinicalRecord


def build_embedding_payload(
    record: ClinicalRecord,
    labels: list[ClinicalLabel],
) -> dict[str, object]:
    """Build a structured payload containing embedding text and metadata.

    Useful for QdrantAdapter point payloads.
    """
    return {
        "record_id": record.record_id,
        "patient_id": record.patient_id,
        "visit_id": record.visit_id,
        "embedding_text": EmbeddingTextBuilder._build_text(record, labels),
        "metadata": {
            "symptoms": [symptom.name for symptom in record.symptoms],
            "labels": [label.label for label in labels],
            "facts": [label.fact for label in labels],
            "risk_concepts": sorted(
                {label.risk_concept for label in labels if label.risk_concept}
            ),
            "source": record.source,
        },
    }


class EmbeddingTextBuilder(BaseTool):
    """Build a clinically meaningful embedding text from record + labels."""

    @property
    def name(self) -> str:
        return "EmbeddingTextBuilder"

    @property
    def dependencies(self) -> list[str]:
        return ["InputNormalizer", "ClinicalRuleEngine"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        if ctx.record is None:
            raise ToolExecutionError(
                "No ClinicalRecord found — InputNormalizer must run first.",
                tool=self.name,
            )

        labels = ctx.labels or []
        ctx.embedding_text = self._build_text(ctx.record, labels)
        return ctx

    # ------------------------------------------------------------------
    # Text builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_text(record: ClinicalRecord, labels: list[ClinicalLabel]) -> str:
        """Build the embedding text as a natural-language clinical summary."""
        parts: list[str] = []

        # --- Patient narrative ---
        narrative = record.query.strip()
        if narrative:
            parts.append(f"Patient says: {narrative}")

        # --- Symptoms ---
        if record.symptoms:
            symptom_text = EmbeddingTextBuilder._format_symptoms(record)
            if symptom_text:
                parts.append(symptom_text)

        # --- Clinical findings ---
        if labels:
            label_names = EmbeddingTextBuilder._dedupe(
                [lbl.label.replace("_", " ") for lbl in labels]
            )
            parts.append(
                "Clinical findings include "
                + ", ".join(label_names)
                + "."
            )

        # --- Clinical facts ---
        facts = EmbeddingTextBuilder._dedupe(
            [lbl.fact for lbl in labels if lbl.fact]
        )
        if facts:
            parts.extend(facts)

        # --- Risk concepts ---
        risks = EmbeddingTextBuilder._dedupe(
            [lbl.risk_concept for lbl in labels if lbl.risk_concept]
        )
        if risks:
            risk_text = "Risk concepts include " + ", ".join(risks) + "."
            parts.append(risk_text)

        return " ".join(parts)

    @staticmethod
    def _format_symptoms(record: ClinicalRecord) -> str:
        """Format symptoms into a readable string."""
        parts: list[str] = []
        for symptom in record.symptoms:
            detail = symptom.name
            if symptom.severity:
                detail = f"{symptom.severity} {detail}"
            if symptom.duration:
                detail = f"{detail} ({symptom.duration})"
            parts.append(detail)
        return "Patient reports symptoms including " + ", ".join(parts) + "."

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        """Remove duplicates while preserving order."""
        seen: set[str] = set()
        result: list[str] = []
        for v in values:
            if v not in seen:
                seen.add(v)
                result.append(v)
        return result

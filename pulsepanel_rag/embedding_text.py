from __future__ import annotations

from .models import ClinicalLabel, ClinicalRecord


def build_embedding_payload(
    record: ClinicalRecord,
    labels: list[ClinicalLabel],
) -> dict[str, object]:
    return {
        "record_id": record.record_id,
        "patient_id": record.patient_id,
        "visit_id": record.visit_id,
        "embedding_text": build_embedding_text(record, labels),
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


def build_embedding_text(record: ClinicalRecord, labels: list[ClinicalLabel]) -> str:
    parts: list[str] = []

    if record.query:
        query = record.query.strip().rstrip(".")
        parts.append(f"Patient narrative: {query}.")

    if record.symptoms:
        parts.append(f"Reported symptoms: {_format_symptoms(record)}.")

    if labels:
        label_text = ", ".join(label.label for label in labels)
        fact_text = "; ".join(_dedupe(label.fact for label in labels))
        risk_text = ", ".join(
            sorted({label.risk_concept for label in labels if label.risk_concept})
        )
        parts.append(f"Clinical findings include {label_text}.")
        parts.append(f"Clinical facts: {fact_text}.")
        if risk_text:
            parts.append(f"Risk concepts include {risk_text}.")

    return " ".join(parts)


def _format_symptoms(record: ClinicalRecord) -> str:
    formatted = []
    for symptom in record.symptoms:
        details = []
        if symptom.severity:
            details.append(f"severity {symptom.severity}")
        if symptom.duration:
            details.append(f"duration {symptom.duration}")
        if details:
            formatted.append(f"{symptom.name} ({', '.join(details)})")
        else:
            formatted.append(symptom.name)
    return ", ".join(formatted)


def _dedupe(values: list[str] | object) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped

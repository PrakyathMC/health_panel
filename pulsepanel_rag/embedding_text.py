from __future__ import annotations

from .models import ClinicalLabel, ClinicalRecord


def build_embedding_text(record: ClinicalRecord, labels: list[ClinicalLabel]) -> str:
    parts: list[str] = []

    if record.query:
        query = record.query.strip().rstrip(".")
        parts.append(f"Patient says: {query}.")

    if record.symptoms:
        symptom_names = ", ".join(symptom.name for symptom in record.symptoms)
        parts.append(f"Patient reports symptoms including {symptom_names}.")

    if labels:
        label_text = ", ".join(label.label for label in labels)
        fact_text = " ".join(label.fact for label in labels)
        risk_text = ", ".join(
            sorted({label.risk_concept for label in labels if label.risk_concept})
        )
        parts.append(f"Clinical findings include {label_text}.")
        parts.append(fact_text)
        if risk_text:
            parts.append(f"Risk concepts include {risk_text}.")

    return " ".join(parts)

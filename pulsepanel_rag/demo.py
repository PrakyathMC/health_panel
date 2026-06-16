from __future__ import annotations

import json
from dataclasses import asdict

from .mock_data import MOCK_KNOWLEDGE_BASE
from .models import ClinicalRecord, Symptom
from .retrieval import HybridRetriever


def main() -> None:
    record = ClinicalRecord(
        record_id="REC001",
        patient_id="P001",
        visit_id="V001",
        query="I have severe chest pain and dizziness.",
        symptoms=[
            Symptom(name="chest pain", severity="severe", duration="2 hours"),
            Symptom(name="dizziness"),
        ],
        vitals={
            "spo2": 90,
            "heart_rate": 110,
            "temperature_c": 38.1,
            "systolic_bp": 145,
            "diastolic_bp": 92,
        },
        source=["patient", "wearable"],
    )

    retriever = HybridRetriever(MOCK_KNOWLEDGE_BASE)
    bundle = retriever.retrieve(record)
    print(json.dumps(asdict(bundle), indent=2))


if __name__ == "__main__":
    main()


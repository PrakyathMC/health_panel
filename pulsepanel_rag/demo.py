from __future__ import annotations

import json

from .input_normalizer import normalize_clinical_record
from .mock_data import MOCK_KNOWLEDGE_BASE
from .retrieval import HybridRetriever


def main() -> None:
    record = normalize_clinical_record(
        {
            "recordId": "REC001",
            "patientId": "P001",
            "visitId": "V001",
            "message": "I have severe chest pain and dizziness.",
            "symptoms": [
                {"symptom": "Chest Pain", "severity": "severe", "duration": "2 hours"},
                "Dizziness",
            ],
            "vitals": {
                "SpO2": 90,
                "HR": 110,
                "temp": 38.1,
                "BP": "145/92",
            },
            "source": "patient",
        }
    )

    retriever = HybridRetriever(MOCK_KNOWLEDGE_BASE)
    bundle = retriever.retrieve(record)
    print(json.dumps(bundle.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()

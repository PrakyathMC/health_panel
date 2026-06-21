from __future__ import annotations

import unittest

from pydantic import ValidationError

from pulsepanel_rag.clinical_rules import ClinicalRuleEngine, derive_clinical_labels
from pulsepanel_rag.embedding_text import build_embedding_payload, build_embedding_text
from pulsepanel_rag.input_normalizer import normalize_clinical_record
from pulsepanel_rag.mock_data import MOCK_KNOWLEDGE_BASE
from pulsepanel_rag.models import ClinicalRecord, RetrievalBundle, Symptom
from pulsepanel_rag.retrieval import HybridRetriever


class ClinicalRulesTest(unittest.TestCase):
    def test_derives_auditable_vital_labels(self) -> None:
        labels = derive_clinical_labels(
            {
                "spo2": 90,
                "heart_rate": 110,
                "temperature_c": 38.1,
                "systolic_bp": 145,
                "diastolic_bp": 92,
            }
        )

        self.assertEqual(
            [label.label for label in labels],
            ["hypoxia", "tachycardia", "fever", "hypertension"],
        )
        self.assertEqual(labels[0].rule, "spo2 < 92")
        self.assertEqual(labels[0].evidence, {"spo2": 90.0})

    def test_clinical_rule_engine_derives_extended_labels(self) -> None:
        labels = ClinicalRuleEngine().derive_labels(
            {
                "spo2": 82,
                "heart_rate": 55,
                "temperature_c": 34.5,
                "systolic_bp": 85,
                "diastolic_bp": 60,
                "respiratory_rate": 24,
            }
        )

        self.assertEqual(
            [label.label for label in labels],
            [
                "severe_hypoxia",
                "hypoxia",
                "bradycardia",
                "hypothermia",
                "hypotension",
                "tachypnea",
            ],
        )
        self.assertEqual(labels[0].evidence, {"spo2": 82.0})


class HybridRetrieverTest(unittest.TestCase):
    def test_ranks_matching_condition_from_symptoms_and_vitals(self) -> None:
        record = ClinicalRecord(
            record_id="REC001",
            patient_id="P001",
            query="I have severe chest pain and dizziness.",
            symptoms=[Symptom(name="chest pain"), Symptom(name="dizziness")],
            vitals={
                "spo2": 90,
                "heart_rate": 110,
                "systolic_bp": 145,
                "diastolic_bp": 92,
            },
        )

        bundle = HybridRetriever(MOCK_KNOWLEDGE_BASE).retrieve(record)

        self.assertIn("hypoxia", bundle.embedding_text)
        self.assertEqual(bundle.results[0].condition, "acute coronary syndrome")
        self.assertIn("semantic", bundle.results[0].retrieval_sources)
        self.assertIn("symbolic", bundle.results[0].retrieval_sources)
        self.assertIsInstance(bundle, RetrievalBundle)


class EmbeddingTextTest(unittest.TestCase):
    def test_builds_clinical_language_for_embedding(self) -> None:
        record = ClinicalRecord(
            record_id="REC001",
            patient_id="P001",
            query="I have chest pain",
            symptoms=[
                Symptom(name="chest pain", severity="severe", duration="2 hours")
            ],
            vitals={"spo2": 90, "heart_rate": 110},
            source=["patient", "wearable"],
        )
        labels = derive_clinical_labels(record.vitals)

        embedding_text = build_embedding_text(record, labels)

        self.assertIn("Patient narrative: I have chest pain.", embedding_text)
        self.assertIn("chest pain (severity severe, duration 2 hours)", embedding_text)
        self.assertIn("Clinical findings include hypoxia, tachycardia.", embedding_text)
        self.assertIn("oxygen saturation is below normal threshold", embedding_text)
        self.assertIn("Risk concepts include cardiac risk, respiratory distress.", embedding_text)
        self.assertNotIn("{", embedding_text)

    def test_builds_embedding_payload_for_future_vector_adapter(self) -> None:
        record = ClinicalRecord(
            record_id="REC001",
            patient_id="P001",
            query="I feel dizzy",
            symptoms=[Symptom(name="dizziness")],
            vitals={"heart_rate": 110},
            source=["patient"],
        )
        labels = derive_clinical_labels(record.vitals)

        payload = build_embedding_payload(record, labels)

        self.assertEqual(payload["record_id"], "REC001")
        self.assertEqual(payload["patient_id"], "P001")
        self.assertIn("embedding_text", payload)
        self.assertEqual(payload["metadata"]["labels"], ["tachycardia"])
        self.assertEqual(payload["metadata"]["risk_concepts"], ["cardiac risk"])


class PydanticContractTest(unittest.TestCase):
    def test_valid_record_parses_with_normalized_vital_aliases(self) -> None:
        record = ClinicalRecord(
            record_id="REC001",
            patient_id="P001",
            query="Shortness of breath",
            vitals={"SpO2": 91, "HR": 108, "temp": 38.0},
        )

        self.assertEqual(record.vitals.spo2, 91)
        self.assertEqual(record.vitals.heart_rate, 108)
        self.assertEqual(record.vitals.temperature_c, 38.0)

    def test_missing_patient_id_fails_validation(self) -> None:
        with self.assertRaises(ValidationError):
            ClinicalRecord(record_id="REC001", query="Chest pain")

    def test_empty_query_fails_validation(self) -> None:
        with self.assertRaises(ValidationError):
            ClinicalRecord(record_id="REC001", patient_id="P001", query="  ")

    def test_invalid_spo2_fails_validation(self) -> None:
        with self.assertRaises(ValidationError):
            ClinicalRecord(
                record_id="REC001",
                patient_id="P001",
                query="Shortness of breath",
                vitals={"spo2": 140},
            )


class InputNormalizerTest(unittest.TestCase):
    def test_normalizes_frontend_aliases_into_clinical_record(self) -> None:
        record = normalize_clinical_record(
            {
                "recordId": "REC001",
                "patientId": "P001",
                "visitId": "V001",
                "message": "Chest pain",
                "symptoms": ["Chest Pain", {"symptom": "Dizziness"}],
                "vitals": {"SpO2": 90, "HR": 110, "temp": 38.1, "BP": "145/92"},
                "source": "patient",
            }
        )

        self.assertEqual(record.record_id, "REC001")
        self.assertEqual(record.patient_id, "P001")
        self.assertEqual(record.query, "Chest pain")
        self.assertEqual([symptom.name for symptom in record.symptoms], ["chest pain", "dizziness"])
        self.assertEqual(record.vitals.spo2, 90)
        self.assertEqual(record.vitals.heart_rate, 110)
        self.assertEqual(record.vitals.temperature_c, 38.1)
        self.assertEqual(record.vitals.systolic_bp, 145)
        self.assertEqual(record.vitals.diastolic_bp, 92)
        self.assertEqual(record.source, ["patient"])

    def test_normalizer_uses_pydantic_to_reject_bad_values(self) -> None:
        with self.assertRaises(ValidationError):
            normalize_clinical_record(
                {
                    "record_id": "REC001",
                    "patient_id": "P001",
                    "query": "Shortness of breath",
                    "vitals": {"SpO2": 140},
                }
            )


if __name__ == "__main__":
    unittest.main()

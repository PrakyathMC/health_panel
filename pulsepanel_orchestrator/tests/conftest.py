"""Shared fixtures for orchestration layer tests."""

from __future__ import annotations

import json
import pytest
from typing import Any

from pulsepanel_orchestrator import PulsePanelOrchestrator
from pulsepanel_orchestrator.models import (
    ClinicalLabel,
    ClinicalRecord,
    KnowledgeDocument,
    RetrievalBundle,
    RetrievalResult,
    Symptom,
    VitalSigns,
)


# ------------------------------------------------------------------
# Sample data
# ------------------------------------------------------------------

SAMPLE_RAW_INPUT: dict[str, Any] = {
    "record_id": "REC001",
    "patient_id": "P001",
    "visit_id": "V001",
    "query": "I have severe chest pain and dizziness.",
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

SAMPLE_RAW_NO_VITALS: dict[str, Any] = {
    "record_id": "REC002",
    "patient_id": "P002",
    "query": "I feel tired.",
    "symptoms": [],
    "vitals": {},
}

SAMPLE_RAW_MISSING_FIELDS: dict[str, Any] = {
    "patient_id": "P003",
}


# ------------------------------------------------------------------
# Expected results
# ------------------------------------------------------------------

EXPECTED_LABELS_FOR_SAMPLE = {
    "hypoxia",
    "tachycardia",
    "fever",
    "hypertension",
}

EXPECTED_RISK_CONCEPTS_FOR_SAMPLE = {
    "respiratory distress",
    "cardiac risk",
    "infection risk",
}


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def orchestrator() -> PulsePanelOrchestrator:
    """Return a default orchestrator instance."""
    return PulsePanelOrchestrator()


@pytest.fixture
def sample_input() -> dict[str, Any]:
    """Return the standard sample clinical input."""
    return dict(SAMPLE_RAW_INPUT)


@pytest.fixture
def sample_no_vitals() -> dict[str, Any]:
    """Return sample input with no vitals."""
    return dict(SAMPLE_RAW_NO_VITALS)


@pytest.fixture
def bundle(orchestrator: PulsePanelOrchestrator) -> RetrievalBundle:
    """Run the orchestrator on sample input and return the bundle."""
    return orchestrator.run(SAMPLE_RAW_INPUT)


@pytest.fixture
def sample_clinical_record() -> ClinicalRecord:
    """Return a ClinicalRecord instance for adapter tests."""
    return ClinicalRecord(
        record_id="REC_TEST",
        patient_id="P_TEST",
        query="Test query",
        symptoms=[Symptom(name="headache", severity="mild")],
        vitals=VitalSigns(spo2=95.0, heart_rate=72.0),
        source=["test"],
        visit_id="V_TEST",
    )


@pytest.fixture
def sample_labels() -> list[ClinicalLabel]:
    """Return sample derived labels."""
    return [
        ClinicalLabel(
            label="hypoxia",
            fact="oxygen saturation below normal threshold",
            risk_concept="respiratory distress",
            rule="hypoxia_rule",
            evidence={"spo2": 88.0},
        ),
        ClinicalLabel(
            label="tachycardia",
            fact="heart rate is elevated",
            risk_concept="cardiac risk",
            rule="tachycardia_rule",
            evidence={"heart_rate": 110.0},
        ),
    ]


@pytest.fixture
def sample_knowledge_docs() -> list[KnowledgeDocument]:
    """Return sample knowledge documents."""
    return [
        KnowledgeDocument(
            doc_id="kb_test_1",
            title="Test condition",
            condition="test_condition",
            text="Test knowledge document.",
            keywords=["headache", "fever"],
            labels=["hypoxia"],
            risk_concepts=["cardiac risk"],
        ),
    ]


@pytest.fixture
def sample_results() -> list[RetrievalResult]:
    """Return sample retrieval results."""
    return [
        RetrievalResult(
            rank=1,
            title="Possible acute coronary syndrome",
            condition="acs",
            score=0.85,
            retrieval_sources=["semantic", "symbolic"],
            evidence=[{"matched_labels": "hypoxia, tachycardia"}],
            explanation="Patient presents with chest pain and tachycardia.",
        ),
        RetrievalResult(
            rank=2,
            title="Possible infection or sepsis risk",
            condition="infection",
            score=0.72,
            retrieval_sources=["keyword"],
            evidence=[{"matched_keywords": "fever"}],
            explanation="Fever and tachycardia suggest possible infection.",
        ),
    ]

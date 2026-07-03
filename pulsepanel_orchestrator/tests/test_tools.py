"""Unit tests for individual orchestration tools.

Tests each tool in isolation using pre-built context objects.
"""

from __future__ import annotations

import pytest

from pulsepanel_rag.models import ClinicalRecord as RagClinicalRecord
from pulsepanel_orchestrator.context import OrchestrationContext
from pulsepanel_orchestrator.errors import ToolExecutionError, ValidationError
from pulsepanel_orchestrator.models import (
    ClinicalLabel,
    ClinicalRecord,
    RetrievalResult,
    Symptom,
    VitalSigns,
)
from pulsepanel_orchestrator.tools import (
    ClinicalRuleEngine,
    EmbeddingTextBuilder,
    ExplanationGenerator,
    GraphRetriever,
    InputNormalizer,
    KeywordRetriever,
    ResultMerger,
    SemanticRetriever,
    SymbolicRetriever,
)
from pulsepanel_orchestrator.tools.adapters import QdrantAdapter


# ======================================================================
# InputNormalizer
# ======================================================================

class TestInputNormalizer:
    def test_normalizes_valid_input(self):
        tool = InputNormalizer()
        ctx = OrchestrationContext(raw_input={
            "record_id": "R1",
            "patient_id": "P1",
            "query": "Chest pain",
            "symptoms": ["Cough"],
            "vitals": {"SpO2": 95},
            "source": "patient",
        })
        ctx = tool.run(ctx)
        assert ctx.record is not None
        assert ctx.record.record_id == "R1"
        assert ctx.record.patient_id == "P1"
        assert isinstance(ctx.record, RagClinicalRecord)

    def test_rejects_missing_record_id(self):
        tool = InputNormalizer()
        ctx = OrchestrationContext(raw_input={"patient_id": "P1", "query": "test"})
        with pytest.raises(ValidationError):
            tool.run(ctx)

    def test_rejects_missing_patient_id(self):
        tool = InputNormalizer()
        ctx = OrchestrationContext(raw_input={"record_id": "R1", "query": "test"})
        with pytest.raises(ValidationError):
            tool.run(ctx)

    def test_rejects_invalid_vital_range(self):
        tool = InputNormalizer()
        ctx = OrchestrationContext(raw_input={
            "record_id": "R1", "patient_id": "P1", "query": "test",
            "vitals": {"SpO2": 140},
        })
        with pytest.raises(ValidationError, match="less than or equal to 100"):
            tool.run(ctx)

    def test_handles_vital_aliases(self):
        tool = InputNormalizer()
        ctx = OrchestrationContext(raw_input={
            "record_id": "R2", "patient_id": "P2", "query": "test",
            "vitals": {"o2": 92, "pulse": 80, "bp": "120/80"},
        })
        ctx = tool.run(ctx)
        assert ctx.record.vitals is not None
        assert ctx.record.vitals.spo2 == 92.0
        assert ctx.record.vitals.heart_rate == 80.0
        assert ctx.record.vitals.systolic_bp == 120.0
        assert ctx.record.vitals.diastolic_bp == 80.0

    def test_handles_symptom_variants(self):
        tool = InputNormalizer()
        ctx = OrchestrationContext(raw_input={
            "record_id": "R3", "patient_id": "P3", "query": "test",
            "symptoms": [
                "Headache",
                {"name": "Fever", "severity": "high"},
                {"symptom": "Cough", "duration": "3 days"},
            ],
        })
        ctx = tool.run(ctx)
        assert len(ctx.record.symptoms) == 3
        assert ctx.record.symptoms[0].name == "headache"
        assert ctx.record.symptoms[1].severity == "high"
        assert ctx.record.symptoms[2].duration == "3 days"


# ======================================================================
# ClinicalRuleEngine
# ======================================================================

class TestClinicalRuleEngine:
    def test_derives_labels_from_vitals(self):
        tool = ClinicalRuleEngine()
        ctx = OrchestrationContext(raw_input={})
        ctx.record = ClinicalRecord(
            record_id="R1", patient_id="P1", query="test",
            vitals=VitalSigns(spo2=90.0, heart_rate=110.0, temperature_c=38.0),
        )
        ctx = tool.run(ctx)
        assert ctx.labels is not None
        assert len(ctx.labels) >= 3

    def test_returns_empty_for_no_vitals(self):
        tool = ClinicalRuleEngine()
        ctx = OrchestrationContext(raw_input={})
        ctx.record = ClinicalRecord(record_id="R1", patient_id="P1", query="test")
        ctx = tool.run(ctx)
        assert ctx.labels == []

    def test_labels_have_correct_fields(self):
        tool = ClinicalRuleEngine()
        ctx = OrchestrationContext(raw_input={})
        ctx.record = ClinicalRecord(
            record_id="R1", patient_id="P1", query="test",
            vitals=VitalSigns(spo2=88.0),
        )
        ctx = tool.run(ctx)
        lbl = ctx.labels[0]
        assert lbl.label
        assert lbl.fact
        assert lbl.risk_concept
        assert lbl.rule
        assert lbl.evidence


# ======================================================================
# EmbeddingTextBuilder
# ======================================================================

class TestEmbeddingTextBuilder:
    def test_builds_text_from_record(self):
        tool = EmbeddingTextBuilder()
        ctx = OrchestrationContext(raw_input={})
        ctx.record = ClinicalRecord(
            record_id="R1", patient_id="P1", query="Severe chest pain",
            symptoms=[Symptom(name="chest pain", severity="severe")],
        )
        ctx.labels = [ClinicalLabel(label="hypoxia", fact="low oxygen", risk_concept="respiratory distress", rule="hypoxia_rule", evidence={"spo2": 88})]
        ctx = tool.run(ctx)
        assert ctx.embedding_text
        assert "chest pain" in ctx.embedding_text
        assert "hypoxia" in ctx.embedding_text

    def test_requires_record(self):
        tool = EmbeddingTextBuilder()
        ctx = OrchestrationContext(raw_input={})
        with pytest.raises(ToolExecutionError):
            tool.run(ctx)


# ======================================================================
# Retrievers
# ======================================================================

class TestSemanticRetriever:
    def test_returns_results(self):
        tool = SemanticRetriever()
        ctx = OrchestrationContext(raw_input={})
        ctx.record = ClinicalRecord(record_id="R1", patient_id="P1", query="chest pain")
        ctx.embedding_text = "Patient has chest pain and shortness of breath"
        ctx = tool.run(ctx)
        assert len(ctx.semantic_results) > 0
        assert ctx.semantic_results[0].score > 0

    def test_uses_vector_store_adapter_when_enabled(self):
        class FakeVectorAdapter:
            def __init__(self):
                self.connected = False
                self.collection_ready = False
                self.ingested_count = 0
                self.search_query = ""

            def connect(self):
                self.connected = True

            def ensure_collection(self):
                self.collection_ready = True

            def ingest_documents(self, documents):
                self.ingested_count = len(documents)

            def search(self, query_text, top_k=10):
                self.search_query = query_text
                return [
                    {
                        "doc_id": "doc-cardiac-risk",
                        "title": "Cardiac Risk Triage",
                        "condition": "cardiac_risk",
                        "score": 0.91,
                        "payload": {},
                    }
                ][:top_k]

        adapter = FakeVectorAdapter()
        tool = SemanticRetriever(
            vector_adapter=adapter,
            use_vector_store=True,
            top_k=3,
        )
        ctx = OrchestrationContext(raw_input={})
        ctx.record = ClinicalRecord(record_id="R1", patient_id="P1", query="chest pain")
        ctx.embedding_text = "Patient has severe chest pain and shortness of breath"

        ctx = tool.run(ctx)

        assert adapter.connected
        assert adapter.collection_ready
        assert adapter.ingested_count > 0
        assert adapter.search_query == ctx.embedding_text
        assert len(ctx.semantic_results) == 1
        assert ctx.semantic_results[0].retrieval_sources == ["semantic", "qdrant"]
        assert ctx.semantic_results[0].evidence[0]["doc_id"] == "doc-cardiac-risk"

    def test_qdrant_adapter_search_uses_query_points(self):
        class FakePoint:
            score = 0.87
            payload = {
                "doc_id": "doc-hypoxia",
                "title": "Hypoxia Protocol",
                "condition": "hypoxia",
            }

        class FakeResponse:
            points = [FakePoint()]

        class FakeClient:
            def __init__(self):
                self.query = None
                self.limit = None

            def query_points(
                self,
                collection_name,
                query,
                limit,
                with_payload,
            ):
                self.query = query
                self.limit = limit
                return FakeResponse()

        adapter = QdrantAdapter(collection_name="test_collection")
        fake_client = FakeClient()
        adapter._connected = True
        adapter._client = fake_client
        adapter.encode = lambda text: [0.1, 0.2, 0.3]

        results = adapter.search("hypoxic patient", top_k=5)

        assert fake_client.query == [0.1, 0.2, 0.3]
        assert fake_client.limit == 5
        assert results[0]["doc_id"] == "doc-hypoxia"
        assert results[0]["score"] == 0.87


class TestKeywordRetriever:
    def test_returns_results(self):
        tool = KeywordRetriever()
        ctx = OrchestrationContext(raw_input={})
        ctx.record = ClinicalRecord(
            record_id="R1", patient_id="P1", query="chest pain dizziness",
            symptoms=[Symptom(name="chest pain"), Symptom(name="dizziness")],
        )
        ctx = tool.run(ctx)
        assert len(ctx.keyword_results) > 0


class TestSymbolicRetriever:
    def test_returns_results(self):
        tool = SymbolicRetriever()
        ctx = OrchestrationContext(raw_input={})
        ctx.labels = [ClinicalLabel(label="hypoxia", fact="low oxygen", risk_concept="respiratory distress", rule="hypoxia_rule", evidence={"spo2": 88})]
        ctx = tool.run(ctx)
        assert len(ctx.symbolic_results) > 0


class TestGraphRetriever:
    def test_returns_results(self):
        tool = GraphRetriever()
        ctx = OrchestrationContext(raw_input={})
        ctx.labels = [ClinicalLabel(label="hypoxia", fact="low oxygen", risk_concept="respiratory distress", rule="hypoxia_rule", evidence={"spo2": 88})]
        ctx = tool.run(ctx)
        assert len(ctx.graph_results) > 0


# ======================================================================
# ResultMerger
# ======================================================================

class TestResultMerger:
    def test_merges_results(self):
        tool = ResultMerger(top_k=5)
        ctx = OrchestrationContext(raw_input={})
        ctx.semantic_results = [
            RetrievalResult(rank=1, title="A", condition="a", score=0.9, retrieval_sources=["semantic"]),
        ]
        ctx.keyword_results = [
            RetrievalResult(rank=1, title="B", condition="b", score=0.8, retrieval_sources=["keyword"]),
        ]
        ctx = tool.run(ctx)
        assert len(ctx.merged_results) == 2
        assert ctx.merged_results[0].score >= ctx.merged_results[1].score


# ======================================================================
# ExplanationGenerator
# ======================================================================

class TestExplanationGenerator:
    def test_generates_explanations(self):
        tool = ExplanationGenerator()
        ctx = OrchestrationContext(raw_input={})
        ctx.record = ClinicalRecord(record_id="R1", patient_id="P1", query="test")
        ctx.embedding_text = "test"
        ctx.merged_results = [
            RetrievalResult(rank=1, title="Test", condition="test", score=0.5, retrieval_sources=["semantic"]),
        ]
        ctx = tool.run(ctx)
        assert ctx.bundle is not None
        assert len(ctx.bundle.results) == 1
        assert ctx.bundle.results[0].explanation

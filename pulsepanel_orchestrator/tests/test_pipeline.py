"""End-to-end integration tests for the orchestration pipeline.

Tests the full pipeline from raw input to RetrievalBundle output,
validating labels, ranking, explanations, and error handling.
"""

from __future__ import annotations

import pytest

from pulsepanel_orchestrator import PulsePanelOrchestrator
from pulsepanel_orchestrator.errors import ValidationError
from pulsepanel_orchestrator.models import ClinicalLabel, ClinicalRecord, RetrievalBundle

from .conftest import (
    EXPECTED_LABELS_FOR_SAMPLE,
    EXPECTED_RISK_CONCEPTS_FOR_SAMPLE,
    SAMPLE_RAW_INPUT,
)


class TestFullPipeline:
    """Test the complete pipeline end-to-end."""

    def test_pipeline_returns_bundle(self, orchestrator: PulsePanelOrchestrator):
        """Pipeline should return a RetrievalBundle."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        assert isinstance(bundle, RetrievalBundle)

    def test_pipeline_populates_record_id(self, orchestrator: PulsePanelOrchestrator):
        """Bundle should contain the original record_id."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        assert bundle.record_id == "REC001"

    def test_pipeline_populates_patient_id(self, orchestrator: PulsePanelOrchestrator):
        """Bundle should contain the original patient_id."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        assert bundle.patient_id == "P001"

    def test_pipeline_generates_labels(self, orchestrator: PulsePanelOrchestrator):
        """Pipeline should derive clinical labels from vitals."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        assert len(bundle.labels) > 0
        label_names = {lbl.label for lbl in bundle.labels}
        assert label_names == EXPECTED_LABELS_FOR_SAMPLE

    def test_pipeline_labels_have_evidence(self, orchestrator: PulsePanelOrchestrator):
        """Each label should have evidence dict populated."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        for lbl in bundle.labels:
            assert lbl.evidence, f"Label {lbl.label} has no evidence"
            assert any(v is not None for v in lbl.evidence.values())

    def test_pipeline_generates_embedding_text(self, orchestrator: PulsePanelOrchestrator):
        """Pipeline should generate embedding text."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        assert bundle.embedding_text
        assert "chest pain" in bundle.embedding_text.lower()

    def test_pipeline_returns_results(self, orchestrator: PulsePanelOrchestrator):
        """Pipeline should return ranked results."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        assert len(bundle.results) > 0

    def test_pipeline_results_are_ranked(self, orchestrator: PulsePanelOrchestrator):
        """Results should be sorted by rank."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        ranks = [r.rank for r in bundle.results]
        assert ranks == sorted(ranks)

    def test_pipeline_acs_is_top_result(self, orchestrator: PulsePanelOrchestrator):
        """ACS should be the top result for chest pain + cardiac risk."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        assert bundle.results[0].condition == "acs"

    def test_pipeline_results_have_sources(self, orchestrator: PulsePanelOrchestrator):
        """Each result should identify its retrieval sources."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        for r in bundle.results:
            assert len(r.retrieval_sources) > 0

    def test_pipeline_results_have_explanations(self, orchestrator: PulsePanelOrchestrator):
        """Each result should have an explanation."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        for r in bundle.results:
            assert r.explanation
            assert len(r.explanation) > 10

    def test_pipeline_has_no_errors(self, orchestrator: PulsePanelOrchestrator):
        """Pipeline should complete without errors for valid input."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        assert len(bundle.errors) == 0, f"Errors: {bundle.errors}"

    def test_pipeline_includes_risk_concepts(self, orchestrator: PulsePanelOrchestrator):
        """Labels should cover expected risk concepts."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        risk_concepts = {lbl.risk_concept for lbl in bundle.labels}
        for expected in EXPECTED_RISK_CONCEPTS_FOR_SAMPLE:
            assert expected in risk_concepts, f"Missing risk concept: {expected}"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_vitals_returns_empty_labels(self, orchestrator: PulsePanelOrchestrator, sample_no_vitals):
        """Input without vitals should produce no labels but still return results."""
        bundle = orchestrator.run(sample_no_vitals)
        assert len(bundle.labels) == 0
        assert isinstance(bundle, RetrievalBundle)

    def test_missing_required_fields_returns_error(self, orchestrator: PulsePanelOrchestrator):
        """Missing record_id or patient_id should produce a validation error."""
        bundle = orchestrator.run({})
        assert len(bundle.errors) > 0

    def test_empty_symptoms_still_works(self, orchestrator: PulsePanelOrchestrator):
        """Empty symptoms list should not crash the pipeline."""
        bundle = orchestrator.run({
            "record_id": "REC_EMPTY",
            "patient_id": "P_EMPTY",
            "query": "Routine checkup",
            "symptoms": [],
            "vitals": {},
        })
        assert bundle.record_id == "REC_EMPTY"

    def test_minimal_input_works(self, orchestrator: PulsePanelOrchestrator):
        """Minimal valid input should process without errors."""
        bundle = orchestrator.run({
            "record_id": "REC_MIN",
            "patient_id": "P_MIN",
            "query": "Cough and fever",
            "symptoms": ["Cough", "Fever"],
            "vitals": {"temp": 38.5},
        })
        assert len(bundle.errors) == 0
        assert len(bundle.results) > 0

    def test_multiple_runs_same_orchestrator(self, orchestrator: PulsePanelOrchestrator):
        """Running the pipeline multiple times should not cause state leaks."""
        bundle1 = orchestrator.run(SAMPLE_RAW_INPUT)
        bundle2 = orchestrator.run({
            "record_id": "REC002",
            "patient_id": "P002",
            "query": "Headache",
            "symptoms": ["Headache"],
            "vitals": {},
        })
        assert bundle1.record_id == "REC001"
        assert bundle2.record_id == "REC002"
        assert bundle2.labels == []  # No vitals → no labels

    def test_high_vitals_produce_correct_labels(self, orchestrator: PulsePanelOrchestrator):
        """Very high vital values should trigger the correct rules."""
        bundle = orchestrator.run({
            "record_id": "REC_HIGH",
            "patient_id": "P_HIGH",
            "query": "Feeling unwell",
            "vitals": {"SpO2": 80, "HR": 140, "temp": 39.5, "BP": "160/100"},
        })
        label_names = {lbl.label for lbl in bundle.labels}
        assert "severe_hypoxia" in label_names
        assert "tachycardia" in label_names
        assert "fever" in label_names
        assert "hypertension" in label_names

    def test_low_vitals_produce_correct_labels(self, orchestrator: PulsePanelOrchestrator):
        """Very low vital values should trigger the correct rules."""
        bundle = orchestrator.run({
            "record_id": "REC_LOW",
            "patient_id": "P_LOW",
            "query": "Feeling faint",
            "vitals": {"HR": 50, "temp": 34.0, "BP": "85/55"},
        })
        label_names = {lbl.label for lbl in bundle.labels}
        assert "bradycardia" in label_names
        assert "hypothermia" in label_names
        assert "hypotension" in label_names


class TestRetrieverCoverage:
    """Test that all retrieval paths contribute results."""

    def test_semantic_retriever_contributes(self, orchestrator: PulsePanelOrchestrator):
        """At least one result should come from semantic retrieval."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        sources = {src for r in bundle.results for src in r.retrieval_sources}
        assert "semantic" in sources

    def test_keyword_retriever_contributes(self, orchestrator: PulsePanelOrchestrator):
        """At least one result should come from keyword retrieval."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        sources = {src for r in bundle.results for src in r.retrieval_sources}
        assert "keyword" in sources

    def test_symbolic_retriever_contributes(self, orchestrator: PulsePanelOrchestrator):
        """At least one result should come from symbolic retrieval."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        sources = {src for r in bundle.results for src in r.retrieval_sources}
        assert "symbolic" in sources

    def test_graph_retriever_contributes(self, orchestrator: PulsePanelOrchestrator):
        """At least one result should come from graph retrieval."""
        bundle = orchestrator.run(SAMPLE_RAW_INPUT)
        sources = {src for r in bundle.results for src in r.retrieval_sources}
        assert "graph" in sources

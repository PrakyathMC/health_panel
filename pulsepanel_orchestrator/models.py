"""Data models shared across the orchestration layer.

RAG input contracts come from :mod:`pulsepanel_rag.models`, which is the
single validation boundary for both standalone and orchestrated use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pulsepanel_rag.models import ClinicalLabel, ClinicalRecord, Symptom, VitalSigns


@dataclass(frozen=True)
class KnowledgeDocument:
    """A document in the clinical knowledge base."""

    doc_id: str
    title: str
    condition: str
    text: str
    keywords: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    risk_concepts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalResult:
    """A single retrieval result with provenance."""

    rank: int
    title: str
    condition: str
    score: float
    retrieval_sources: list[str] = field(default_factory=list)
    evidence: list[dict[str, str]] = field(default_factory=list)
    explanation: str = ""


@dataclass(frozen=True)
class RetrievalBundle:
    """The complete retrieval output returned to the caller."""

    record_id: str
    patient_id: str
    embedding_text: str
    labels: list[ClinicalLabel] = field(default_factory=list)
    results: list[RetrievalResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

"""Core data models shared across the orchestration layer.

These models define the contracts between tools. They mirror the Pydantic
models in pulsepanel_rag/models.py for seamless integration later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Symptom:
    """A single symptom reported by a patient."""

    name: str
    severity: str | None = None
    duration: str | None = None


@dataclass(frozen=True)
class VitalSigns:
    """Canonical vital signs with standardised keys."""

    spo2: float | None = None
    heart_rate: float | None = None
    temperature_c: float | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    respiratory_rate: float | None = None


@dataclass(frozen=True)
class ClinicalRecord:
    """A normalised clinical encounter record."""

    record_id: str
    patient_id: str
    query: str
    symptoms: list[Symptom] = field(default_factory=list)
    vitals: VitalSigns | None = None
    source: list[str] = field(default_factory=list)
    visit_id: str | None = None


@dataclass(frozen=True)
class ClinicalLabel:
    """A deterministic label derived from clinical rules."""

    label: str
    fact: str
    risk_concept: str
    rule: str
    evidence: dict[str, Any] = field(default_factory=dict)


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

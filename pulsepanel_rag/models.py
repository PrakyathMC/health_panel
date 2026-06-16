from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Symptom:
    name: str
    severity: str | None = None
    duration: str | None = None


@dataclass(frozen=True)
class ClinicalRecord:
    record_id: str
    patient_id: str
    query: str
    symptoms: list[Symptom] = field(default_factory=list)
    vitals: dict[str, float | int | str] = field(default_factory=dict)
    source: list[str] = field(default_factory=list)
    visit_id: str | None = None


@dataclass(frozen=True)
class ClinicalLabel:
    label: str
    fact: str
    risk_concept: str | None
    rule: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    title: str
    condition: str
    text: str
    keywords: set[str]
    labels: set[str]
    risk_concepts: set[str]


@dataclass(frozen=True)
class RetrievalResult:
    rank: int
    title: str
    condition: str
    score: float
    retrieval_sources: list[str]
    evidence: list[str]
    explanation: str


@dataclass(frozen=True)
class RetrievalBundle:
    record_id: str
    patient_id: str
    embedding_text: str
    labels: list[ClinicalLabel]
    results: list[RetrievalResult]


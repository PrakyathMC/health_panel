"""Tool 6 — SymbolicRetriever.

Performs exact matching of clinical labels and risk concepts between
the derived labels and the knowledge base. This is a deterministic,
high-precision retrieval path.
"""

from __future__ import annotations

from ..base import BaseTool
from ..context import OrchestrationContext
from ..models import RetrievalResult

from ..data.knowledge_base import KNOWLEDGE_DOCUMENTS as _BUILTIN_KNOWLEDGE


class SymbolicRetriever(BaseTool):
    """Match clinical labels and risk concepts against the knowledge base."""

    def __init__(self, knowledge_base: list[KnowledgeDocument] | None = None) -> None:
        self._knowledge = knowledge_base or _BUILTIN_KNOWLEDGE

    @property
    def name(self) -> str:
        return "SymbolicRetriever"

    @property
    def dependencies(self) -> list[str]:
        return ["ClinicalRuleEngine"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        if not ctx.labels:
            ctx.symbolic_results = []
            return ctx

        # Collect patient labels and risk concepts
        patient_labels = {lbl.label for lbl in ctx.labels}
        patient_risks = {lbl.risk_concept for lbl in ctx.labels}

        scored: list[tuple[float, KnowledgeDocument, list[str], list[str]]] = []

        for doc in self._knowledge:
            matched_labels = patient_labels & set(doc.labels)
            matched_risks = patient_risks & set(doc.risk_concepts)

            # Score: label match = 1.0 each, risk match = 0.7 each
            label_score = len(matched_labels) * 1.0
            risk_score = len(matched_risks) * 0.7
            total_score = label_score + risk_score

            if total_score > 0:
                scored.append((total_score, doc, list(matched_labels), list(matched_risks)))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[RetrievalResult] = []
        for rank, (score, doc, matched_labels, matched_risks) in enumerate(scored[:10], start=1):
            evidence_parts = []
            if matched_labels:
                evidence_parts.append({"matched_labels": ", ".join(matched_labels)})
            if matched_risks:
                evidence_parts.append({"matched_risks": ", ".join(matched_risks)})

            results.append(
                RetrievalResult(
                    rank=rank,
                    title=doc.title,
                    condition=doc.condition,
                    score=round(score, 4),
                    retrieval_sources=["symbolic"],
                    evidence=evidence_parts,
                    explanation="",
                )
            )

        ctx.symbolic_results = results
        return ctx

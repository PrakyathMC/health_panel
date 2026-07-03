"""Tool 7 — GraphRetriever.

Traverses the clinical knowledge graph to find related conditions.
Phase 1 uses an in-memory graph representation using the built-in
knowledge base. Phase 2 connects to Neo4jAdapter for production
graph traversal with Cypher queries.
"""

from __future__ import annotations

from ..base import BaseTool
from ..context import OrchestrationContext
from ..models import RetrievalResult

from ..data.knowledge_base import (
    KNOWLEDGE_BY_ID as _BUILTIN_KNOWLEDGE,
    LABEL_TO_CONDITION as _LABEL_TO_CONDITION,
    RISK_TO_CONDITION as _RISK_TO_CONDITION,
)


class GraphRetriever(BaseTool):
    """Traverse the clinical graph from labels/risks to conditions.

    Phase 1: in-memory traversal.
    Phase 2: Cypher queries against Neo4j via Neo4jAdapter.
    """

    @property
    def name(self) -> str:
        return "GraphRetriever"

    @property
    def dependencies(self) -> list[str]:
        return ["ClinicalRuleEngine"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        if not ctx.labels:
            ctx.graph_results = []
            return ctx

        # Collect paths from labels and risks
        doc_scores: dict[str, float] = {}
        doc_evidence: dict[str, list[str]] = {}
        doc_paths: dict[str, list[str]] = {}

        for lbl in ctx.labels:
            # Traverse label → condition
            for doc_id, path_desc in _LABEL_TO_CONDITION.get(lbl.label, []):
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1.0
                if doc_id not in doc_evidence:
                    doc_evidence[doc_id] = []
                doc_evidence[doc_id].append(f"Label '{lbl.label}' → {path_desc}")
                doc_paths.setdefault(doc_id, []).append("graph")

            # Traverse risk → condition
            for doc_id, path_desc in _RISK_TO_CONDITION.get(lbl.risk_concept, []):
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 0.7
                if doc_id not in doc_evidence:
                    doc_evidence[doc_id] = []
                doc_evidence[doc_id].append(f"Risk '{lbl.risk_concept}' → {path_desc}")
                doc_paths.setdefault(doc_id, []).append("graph")

        if not doc_scores:
            ctx.graph_results = []
            return ctx

        # Sort by score descending
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        results: list[RetrievalResult] = []
        for rank, (doc_id, score) in enumerate(sorted_docs[:10], start=1):
            doc = _BUILTIN_KNOWLEDGE.get(doc_id)
            if doc is None:
                continue
            results.append(
                RetrievalResult(
                    rank=rank,
                    title=doc.title,
                    condition=doc.condition,
                    score=round(score, 4),
                    retrieval_sources=["graph"],
                    evidence=[{"path": "; ".join(doc_evidence.get(doc_id, []))}],
                    explanation="",
                )
            )

        ctx.graph_results = results
        return ctx

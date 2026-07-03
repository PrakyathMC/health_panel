"""Tool 8 — ResultMerger.

Merges, deduplicates, and ranks retrieval results from all four retrieval
paths (semantic, keyword, symbolic, graph) using configured weights.
"""

from __future__ import annotations

from ..base import BaseTool
from ..config.settings import settings
from ..context import OrchestrationContext
from ..models import RetrievalResult


class ResultMerger(BaseTool):
    """Merge, deduplicate, and rank results from all retrieval paths."""

    def __init__(
        self,
        top_k: int | None = None,
        semantic_weight: float | None = None,
        keyword_weight: float | None = None,
        symbolic_weight: float | None = None,
        graph_weight: float | None = None,
    ) -> None:
        self._top_k = top_k if top_k is not None else settings.top_k
        self._semantic_weight = (
            semantic_weight if semantic_weight is not None else settings.semantic_weight
        )
        self._keyword_weight = (
            keyword_weight if keyword_weight is not None else settings.keyword_weight
        )
        self._symbolic_weight = (
            symbolic_weight if symbolic_weight is not None else settings.symbolic_weight
        )
        self._graph_weight = (
            graph_weight if graph_weight is not None else settings.graph_weight
        )

    @property
    def name(self) -> str:
        return "ResultMerger"

    @property
    def dependencies(self) -> list[str]:
        return ["SemanticRetriever", "KeywordRetriever", "SymbolicRetriever", "GraphRetriever"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        # Collect all results tagged with their path + weight
        path_weights = {
            "semantic": self._semantic_weight,
            "keyword": self._keyword_weight,
            "symbolic": self._symbolic_weight,
            "graph": self._graph_weight,
        }

        path_results = {
            "semantic": ctx.semantic_results,
            "keyword": ctx.keyword_results,
            "symbolic": ctx.symbolic_results,
            "graph": ctx.graph_results,
        }

        # Aggregate scores by doc_id (identified by title+condition)
        doc_scores: dict[tuple[str, str], float] = {}
        doc_sources: dict[tuple[str, str], list[str]] = {}
        doc_evidence: dict[tuple[str, str], list[dict[str, str]]] = {}
        doc_meta: dict[tuple[str, str], tuple[str, str]] = {}  # (title, condition)

        for path, results in path_results.items():
            weight = path_weights.get(path, 0.25)
            for result in results:
                key = (result.title, result.condition)
                # Apply path weight to the result's score
                weighted_score = result.score * weight
                doc_scores[key] = doc_scores.get(key, 0.0) + weighted_score
                if key not in doc_sources:
                    doc_sources[key] = []
                if path not in doc_sources[key]:
                    doc_sources[key].append(path)
                if result.evidence:
                    if key not in doc_evidence:
                        doc_evidence[key] = []
                    doc_evidence[key].extend(result.evidence)
                doc_meta[key] = (result.title, result.condition)

        # Sort by aggregated score descending
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # Build merged results
        merged: list[RetrievalResult] = []
        for rank, (key, score) in enumerate(sorted_docs[: self._top_k], start=1):
            title, condition = key
            merged.append(
                RetrievalResult(
                    rank=rank,
                    title=title,
                    condition=condition,
                    score=round(score, 4),
                    retrieval_sources=doc_sources.get(key, []),
                    evidence=doc_evidence.get(key, []),
                    explanation="",
                )
            )

        ctx.merged_results = merged
        return ctx

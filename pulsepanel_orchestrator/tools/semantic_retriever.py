"""Tool 4 — SemanticRetriever.

Performs semantic similarity search against the knowledge base using
cosine similarity on tokenised text.  In Phase 1 this runs in-memory;
in Phase 2 it delegates to QdrantAdapter for production vector search.
"""

from __future__ import annotations

import math
from collections import Counter

from ..base import BaseTool
from ..context import OrchestrationContext
from ..errors import ToolExecutionError
from ..models import RetrievalResult

from ..data.knowledge_base import KNOWLEDGE_DOCUMENTS as _BUILTIN_KNOWLEDGE


class SemanticRetriever(BaseTool):
    """Search the knowledge base by semantic similarity (cosine on tokens).

    Phase 1 uses an in-memory knowledge base with basic token vectorisation.
    Phase 2 swaps to QdrantAdapter for production-grade vector search.
    """

    def __init__(self, knowledge_base: list[KnowledgeDocument] | None = None) -> None:
        self._knowledge = knowledge_base or _BUILTIN_KNOWLEDGE
        # Pre-compute token vectors for the knowledge base
        self._doc_vectors: dict[str, Counter[str]] = {}
        for doc in self._knowledge:
            self._doc_vectors[doc.doc_id] = self._tokenize(doc.text + " " + doc.title)

    @property
    def name(self) -> str:
        return "SemanticRetriever"

    @property
    def dependencies(self) -> list[str]:
        return ["EmbeddingTextBuilder"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        if not ctx.embedding_text:
            raise ToolExecutionError(
                "No embedding text found — EmbeddingTextBuilder must run first.",
                tool=self.name,
            )

        query_vec = self._tokenize(ctx.embedding_text)
        scored: list[tuple[float, KnowledgeDocument]] = []

        for doc in self._knowledge:
            doc_vec = self._doc_vectors[doc.doc_id]
            sim = self._cosine_similarity(query_vec, doc_vec)
            scored.append((sim, doc))

        # Sort descending by similarity
        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[RetrievalResult] = []
        for rank, (score, doc) in enumerate(scored[:10], start=1):
            results.append(
                RetrievalResult(
                    rank=rank,
                    title=doc.title,
                    condition=doc.condition,
                    score=round(score, 4),
                    retrieval_sources=["semantic"],
                    evidence=[{"similarity": str(round(score, 4))}],
                    explanation="",
                )
            )

        ctx.semantic_results = results
        return ctx

    # ------------------------------------------------------------------
    # Vector helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> Counter[str]:
        """Convert text to a token-frequency counter."""
        import re as _re
        tokens = _re.findall(r"[a-zA-Z0-9]+", text.lower())
        return Counter(tokens)

    @staticmethod
    def _cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
        """Cosine similarity between two token-frequency vectors."""
        intersection = set(left.keys()) & set(right.keys())
        dot_product = sum(left[t] * right[t] for t in intersection)
        norm_left = math.sqrt(sum(v * v for v in left.values()))
        norm_right = math.sqrt(sum(v * v for v in right.values()))
        if norm_left == 0 or norm_right == 0:
            return 0.0
        return dot_product / (norm_left * norm_right)

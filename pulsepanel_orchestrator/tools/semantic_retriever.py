"""Tool 4 - SemanticRetriever.

Performs semantic similarity search. Local tests can use the in-memory
token retriever, while production can enable Qdrant/OpenAI vector search.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from ..base import BaseTool
from ..config.settings import settings
from ..context import OrchestrationContext
from ..errors import ToolExecutionError
from ..models import KnowledgeDocument, RetrievalResult

from ..data.knowledge_base import KNOWLEDGE_DOCUMENTS as _BUILTIN_KNOWLEDGE


class SemanticRetriever(BaseTool):
    """Search the clinical knowledge base by semantic similarity.

    By default this keeps the in-memory token implementation for fast local
    tests. Set ``PULSEPANEL_ENABLE_QDRANT_SEMANTIC=true`` or inject a vector
    adapter to use OpenAI embeddings with Qdrant.
    """

    def __init__(
        self,
        knowledge_base: list[KnowledgeDocument] | None = None,
        vector_adapter: Any | None = None,
        use_vector_store: bool | None = None,
        top_k: int | None = None,
        auto_ingest: bool = True,
    ) -> None:
        self._knowledge = knowledge_base or _BUILTIN_KNOWLEDGE
        self._vector_adapter = vector_adapter
        self._use_vector_store = (
            settings.enable_qdrant_semantic if use_vector_store is None else use_vector_store
        )
        self._top_k = top_k or settings.top_k
        self._auto_ingest = auto_ingest
        self._vector_store_ready = False

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
                "No embedding text found; EmbeddingTextBuilder must run first.",
                tool=self.name,
            )

        if self._use_vector_store:
            return self._run_vector_store(ctx)
        return self._run_in_memory(ctx)

    # ------------------------------------------------------------------
    # Qdrant/OpenAI vector retrieval
    # ------------------------------------------------------------------

    def _run_vector_store(self, ctx: OrchestrationContext) -> OrchestrationContext:
        adapter = self._get_vector_adapter()
        if not self._vector_store_ready:
            adapter.connect()
            adapter.ensure_collection()
            if self._auto_ingest:
                adapter.ingest_documents(self._knowledge)
            self._vector_store_ready = True

        matches = adapter.search(ctx.embedding_text, top_k=self._top_k)
        ctx.semantic_results = [
            RetrievalResult(
                rank=rank,
                title=match.get("title", ""),
                condition=match.get("condition", ""),
                score=float(match.get("score", 0.0)),
                retrieval_sources=["semantic", "qdrant"],
                evidence=[
                    {
                        "doc_id": str(match.get("doc_id", "")),
                        "similarity": str(match.get("score", 0.0)),
                    }
                ],
                explanation="",
            )
            for rank, match in enumerate(matches, start=1)
        ]
        return ctx

    def _get_vector_adapter(self) -> Any:
        if self._vector_adapter is None:
            from .adapters import QdrantAdapter

            self._vector_adapter = QdrantAdapter()
        return self._vector_adapter

    # ------------------------------------------------------------------
    # Local token fallback
    # ------------------------------------------------------------------

    def _run_in_memory(self, ctx: OrchestrationContext) -> OrchestrationContext:
        query_vec = self._tokenize(ctx.embedding_text)
        scored: list[tuple[float, KnowledgeDocument]] = []

        for doc in self._knowledge:
            doc_vec = self._doc_vectors[doc.doc_id]
            sim = self._cosine_similarity(query_vec, doc_vec)
            scored.append((sim, doc))

        scored.sort(key=lambda x: x[0], reverse=True)

        ctx.semantic_results = [
            RetrievalResult(
                rank=rank,
                title=doc.title,
                condition=doc.condition,
                score=round(score, 4),
                retrieval_sources=["semantic"],
                evidence=[{"similarity": str(round(score, 4))}],
                explanation="",
            )
            for rank, (score, doc) in enumerate(scored[: self._top_k], start=1)
        ]
        return ctx

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

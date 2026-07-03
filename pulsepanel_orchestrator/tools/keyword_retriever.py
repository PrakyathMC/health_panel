"""Tool 5 — KeywordRetriever.

Performs token-level keyword matching between the patient's symptoms
and the knowledge base document keywords. Returns scored results based
on keyword overlap ratio.
"""

from __future__ import annotations

import re
from ..base import BaseTool
from ..context import OrchestrationContext
from ..models import RetrievalResult

from ..data.knowledge_base import KNOWLEDGE_DOCUMENTS as _BUILTIN_KNOWLEDGE


class KeywordRetriever(BaseTool):
    """Match patient symptoms against knowledge-base keywords."""

    def __init__(self, knowledge_base: list[KnowledgeDocument] | None = None) -> None:
        self._knowledge = knowledge_base or _BUILTIN_KNOWLEDGE

    @property
    def name(self) -> str:
        return "KeywordRetriever"

    @property
    def dependencies(self) -> list[str]:
        return ["InputNormalizer"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        if ctx.record is None:
            return ctx

        # Collect all symptom names + query tokens from the record
        symptom_tokens: set[str] = set()
        for symptom in ctx.record.symptoms:
            for token in self._tokenize(symptom.name):
                symptom_tokens.add(token)

        # Also include query tokens
        if ctx.record.query:
            for token in self._tokenize(ctx.record.query):
                symptom_tokens.add(token)

        if not symptom_tokens:
            ctx.keyword_results = []
            return ctx

        scored: list[tuple[float, KnowledgeDocument]] = []
        for doc in self._knowledge:
            # Collect all keyword tokens for this document
            doc_keyword_tokens: set[str] = set()
            for kw in doc.keywords:
                for token in self._tokenize(kw):
                    doc_keyword_tokens.add(token)

            if not doc_keyword_tokens:
                continue

            # Jaccard-like overlap
            overlap = len(symptom_tokens & doc_keyword_tokens)
            total = len(symptom_tokens | doc_keyword_tokens)
            score = overlap / total if total > 0 else 0.0
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[RetrievalResult] = []
        for rank, (score, doc) in enumerate(scored[:10], start=1):
            if score <= 0:
                continue
            matched_keywords = [
                kw for kw in doc.keywords
                if any(t in symptom_tokens for t in self._tokenize(kw))
            ]
            results.append(
                RetrievalResult(
                    rank=rank,
                    title=doc.title,
                    condition=doc.condition,
                    score=round(score, 4),
                    retrieval_sources=["keyword"],
                    evidence=[{"matched_keywords": ", ".join(matched_keywords)}],
                    explanation="",
                )
            )

        ctx.keyword_results = results
        return ctx

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Extract unique lowercase alphanumeric tokens from text."""
        return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))

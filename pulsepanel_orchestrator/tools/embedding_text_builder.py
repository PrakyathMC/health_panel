"""Orchestrator wrapper for the canonical RAG embedding-text builder."""

from __future__ import annotations

from pulsepanel_rag.embedding_text import build_embedding_payload, build_embedding_text
from pulsepanel_rag.models import ClinicalLabel, ClinicalRecord

from ..base import BaseTool
from ..context import OrchestrationContext
from ..errors import ToolExecutionError


class EmbeddingTextBuilder(BaseTool):
    """Build embedding text through the shared RAG implementation."""

    @property
    def name(self) -> str:
        return "EmbeddingTextBuilder"

    @property
    def dependencies(self) -> list[str]:
        return ["InputNormalizer", "ClinicalRuleEngine"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        if ctx.record is None:
            raise ToolExecutionError(
                "No ClinicalRecord found - InputNormalizer must run first.",
                tool=self.name,
            )

        ctx.embedding_text = build_embedding_text(ctx.record, ctx.labels or [])
        return ctx

    @staticmethod
    def _build_text(record: ClinicalRecord, labels: list[ClinicalLabel]) -> str:
        """Keep the existing helper API while delegating to shared RAG logic."""
        return build_embedding_text(record, labels)

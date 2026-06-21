"""Orchestrator wrapper for the canonical RAG clinical rule engine."""

from __future__ import annotations

from pulsepanel_rag.clinical_rules import derive_clinical_labels
from pulsepanel_rag.models import ClinicalLabel, VitalSigns

from ..base import BaseTool
from ..context import OrchestrationContext
from ..errors import ToolExecutionError


class ClinicalRuleEngine(BaseTool):
    """Apply the shared deterministic clinical rules to normalized vitals."""

    @property
    def name(self) -> str:
        return "ClinicalRuleEngine"

    @property
    def dependencies(self) -> list[str]:
        return ["InputNormalizer"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        if ctx.record is None:
            raise ToolExecutionError(
                "No ClinicalRecord found - InputNormalizer must run first.",
                tool=self.name,
            )

        ctx.labels = derive_clinical_labels(ctx.record.vitals)
        return ctx

    @staticmethod
    def _derive_labels(vitals: VitalSigns) -> list[ClinicalLabel]:
        """Keep the existing helper API while delegating to shared RAG logic."""
        return derive_clinical_labels(vitals)

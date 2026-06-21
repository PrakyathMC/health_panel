"""Tool 2 — ClinicalRuleEngine.

Derives deterministic clinical labels, facts, and risk concepts from
raw vital signs using threshold-based rules. Results are auditable:
every label includes the rule name and evidence that triggered it.
"""

from __future__ import annotations

from __future__ import annotations

from typing import Any

from ..base import BaseTool
from ..config.rules import CLINICAL_RULE_DEFS, ClinicalRuleDef
from ..context import OrchestrationContext
from ..errors import ToolExecutionError
from ..models import ClinicalLabel, VitalSigns


def derive_clinical_labels(vitals: VitalSigns) -> list[ClinicalLabel]:
    """Convenience function: derive labels from vitals without the full pipeline.

    Note: Accepts only VitalSigns objects, not raw dicts.
    Use InputNormalizer first to convert dicts to VitalSigns.
    """
    engine = ClinicalRuleEngine()
    return engine._derive_labels(vitals)


class ClinicalRuleEngine(BaseTool):
    """Apply deterministic clinical rules to vitals and produce labels."""

    @property
    def name(self) -> str:
        return "ClinicalRuleEngine"

    @property
    def dependencies(self) -> list[str]:
        return ["InputNormalizer"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        if ctx.record is None:
            raise ToolExecutionError(
                "No ClinicalRecord found — InputNormalizer must run first.",
                tool=self.name,
            )

        vitals = ctx.record.vitals
        if vitals is None:
            ctx.labels = []
            return ctx

        ctx.labels = self._derive_labels(vitals)
        return ctx

    # ------------------------------------------------------------------
    # Rule-checking logic
    # ------------------------------------------------------------------

    def _derive_labels(self, vitals: VitalSigns) -> list[ClinicalLabel]:
        """Derive labels from a VitalSigns object (internal helper)."""
        labels: list[ClinicalLabel] = []
        for rule_def in CLINICAL_RULE_DEFS:
            evidence = self._check_rule(rule_def, vitals)
            if evidence is not None:
                labels.append(
                    ClinicalLabel(
                        label=rule_def.label,
                        fact=rule_def.fact,
                        risk_concept=rule_def.risk_concept,
                        rule=rule_def.name,
                        evidence=evidence,
                    )
                )
        return labels

    @staticmethod
    def _check_rule(
        rule_def: ClinicalRuleDef, vitals: VitalSigns
    ) -> dict[str, object] | None:
        """Check if a clinical rule is triggered by the vitals.

        Returns evidence dict if triggered, None otherwise.
        """
        v = vitals

        if rule_def.name == "hypoxia_rule":
            if v.spo2 is not None and v.spo2 < 92:
                return {"spo2": v.spo2}

        if rule_def.name == "severe_hypoxia_rule":
            if v.spo2 is not None and v.spo2 < 85:
                return {"spo2": v.spo2}

        if rule_def.name == "tachycardia_rule":
            if v.heart_rate is not None and v.heart_rate > 100:
                return {"heart_rate": v.heart_rate}

        if rule_def.name == "bradycardia_rule":
            if v.heart_rate is not None and v.heart_rate < 60:
                return {"heart_rate": v.heart_rate}

        if rule_def.name == "fever_rule":
            if v.temperature_c is not None and v.temperature_c > 37.5:
                return {"temperature_c": v.temperature_c}

        if rule_def.name == "hypothermia_rule":
            if v.temperature_c is not None and v.temperature_c < 35.0:
                return {"temperature_c": v.temperature_c}

        if rule_def.name == "hypertension_rule":
            if (v.systolic_bp is not None and v.systolic_bp >= 140) or (
                v.diastolic_bp is not None and v.diastolic_bp >= 90
            ):
                evidence: dict[str, object] = {}
                if v.systolic_bp is not None and v.systolic_bp >= 140:
                    evidence["systolic_bp"] = v.systolic_bp
                if v.diastolic_bp is not None and v.diastolic_bp >= 90:
                    evidence["diastolic_bp"] = v.diastolic_bp
                return evidence

        if rule_def.name == "hypotension_rule":
            if (v.systolic_bp is not None and v.systolic_bp < 90) or (
                v.diastolic_bp is not None and v.diastolic_bp < 60
            ):
                evidence = {}
                if v.systolic_bp is not None and v.systolic_bp < 90:
                    evidence["systolic_bp"] = v.systolic_bp
                if v.diastolic_bp is not None and v.diastolic_bp < 60:
                    evidence["diastolic_bp"] = v.diastolic_bp
                return evidence

        if rule_def.name == "tachypnea_rule":
            if v.respiratory_rate is not None and v.respiratory_rate > 20:
                return {"respiratory_rate": v.respiratory_rate}

        return None

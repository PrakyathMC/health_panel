from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .models import ClinicalLabel, VitalSigns


@dataclass(frozen=True)
class ClinicalRule:
    name: str
    label: str
    fact: str
    risk_concept: str
    rule_text: str
    evidence_keys: tuple[str, ...]


CLINICAL_RULES = [
    ClinicalRule(
        name="severe_hypoxia_rule",
        label="severe_hypoxia",
        fact="oxygen saturation is critically low",
        risk_concept="respiratory failure",
        rule_text="spo2 < 85",
        evidence_keys=("spo2",),
    ),
    ClinicalRule(
        name="hypoxia_rule",
        label="hypoxia",
        fact="oxygen saturation is below normal threshold",
        risk_concept="respiratory distress",
        rule_text="spo2 < 92",
        evidence_keys=("spo2",),
    ),
    ClinicalRule(
        name="tachycardia_rule",
        label="tachycardia",
        fact="heart rate is elevated",
        risk_concept="cardiac risk",
        rule_text="heart_rate > 100",
        evidence_keys=("heart_rate",),
    ),
    ClinicalRule(
        name="bradycardia_rule",
        label="bradycardia",
        fact="heart rate is below normal",
        risk_concept="cardiac risk",
        rule_text="heart_rate < 60",
        evidence_keys=("heart_rate",),
    ),
    ClinicalRule(
        name="fever_rule",
        label="fever",
        fact="body temperature is high",
        risk_concept="infection risk",
        rule_text="temperature_c > 37.5",
        evidence_keys=("temperature_c",),
    ),
    ClinicalRule(
        name="hypothermia_rule",
        label="hypothermia",
        fact="body temperature is below normal",
        risk_concept="exposure risk",
        rule_text="temperature_c < 35.0",
        evidence_keys=("temperature_c",),
    ),
    ClinicalRule(
        name="hypertension_rule",
        label="hypertension",
        fact="blood pressure is elevated",
        risk_concept="cardiovascular risk",
        rule_text="systolic_bp >= 140 or diastolic_bp >= 90",
        evidence_keys=("systolic_bp", "diastolic_bp"),
    ),
    ClinicalRule(
        name="hypotension_rule",
        label="hypotension",
        fact="blood pressure is below normal",
        risk_concept="shock risk",
        rule_text="systolic_bp < 90",
        evidence_keys=("systolic_bp",),
    ),
    ClinicalRule(
        name="tachypnea_rule",
        label="tachypnea",
        fact="respiratory rate is elevated",
        risk_concept="respiratory distress",
        rule_text="respiratory_rate > 20",
        evidence_keys=("respiratory_rate",),
    ),
]


def _number(vitals: Mapping[str, Any] | VitalSigns, key: str) -> float | None:
    if isinstance(vitals, VitalSigns):
        value = getattr(vitals, key)
    else:
        value = vitals.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ClinicalRuleEngine:
    def __init__(self, rules: list[ClinicalRule] | None = None) -> None:
        self.rules = rules or CLINICAL_RULES

    def derive_labels(self, vitals: Mapping[str, Any] | VitalSigns) -> list[ClinicalLabel]:
        labels: list[ClinicalLabel] = []
        for rule in self.rules:
            if self._matches(rule, vitals):
                labels.append(
                    ClinicalLabel(
                        label=rule.label,
                        fact=rule.fact,
                        risk_concept=rule.risk_concept,
                        rule=rule.rule_text,
                        evidence=self._evidence(rule, vitals),
                    )
                )
        return labels

    def _matches(self, rule: ClinicalRule, vitals: Mapping[str, Any] | VitalSigns) -> bool:
        spo2 = _number(vitals, "spo2")
        heart_rate = _number(vitals, "heart_rate")
        temperature_c = _number(vitals, "temperature_c")
        systolic_bp = _number(vitals, "systolic_bp")
        diastolic_bp = _number(vitals, "diastolic_bp")
        respiratory_rate = _number(vitals, "respiratory_rate")

        if rule.name == "severe_hypoxia_rule":
            return spo2 is not None and spo2 < 85
        if rule.name == "hypoxia_rule":
            return spo2 is not None and spo2 < 92
        if rule.name == "tachycardia_rule":
            return heart_rate is not None and heart_rate > 100
        if rule.name == "bradycardia_rule":
            return heart_rate is not None and heart_rate < 60
        if rule.name == "fever_rule":
            return temperature_c is not None and temperature_c > 37.5
        if rule.name == "hypothermia_rule":
            return temperature_c is not None and temperature_c < 35.0
        if rule.name == "hypertension_rule":
            return (
                systolic_bp is not None
                and diastolic_bp is not None
                and (systolic_bp >= 140 or diastolic_bp >= 90)
            )
        if rule.name == "hypotension_rule":
            return systolic_bp is not None and systolic_bp < 90
        if rule.name == "tachypnea_rule":
            return respiratory_rate is not None and respiratory_rate > 20
        return False

    def _evidence(
        self,
        rule: ClinicalRule,
        vitals: Mapping[str, Any] | VitalSigns,
    ) -> dict[str, float]:
        evidence: dict[str, float] = {}
        for key in rule.evidence_keys:
            value = _number(vitals, key)
            if value is not None:
                evidence[key] = value
        return evidence


def derive_clinical_labels(vitals: Mapping[str, Any] | VitalSigns) -> list[ClinicalLabel]:
    return ClinicalRuleEngine().derive_labels(vitals)

    return labels

"""Clinical rule definitions — extensible registry.

Each rule maps a vital-sign threshold to a clinical label, fact,
risk concept, and human-readable description.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClinicalRuleDef:
    """Definition of a single deterministic clinical rule."""

    name: str
    label: str
    fact: str
    risk_concept: str
    description: str
    required_vitals: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Built-in rules
# ---------------------------------------------------------------------------

CLINICAL_RULE_DEFS: list[ClinicalRuleDef] = [
    ClinicalRuleDef(
        name="hypoxia_rule",
        label="hypoxia",
        fact="oxygen saturation below normal threshold",
        risk_concept="respiratory distress",
        description="SpO2 < 92 indicates hypoxia — patient may need supplemental oxygen.",
        required_vitals=["spo2"],
    ),
    ClinicalRuleDef(
        name="severe_hypoxia_rule",
        label="severe_hypoxia",
        fact="oxygen saturation critically low",
        risk_concept="respiratory failure",
        description="SpO2 < 85 indicates severe hypoxia — urgent intervention required.",
        required_vitals=["spo2"],
    ),
    ClinicalRuleDef(
        name="tachycardia_rule",
        label="tachycardia",
        fact="heart rate is elevated",
        risk_concept="cardiac risk",
        description="Heart rate > 100 bpm indicates tachycardia.",
        required_vitals=["heart_rate"],
    ),
    ClinicalRuleDef(
        name="bradycardia_rule",
        label="bradycardia",
        fact="heart rate is below normal",
        risk_concept="cardiac risk",
        description="Heart rate < 60 bpm indicates bradycardia.",
        required_vitals=["heart_rate"],
    ),
    ClinicalRuleDef(
        name="fever_rule",
        label="fever",
        fact="body temperature is high",
        risk_concept="infection risk",
        description="Temperature > 37.5°C indicates fever — possible infection.",
        required_vitals=["temperature_c"],
    ),
    ClinicalRuleDef(
        name="hypothermia_rule",
        label="hypothermia",
        fact="body temperature is below normal",
        risk_concept="exposure risk",
        description="Temperature < 35.0°C indicates hypothermia.",
        required_vitals=["temperature_c"],
    ),
    ClinicalRuleDef(
        name="hypertension_rule",
        label="hypertension",
        fact="blood pressure is elevated",
        risk_concept="cardiac risk",
        description="BP systolic >= 140 or diastolic >= 90 indicates hypertension.",
        required_vitals=["systolic_bp", "diastolic_bp"],
    ),
    ClinicalRuleDef(
        name="hypotension_rule",
        label="hypotension",
        fact="blood pressure is below normal",
        risk_concept="shock risk",
        description="BP systolic < 90 or diastolic < 60 indicates hypotension.",
        required_vitals=["systolic_bp", "diastolic_bp"],
    ),
    ClinicalRuleDef(
        name="tachypnea_rule",
        label="tachypnea",
        fact="respiratory rate is elevated",
        risk_concept="respiratory distress",
        description="Respiratory rate > 20 breaths/min indicates tachypnea.",
        required_vitals=["respiratory_rate"],
    ),
]


def get_rule_def(name: str) -> ClinicalRuleDef | None:
    """Look up a rule definition by name."""
    for r in CLINICAL_RULE_DEFS:
        if r.name == name:
            return r
    return None

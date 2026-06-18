from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import ClinicalLabel, VitalSigns


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


def derive_clinical_labels(
    vitals: Mapping[str, Any] | VitalSigns,
) -> list[ClinicalLabel]:
    labels: list[ClinicalLabel] = []

    spo2 = _number(vitals, "spo2")
    if spo2 is not None and spo2 < 92:
        labels.append(
            ClinicalLabel(
                label="hypoxia",
                fact="oxygen saturation is below normal threshold",
                risk_concept="respiratory distress",
                rule="spo2 < 92",
                evidence={"spo2": spo2},
            )
        )

    heart_rate = _number(vitals, "heart_rate")
    if heart_rate is not None and heart_rate > 100:
        labels.append(
            ClinicalLabel(
                label="tachycardia",
                fact="heart rate is elevated",
                risk_concept="cardiac risk",
                rule="heart_rate > 100",
                evidence={"heart_rate": heart_rate},
            )
        )

    temperature_c = _number(vitals, "temperature_c")
    if temperature_c is not None and temperature_c > 37.5:
        labels.append(
            ClinicalLabel(
                label="fever",
                fact="body temperature is high",
                risk_concept="infection risk",
                rule="temperature_c > 37.5",
                evidence={"temperature_c": temperature_c},
            )
        )

    systolic_bp = _number(vitals, "systolic_bp")
    diastolic_bp = _number(vitals, "diastolic_bp")
    if (
        systolic_bp is not None
        and diastolic_bp is not None
        and (systolic_bp >= 140 or diastolic_bp >= 90)
    ):
        labels.append(
            ClinicalLabel(
                label="hypertension",
                fact="blood pressure is elevated",
                risk_concept="cardiovascular risk",
                rule="systolic_bp >= 140 or diastolic_bp >= 90",
                evidence={"systolic_bp": systolic_bp, "diastolic_bp": diastolic_bp},
            )
        )

    return labels

"""Tool 1 — InputNormalizer.

Validates and normalises raw clinical input into a canonical ClinicalRecord.
Handles vital-name aliases, blood-pressure parsing, symptom normalisation,
and input validation with explicit error messages.
"""

from __future__ import annotations

import re
from typing import Any

from collections.abc import Mapping
from typing import Any

from ..base import BaseTool
from ..context import OrchestrationContext
from ..errors import ValidationError
from ..models import ClinicalRecord, Symptom, VitalSigns


def _first_present(raw_input: Mapping[str, Any], *keys: str) -> Any:
    """Return the first non-None value from the given keys."""
    for key in keys:
        if key in raw_input and raw_input[key] is not None:
            return raw_input[key]
    return None


# ---------------------------------------------------------------------------
# Vital-sign aliases — maps common synonyms to canonical keys
# ---------------------------------------------------------------------------
VITAL_KEY_ALIASES: dict[str, str] = {
    # SpO2
    "spo2": "spo2",
    "spo₂": "spo2",
    "oxygen_saturation": "spo2",
    "o2sat": "spo2",
    "o2": "spo2",
    # Heart rate
    "heart_rate": "heart_rate",
    "hr": "heart_rate",
    "pulse": "heart_rate",
    "heartrate": "heart_rate",
    # Temperature
    "temperature_c": "temperature_c",
    "temp": "temperature_c",
    "temperature": "temperature_c",
    "tmp": "temperature_c",
    # Systolic BP
    "systolic_bp": "systolic_bp",
    "systolic": "systolic_bp",
    "sys": "systolic_bp",
    # Diastolic BP
    "diastolic_bp": "diastolic_bp",
    "diastolic": "diastolic_bp",
    "dia": "diastolic_bp",
    # BP composite
    "bp": "bp",
    "blood_pressure": "bp",
    # Respiratory rate
    "respiratory_rate": "respiratory_rate",
    "rr": "respiratory_rate",
    "respiration": "respiratory_rate",
    "resp_rate": "respiratory_rate",
}

BP_KEYS = {"systolic_bp", "diastolic_bp", "bp", "blood_pressure"}


class InputNormalizer(BaseTool):
    """Validate and normalise raw clinical input into a canonical ClinicalRecord."""

    @property
    def name(self) -> str:
        return "InputNormalizer"

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        raw = ctx.raw_input

        # --- Validate required fields ---
        record_id = _first_present(raw, "record_id", "recordId")
        patient_id = _first_present(raw, "patient_id", "patientId")
        query = _first_present(raw, "query", "message")

        if not record_id:
            raise ValidationError("Missing required field: record_id", field="record_id")
        if not patient_id:
            raise ValidationError("Missing required field: patient_id", field="patient_id")
        if not query:
            raise ValidationError("Missing required field: query or message", field="query")

        # --- Normalise symptoms ---
        symptoms = self._normalize_symptoms(raw.get("symptoms", []))

        # --- Normalise vitals ---
        vitals = self._normalize_vitals(raw.get("vitals", {}))

        # --- Normalise source ---
        source = self._normalize_source(raw.get("source", []))

        # --- Visit ID ---
        visit_id = _first_present(raw, "visit_id", "visitId")

        ctx.record = ClinicalRecord(
            record_id=record_id,
            patient_id=patient_id,
            query=query,
            symptoms=symptoms,
            vitals=vitals,
            source=source,
            visit_id=visit_id,
        )
        return ctx

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_symptoms(raw_symptoms: list[Any]) -> list[Symptom]:
        """Parse symptom input into canonical Symptom objects."""
        result: list[Symptom] = []
        for s in raw_symptoms:
            if isinstance(s, str):
                result.append(Symptom(name=s.strip().lower()))
            elif isinstance(s, dict):
                name = (s.get("name") or s.get("symptom") or "").strip().lower()
                if not name:
                    continue
                severity = s.get("severity")
                duration = s.get("duration")
                result.append(
                    Symptom(
                        name=name,
                        severity=str(severity).strip() if severity else None,
                        duration=str(duration).strip() if duration else None,
                    )
                )
        return result

    @staticmethod
    def _normalize_vitals(raw_vitals: dict[str, Any]) -> VitalSigns | None:
        """Extract and normalise vital signs using alias mapping."""
        if not raw_vitals:
            return None

        normalized: dict[str, float | None] = {
            "spo2": None,
            "heart_rate": None,
            "temperature_c": None,
            "systolic_bp": None,
            "diastolic_bp": None,
            "respiratory_rate": None,
        }

        for raw_key, raw_value in raw_vitals.items():
            key = raw_key.strip().lower().replace(" ", "_")
            canonical = VITAL_KEY_ALIASES.get(key)

            if canonical is None:
                continue

            if canonical == "bp":
                # Handle composite BP strings like "120/80" or dict {"systolic": 120}
                sys_val, dia_val = InputNormalizer._merge_blood_pressure(raw_value)
                if sys_val is not None:
                    normalized["systolic_bp"] = sys_val
                if dia_val is not None:
                    normalized["diastolic_bp"] = dia_val
            elif canonical in BP_KEYS:
                # Single BP key — determine which one
                if "systolic" in canonical or "sys" in key:
                    val = InputNormalizer._number(raw_value)
                    if val is not None:
                        normalized["systolic_bp"] = val
                elif "diastolic" in canonical or "dia" in key:
                    val = InputNormalizer._number(raw_value)
                    if val is not None:
                        normalized["diastolic_bp"] = val
            else:
                val = InputNormalizer._number(raw_value)
                if val is not None and canonical in normalized:
                    normalized[canonical] = val

        # Only create VitalSigns if at least one value was set
        if all(v is None for v in normalized.values()):
            return None

        return VitalSigns(
            spo2=normalized["spo2"],
            heart_rate=normalized["heart_rate"],
            temperature_c=normalized["temperature_c"],
            systolic_bp=normalized["systolic_bp"],
            diastolic_bp=normalized["diastolic_bp"],
            respiratory_rate=normalized["respiratory_rate"],
        )

    @staticmethod
    def _merge_blood_pressure(value: Any) -> tuple[float | None, float | None]:
        """Parse blood pressure from string ('120/80'), dict, or number."""
        if isinstance(value, str):
            match = re.match(r"(\d+)\s*/\s*(\d+)", value.strip())
            if match:
                return float(match.group(1)), float(match.group(2))
        elif isinstance(value, dict):
            sys = InputNormalizer._number(value.get("systolic") or value.get("sys"))
            dia = InputNormalizer._number(value.get("diastolic") or value.get("dia"))
            return sys, dia
        return None, None

    @staticmethod
    def _number(value: Any) -> float | None:
        """Safely cast a value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalize_source(raw_source: Any) -> list[str]:
        """Normalise source field into a list of strings."""
        if not raw_source:
            return []
        if isinstance(raw_source, str):
            return [raw_source.strip().lower()]
        if isinstance(raw_source, list):
            return [str(s).strip().lower() for s in raw_source if s]
        return [str(raw_source).strip().lower()]

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .models import ClinicalRecord


VITAL_KEY_ALIASES = {
    "spo2": "spo2",
    "sp02": "spo2",
    "oxygen_saturation": "spo2",
    "oxygensaturation": "spo2",
    "o2sat": "spo2",
    "hr": "heart_rate",
    "heart_rate": "heart_rate",
    "heartrate": "heart_rate",
    "pulse": "heart_rate",
    "temp": "temperature_c",
    "temperature": "temperature_c",
    "temperature_c": "temperature_c",
    "temperaturec": "temperature_c",
    "systolic": "systolic_bp",
    "systolic_bp": "systolic_bp",
    "systolicbp": "systolic_bp",
    "sbp": "systolic_bp",
    "diastolic": "diastolic_bp",
    "diastolic_bp": "diastolic_bp",
    "diastolicbp": "diastolic_bp",
    "dbp": "diastolic_bp",
    "respiratory_rate": "respiratory_rate",
    "respiratoryrate": "respiratory_rate",
    "rr": "respiratory_rate",
}


BP_KEYS = {"bp", "blood_pressure", "bloodpressure"}


def normalize_clinical_record(raw_input: Mapping[str, Any] | ClinicalRecord) -> ClinicalRecord:
    if isinstance(raw_input, ClinicalRecord):
        return raw_input

    record_payload = {
        "record_id": _first_present(raw_input, "record_id", "recordId", "id"),
        "patient_id": _first_present(raw_input, "patient_id", "patientId"),
        "visit_id": _first_present(raw_input, "visit_id", "visitId", "encounter_id"),
        "query": _first_present(raw_input, "query", "message", "text", "user_message"),
        "symptoms": _normalize_symptoms(raw_input.get("symptoms", [])),
        "vitals": _normalize_vitals(raw_input),
        "source": _normalize_source(raw_input.get("source", [])),
    }

    return ClinicalRecord(**record_payload)


def _first_present(raw_input: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw_input and raw_input[key] is not None:
            return raw_input[key]
    return None


def _normalize_symptoms(raw_symptoms: Any) -> list[dict[str, Any]]:
    if raw_symptoms is None:
        return []
    if isinstance(raw_symptoms, str):
        raw_symptoms = [
            symptom.strip()
            for symptom in re.split(r",|;", raw_symptoms)
            if symptom.strip()
        ]
    if not isinstance(raw_symptoms, list):
        raw_symptoms = [raw_symptoms]

    symptoms: list[dict[str, Any]] = []
    for symptom in raw_symptoms:
        if isinstance(symptom, str):
            symptoms.append({"name": symptom.strip().lower()})
        elif isinstance(symptom, Mapping):
            name = _first_present(symptom, "name", "symptom", "text", "label")
            if name is None:
                symptoms.append(dict(symptom))
                continue
            symptoms.append(
                {
                    "name": str(name).strip().lower(),
                    "severity": _optional_clean(symptom.get("severity")),
                    "duration": _optional_clean(symptom.get("duration")),
                }
            )
        else:
            symptoms.append({"name": str(symptom).strip().lower()})
    return symptoms


def _normalize_vitals(raw_input: Mapping[str, Any]) -> dict[str, Any]:
    raw_vitals = raw_input.get("vitals", {})
    if raw_vitals is None:
        raw_vitals = {}
    if not isinstance(raw_vitals, Mapping):
        raise ValueError("vitals must be an object")

    normalized: dict[str, Any] = {}
    for source in (raw_input, raw_vitals):
        for key, value in source.items():
            normalized_key = _normalize_key(str(key))
            if normalized_key in BP_KEYS:
                _merge_blood_pressure(normalized, value)
                continue
            canonical_key = VITAL_KEY_ALIASES.get(normalized_key)
            if canonical_key:
                normalized[canonical_key] = value

    return normalized


def _merge_blood_pressure(normalized: dict[str, Any], value: Any) -> None:
    if isinstance(value, str):
        match = re.match(r"\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$", value)
        if match:
            normalized.setdefault("systolic_bp", float(match.group(1)))
            normalized.setdefault("diastolic_bp", float(match.group(2)))
    elif isinstance(value, Mapping):
        systolic = _first_present(value, "systolic", "systolic_bp", "SBP")
        diastolic = _first_present(value, "diastolic", "diastolic_bp", "DBP")
        if systolic is not None:
            normalized.setdefault("systolic_bp", systolic)
        if diastolic is not None:
            normalized.setdefault("diastolic_bp", diastolic)


def _normalize_source(raw_source: Any) -> list[str]:
    if raw_source is None:
        return []
    if isinstance(raw_source, str):
        return [raw_source.strip()] if raw_source.strip() else []
    if isinstance(raw_source, list):
        return [str(source).strip() for source in raw_source if str(source).strip()]
    return [str(raw_source).strip()]


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


def _optional_clean(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None

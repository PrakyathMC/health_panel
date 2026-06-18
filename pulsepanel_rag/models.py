from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _clean_required_text(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


class Symptom(ContractModel):
    name: str
    severity: str | None = None
    duration: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _clean_required_text(value)


class VitalSigns(ContractModel):
    spo2: float | None = Field(
        default=None,
        ge=0,
        le=100,
        validation_alias=AliasChoices("spo2", "SpO2", "oxygen_saturation"),
    )
    heart_rate: float | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("heart_rate", "HR"),
    )
    temperature_c: float | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("temperature_c", "temp"),
    )
    systolic_bp: float | None = Field(default=None, gt=0)
    diastolic_bp: float | None = Field(default=None, gt=0)
    respiratory_rate: float | None = Field(default=None, gt=0)


class ClinicalRecord(ContractModel):
    record_id: str
    patient_id: str
    query: str
    symptoms: list[Symptom] = Field(default_factory=list)
    vitals: VitalSigns = Field(default_factory=VitalSigns)
    source: list[str] = Field(default_factory=list)
    visit_id: str | None = None

    @field_validator("record_id", "patient_id", "query")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


class ClinicalLabel(ContractModel):
    label: str
    fact: str
    risk_concept: str | None
    rule: str
    evidence: dict[str, Any]

    @field_validator("label", "fact", "rule")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


class KnowledgeDocument(ContractModel):
    doc_id: str
    title: str
    condition: str
    text: str
    keywords: set[str]
    labels: set[str]
    risk_concepts: set[str]

    @field_validator("doc_id", "title", "condition", "text")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


class RetrievalResult(ContractModel):
    rank: int = Field(ge=1)
    title: str
    condition: str
    score: float = Field(ge=0)
    retrieval_sources: list[str]
    evidence: list[str]
    explanation: str

    @field_validator("title", "condition", "explanation")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


class RetrievalBundle(ContractModel):
    record_id: str
    patient_id: str
    embedding_text: str
    labels: list[ClinicalLabel]
    results: list[RetrievalResult]

    @field_validator("record_id", "patient_id", "embedding_text")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _clean_required_text(value)

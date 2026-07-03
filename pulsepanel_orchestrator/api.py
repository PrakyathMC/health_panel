"""FastAPI application for the PulsePanel orchestrator.

Provides HTTP endpoints for clinical analysis:
- POST /analyze — submit a clinical record for analysis
- GET /health — health check
- POST /analyze/batch — batch analysis of multiple records

Start with:
    uvicorn pulsepanel_orchestrator.api:app --reload
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config.settings import settings
from .orchestrator import PulsePanelOrchestrator

app = FastAPI(
    title="PulsePanel Clinical RAG API",
    description="Orchestrated clinical retrieval-augmented generation pipeline",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Global orchestrator instance
_orchestrator: PulsePanelOrchestrator | None = None


def get_orchestrator() -> PulsePanelOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PulsePanelOrchestrator()
    return _orchestrator


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------


class SymptomInput(BaseModel):
    """A single symptom from the frontend."""

    name: str | None = Field(None, description="Symptom name (e.g. chest pain)")
    symptom: str | None = Field(None, description="Alias for name")
    severity: str | None = Field(None, description="Severity level")
    duration: str | None = Field(None, description="Duration")


class VitalInput(BaseModel):
    """Vital signs with common aliases."""

    spo2: float | None = Field(None, alias="SpO2")
    heart_rate: float | None = Field(None, alias="HR")
    temperature_c: float | None = Field(None, alias="temp")
    systolic_bp: float | None = Field(None)
    diastolic_bp: float | None = Field(None)
    bp: str | None = Field(None, description="Blood pressure as string (e.g. 120/80)")


class AnalyzeRequest(BaseModel):
    """Clinical record input for analysis."""

    record_id: str = Field(..., description="Unique record identifier")
    patient_id: str = Field(..., description="Unique patient identifier")
    query: str = Field(..., description="Free-text clinical query / chief complaint")
    symptoms: list[str | dict[str, Any]] = Field(default_factory=list)
    vitals: dict[str, Any] = Field(default_factory=dict)
    source: str | list[str] | None = None
    visit_id: str | None = None


class BatchAnalyzeRequest(BaseModel):
    """Batch analysis request."""

    records: list[AnalyzeRequest]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "pulsepanel-orchestrator"}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    """Submit a clinical record for analysis.

    Returns a RetrievalBundle with ranked results and explanations.
    """
    orchestrator = get_orchestrator()

    try:
        raw_input = request.model_dump(by_alias=True, exclude_none=True)
        bundle = orchestrator.run(raw_input)
        return _serialize_bundle(bundle)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze/batch")
async def analyze_batch(request: BatchAnalyzeRequest) -> list[dict[str, Any]]:
    """Submit multiple clinical records for batch analysis."""
    orchestrator = get_orchestrator()
    results: list[dict[str, Any]] = []

    for record in request.records:
        try:
            raw_input = record.model_dump(by_alias=True, exclude_none=True)
            bundle = orchestrator.run(raw_input)
            results.append(_serialize_bundle(bundle))
        except Exception as exc:
            results.append({"record_id": record.record_id, "error": str(exc)})

    return results


# ------------------------------------------------------------------
# Serialization
# ------------------------------------------------------------------


def _serialize_bundle(bundle: Any) -> dict[str, Any]:
    """Convert a RetrievalBundle dataclass to a JSON-serializable dict."""
    return {
        "record_id": bundle.record_id,
        "patient_id": bundle.patient_id,
        "embedding_text": bundle.embedding_text,
        "labels": [
            {
                "label": lbl.label,
                "fact": lbl.fact,
                "risk_concept": lbl.risk_concept,
                "rule": lbl.rule,
                "evidence": lbl.evidence,
            }
            for lbl in bundle.labels
        ],
        "results": [
            {
                "rank": r.rank,
                "title": r.title,
                "condition": r.condition,
                "score": r.score,
                "retrieval_sources": r.retrieval_sources,
                "evidence": r.evidence,
                "explanation": r.explanation,
            }
            for r in bundle.results
        ],
        "errors": bundle.errors,
    }

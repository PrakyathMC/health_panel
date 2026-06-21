"""PulsePanel Orchestration Layer.

Pure Python tool-based pipeline for clinical RAG orchestration.
No frameworks — every tool does one thing, does it well, and is auditable.
"""

from .orchestrator import PulsePanelOrchestrator
from .context import OrchestrationContext
from .base import BaseTool
from .models import (
    Symptom,
    VitalSigns,
    ClinicalRecord,
    ClinicalLabel,
    KnowledgeDocument,
    RetrievalResult,
    RetrievalBundle,
)
from .errors import (
    OrchestrationError,
    ValidationError,
    ToolExecutionError,
    DbConnectionError,
    ToolTimeoutError,
)

__all__ = [
    "PulsePanelOrchestrator",
    "OrchestrationContext",
    "BaseTool",
    "Symptom",
    "VitalSigns",
    "ClinicalRecord",
    "ClinicalLabel",
    "KnowledgeDocument",
    "RetrievalResult",
    "RetrievalBundle",
    "OrchestrationError",
    "ValidationError",
    "ToolExecutionError",
    "DbConnectionError",
    "ToolTimeoutError",
]

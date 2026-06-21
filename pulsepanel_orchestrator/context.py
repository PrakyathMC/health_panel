"""Shared context object that flows through the pipeline.

OrchestrationContext is a mutable container that each tool reads from and
writes to. It carries:

- The original raw input
- The normalised ClinicalRecord
- Derived clinical labels
- Embedding text
- Retrieval results from each path
- The final merged results
- Errors encountered along the way
- Timing metrics for audit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import (
    ClinicalLabel,
    ClinicalRecord,
    RetrievalBundle,
    RetrievalResult,
)


@dataclass
class OrchestrationContext:
    """Mutable context passed through the tool pipeline.

    Each tool reads from and writes to this context. The orchestrator
    initialises it with raw_input and accesses bundle at the end.
    """

    # --- Input ---
    raw_input: dict[str, Any]

    # --- Stage 1: Normalisation ---
    record: ClinicalRecord | None = None

    # --- Stage 2: Clinical reasoning ---
    labels: list[ClinicalLabel] | None = None

    # --- Stage 3: Embedding ---
    embedding_text: str | None = None

    # --- Stage 4-7: Retrieval ---
    semantic_results: list[RetrievalResult] = field(default_factory=list)
    keyword_results: list[RetrievalResult] = field(default_factory=list)
    symbolic_results: list[RetrievalResult] = field(default_factory=list)
    graph_results: list[RetrievalResult] = field(default_factory=list)

    # --- Stage 8: Merged ---
    merged_results: list[RetrievalResult] = field(default_factory=list)

    # --- Stage 9: Final output ---
    bundle: RetrievalBundle | None = None

    # --- Runtime ---
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def all_retrieval_results(self) -> list[list[RetrievalResult]]:
        """Return all retrieval-path results as a list-of-lists for merging."""
        return [
            self.semantic_results,
            self.keyword_results,
            self.symbolic_results,
            self.graph_results,
        ]

    def add_error(self, message: str) -> None:
        """Append a non-fatal error message to the context."""
        self.errors.append(message)

"""Tool 9 — ExplanationGenerator.

Generates human-readable explanations for each retrieval result,
describing why each document was matched and which clinical signals
contributed to the retrieval.
"""

from __future__ import annotations

from ..base import BaseTool
from ..context import OrchestrationContext
from ..models import ClinicalLabel, RetrievalBundle, RetrievalResult


class ExplanationGenerator(BaseTool):
    """Generate human-readable explanations for each retrieval result."""

    @property
    def name(self) -> str:
        return "ExplanationGenerator"

    @property
    def dependencies(self) -> list[str]:
        return ["ResultMerger"]

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        if not ctx.merged_results:
            ctx.bundle = RetrievalBundle(
                record_id=ctx.record.record_id if ctx.record else "",
                patient_id=ctx.record.patient_id if ctx.record else "",
                embedding_text=ctx.embedding_text or "",
                labels=ctx.labels or [],
                results=[],
                errors=ctx.errors,
            )
            return ctx

        record = ctx.record
        labels = ctx.labels or []

        explained: list[RetrievalResult] = []
        for result in ctx.merged_results:
            explanation = self._generate_explanation(result, labels)
            explained.append(
                RetrievalResult(
                    rank=result.rank,
                    title=result.title,
                    condition=result.condition,
                    score=result.score,
                    retrieval_sources=result.retrieval_sources,
                    evidence=result.evidence,
                    explanation=explanation,
                )
            )

        ctx.bundle = RetrievalBundle(
            record_id=record.record_id if record else "",
            patient_id=record.patient_id if record else "",
            embedding_text=ctx.embedding_text or "",
            labels=labels,
            results=explained,
            errors=ctx.errors,
        )
        return ctx

    @staticmethod
    def _generate_explanation(
        result: RetrievalResult,
        labels: list[ClinicalLabel],
    ) -> str:
        """Build a human-readable explanation for a single result."""
        parts: list[str] = []

        # Opening — what was found
        parts.append(f"Patient presentation matches {result.title.lower()}.")

        # Which retrieval paths contributed
        if result.retrieval_sources:
            path_names = [s.replace("_", " ") for s in result.retrieval_sources]
            parts.append(
                f"Matched via {', '.join(path_names)} retrieval."
            )

        # Which clinical signals contributed
        matched_signals = []
        for ev in result.evidence:
            if "matched_labels" in ev:
                matched_signals.append(ev["matched_labels"])
            if "matched_risks" in ev:
                matched_signals.append(ev["matched_risks"])
            if "path" in ev:
                matched_signals.append(ev["path"])
            if "similarity" in ev:
                matched_signals.append(f"semantic similarity {ev['similarity']}")
            if "matched_keywords" in ev:
                matched_signals.append(f"keywords: {ev['matched_keywords']}")

        if matched_signals:
            parts.append(
                f"Relevant signals: {'; '.join(matched_signals)}."
            )

        # Evidence from clinical rules
        if labels and result.condition:
            condition_labels = [
                lbl for lbl in labels
                if lbl.risk_concept.replace(" ", "_") == result.condition
            ]
            if condition_labels:
                label_str = ", ".join(
                    f"{lbl.label} ({lbl.evidence})" for lbl in condition_labels
                )
                parts.append(f"Clinical evidence: {label_str}.")
            else:
                # Fallback: show any labels that could relate
                for lbl in labels:
                    matched = []
                    for kw in result.title.lower().split():
                        if kw in lbl.label.replace("_", " ") or kw in lbl.risk_concept:
                            matched.append(kw)
                    if matched:
                        parts.append(
                            f"Label '{lbl.label}' ({lbl.evidence}) may be relevant."
                        )

        return " ".join(parts)

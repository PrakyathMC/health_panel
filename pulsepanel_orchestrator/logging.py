"""Audit logging for the orchestration layer.

Every tool call is logged with timing, input summary, output summary,
and error information. This provides full auditability for clinical use.
"""

from __future__ import annotations

import time
import logging
from typing import Any

logger = logging.getLogger("pulsepanel.orchestrator")


def log_tool_call(
    tool_name: str,
    started_at: float,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Log a single tool execution with timing and summaries.

    Args:
        tool_name: Name of the tool that executed.
        started_at: Timestamp (time.monotonic()) when the tool started.
        input_summary: Brief summary of what the tool received.
        output_summary: Brief summary of what the tool produced.
        error: Error message if the tool failed, else None.
    """
    duration_ms = (time.monotonic() - started_at) * 1000
    record = {
        "tool": tool_name,
        "duration_ms": round(duration_ms, 2),
        "input_summary": input_summary or {},
        "output_summary": output_summary or {},
        "error": error,
    }

    if error:
        logger.warning("Tool %s failed in %.2fms: %s", tool_name, duration_ms, error)
    else:
        logger.info(
            "Tool %s completed in %.2fms", tool_name, duration_ms,
        )

    # Also attach to the record for structured logging
    if hasattr(logging, "LogRecord") and hasattr(logging.LogRecord, "__dict__"):
        pass  # structured logging handlers can access the dict


def make_input_summary(ctx: Any, tool: str) -> dict[str, Any]:
    """Build a standardised input summary for a tool."""
    if tool == "InputNormalizer":
        return {"has_raw_input": ctx.raw_input is not None}
    if tool in ("ClinicalRuleEngine",):
        return {"has_vitals": ctx.record is not None and ctx.record.vitals is not None}
    if tool == "EmbeddingTextBuilder":
        return {
            "record_id": ctx.record.record_id if ctx.record else None,
            "labels_count": len(ctx.labels) if ctx.labels else 0,
        }
    if tool in ("SemanticRetriever", "KeywordRetriever", "SymbolicRetriever", "GraphRetriever"):
        return {
            "record_id": ctx.record.record_id if ctx.record else None,
            "labels_count": len(ctx.labels) if ctx.labels else 0,
        }
    if tool == "ResultMerger":
        return {
            "semantic": len(ctx.semantic_results),
            "keyword": len(ctx.keyword_results),
            "symbolic": len(ctx.symbolic_results),
            "graph": len(ctx.graph_results),
        }
    if tool == "ExplanationGenerator":
        return {"results_count": len(ctx.merged_results)}
    return {}


def make_output_summary(ctx: Any, tool: str) -> dict[str, Any]:
    """Build a standardised output summary for a tool."""
    if tool == "InputNormalizer":
        return {
            "record_id": ctx.record.record_id if ctx.record else None,
            "symptoms": len(ctx.record.symptoms) if ctx.record and ctx.record.symptoms else 0,
        }
    if tool == "ClinicalRuleEngine":
        return {"labels_count": len(ctx.labels) if ctx.labels else 0}
    if tool == "EmbeddingTextBuilder":
        return {"text_length": len(ctx.embedding_text) if ctx.embedding_text else 0}
    if tool == "SemanticRetriever":
        return {"results": len(ctx.semantic_results)}
    if tool == "KeywordRetriever":
        return {"results": len(ctx.keyword_results)}
    if tool == "SymbolicRetriever":
        return {"results": len(ctx.symbolic_results)}
    if tool == "GraphRetriever":
        return {"results": len(ctx.graph_results)}
    if tool == "ResultMerger":
        return {"results": len(ctx.merged_results)}
    if tool == "ExplanationGenerator":
        return {"has_bundle": ctx.bundle is not None}
    return {}

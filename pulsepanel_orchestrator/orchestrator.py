"""PulsePanelOrchestrator — central coordinator of the tool pipeline.

The orchestrator:
1. Initialises the shared OrchestrationContext
2. Executes tools in dependency order
3. Handles errors with graceful degradation
4. Logs every step for auditability
5. Returns a complete RetrievalBundle
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .base import BaseTool
from .config.settings import settings
from .context import OrchestrationContext
from .errors import (
    DbConnectionError,
    OrchestrationError,
    ToolExecutionError,
    ToolTimeoutError,
    ValidationError,
)
from .logging import log_tool_call, make_input_summary, make_output_summary
from .models import RetrievalBundle
from .tools import (
    ClinicalRuleEngine,
    EmbeddingTextBuilder,
    ExplanationGenerator,
    GraphRetriever,
    InputNormalizer,
    KeywordRetriever,
    ResultMerger,
    SemanticRetriever,
    SymbolicRetriever,
)

logger = logging.getLogger("pulsepanel.orchestrator")


class PulsePanelOrchestrator:
    """Central coordinator for the clinical RAG pipeline.

    Usage:
        orchestrator = PulsePanelOrchestrator()
        bundle = orchestrator.run(raw_input)
    """

    def __init__(
        self,
        tools: list[BaseTool] | None = None,
        top_k: int | None = None,
    ) -> None:
        """Initialise the orchestrator with a list of tools.

        Args:
            tools: List of tool instances. If None, uses the default pipeline.
            top_k: Maximum number of results to return.
        """
        self._tools: dict[str, BaseTool] = {}
        self._pipeline_order: list[str] = []

        tool_list = tools or self._default_tools(top_k)
        for tool in tool_list:
            self._tools[tool.name] = tool
            self._pipeline_order.append(tool.name)

    @staticmethod
    def _default_tools(top_k: int | None = None) -> list[BaseTool]:
        """Build the default tool pipeline."""
        merger = ResultMerger(top_k=top_k) if top_k else ResultMerger()
        return [
            InputNormalizer(),
            ClinicalRuleEngine(),
            EmbeddingTextBuilder(),
            SemanticRetriever(),
            KeywordRetriever(),
            SymbolicRetriever(),
            GraphRetriever(),
            merger,
            ExplanationGenerator(),
        ]

    def run(self, raw_input: dict[str, Any]) -> RetrievalBundle:
        """Execute the full pipeline on raw clinical input.

        Args:
            raw_input: Raw clinical data from the frontend.

        Returns:
            A RetrievalBundle with ranked results and explanations.
        """
        ctx = OrchestrationContext(raw_input=raw_input)
        logger.info(
            "Pipeline started — %d tools registered",
            len(self._pipeline_order),
        )

        for tool_name in self._pipeline_order:
            tool = self._tools[tool_name]

            # Check dependencies were executed
            if not self._dependencies_met(ctx, tool):
                continue

            ctx = self._execute_tool(ctx, tool)

            # Stop on validation errors
            if ctx.errors and self._has_fatal_error(ctx):
                break

        # Ensure a bundle exists even if pipeline failed early
        if ctx.bundle is None:
            ctx.bundle = RetrievalBundle(
                record_id=ctx.record.record_id if ctx.record else "",
                patient_id=ctx.record.patient_id if ctx.record else "",
                embedding_text=ctx.embedding_text or "",
                labels=ctx.labels or [],
                results=ctx.merged_results,
                errors=ctx.errors,
            )

        logger.info(
            "Pipeline finished — %d results, %d error(s)",
            len(ctx.bundle.results),
            len(ctx.bundle.errors),
        )
        return ctx.bundle

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _execute_tool(
        self, ctx: OrchestrationContext, tool: BaseTool
    ) -> OrchestrationContext:
        """Execute a single tool with timing and error handling."""
        started_at = time.monotonic()
        input_summary = make_input_summary(ctx, tool.name)

        try:
            ctx = tool.run(ctx)
            output_summary = make_output_summary(ctx, tool.name)
            log_tool_call(tool.name, started_at, input_summary, output_summary)
        except ValidationError as exc:
            ctx.add_error(str(exc))
            log_tool_call(tool.name, started_at, input_summary, error=str(exc))
        except DbConnectionError as exc:
            ctx.add_error(str(exc))
            log_tool_call(tool.name, started_at, input_summary, error=str(exc))
        except ToolTimeoutError as exc:
            ctx.add_error(str(exc))
            log_tool_call(tool.name, started_at, input_summary, error=str(exc))
        except ToolExecutionError as exc:
            ctx.add_error(str(exc))
            log_tool_call(tool.name, started_at, input_summary, error=str(exc))
        except Exception as exc:
            msg = f"{tool.name} failed unexpectedly: {exc}"
            ctx.add_error(msg)
            log_tool_call(tool.name, started_at, input_summary, error=msg)

        # Track timing
        elapsed = time.monotonic() - started_at
        ctx.metrics[tool.name] = round(elapsed * 1000, 2)

        return ctx

    def _dependencies_met(self, ctx: OrchestrationContext, tool: BaseTool) -> bool:
        """Check if a tool's dependencies have been met.

        If a dependency failed (error logged), the dependent tool is skipped
        with a warning rather than crashing the pipeline.
        """
        for dep_name in tool.dependencies:
            if dep_name not in self._tools:
                ctx.add_error(
                    f"Dependency '{dep_name}' not found for tool '{tool.name}'"
                )
                return False
        return True

    @staticmethod
    def _has_fatal_error(ctx: OrchestrationContext) -> bool:
        """Check if a fatal (validation) error occurred."""
        for err in ctx.errors:
            if "ValidationError" in err or "Missing required" in err:
                return True
        return False

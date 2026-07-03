"""Abstract base class for all orchestration tools.

Every tool in the pipeline must implement the BaseTool interface:
- name: unique identifier
- dependencies: list of tools that must run first
- run(ctx): executes the tool and returns updated context
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .context import OrchestrationContext


class BaseTool(ABC):
    """Every tool in the pipeline must subclass BaseTool."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier (snake_case)."""
        ...

    @property
    def dependencies(self) -> list[str]:
        """Tools that must execute before this one (default: none)."""
        return []

    @abstractmethod
    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        """Execute this tool's logic and return the updated context.

        Args:
            ctx: The shared orchestration context carrying data between tools.

        Returns:
            The same context object with this tool's outputs populated.

        Raises:
            ToolExecutionError: if the tool fails internally.
            ConnectionError: if a required external service is unavailable.
        """
        ...

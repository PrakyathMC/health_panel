"""Typed exceptions for the orchestration layer.

Each error type maps to a specific behaviour in the orchestrator:
- ValidationError   → halt immediately
- ToolExecutionError → skip tool, continue
- ConnectionError   → skip dependent tools, return partial
- TimeoutError      → skip tool, continue
"""


class OrchestrationError(Exception):
    """Base exception for all orchestration-layer errors."""

    def __init__(self, message: str, tool: str | None = None) -> None:
        self.tool = tool
        super().__init__(message)


class ValidationError(OrchestrationError):
    """Input validation failed — halt the pipeline immediately."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message, tool="InputNormalizer")


class ToolExecutionError(OrchestrationError):
    """A tool encountered an error during execution — skip and continue."""

    def __init__(self, message: str, tool: str, details: str | None = None) -> None:
        self.details = details
        super().__init__(message, tool=tool)


class DbConnectionError(OrchestrationError):
    """A database or external service is unavailable — graceful degradation."""

    def __init__(self, message: str, tool: str, service: str) -> None:
        self.service = service
        super().__init__(message, tool=tool)


class ToolTimeoutError(OrchestrationError):
    """A tool exceeded its time budget — skip and continue."""

    def __init__(self, message: str, tool: str, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message, tool=tool)

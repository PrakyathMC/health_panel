"""Abstract base class for all database adapters.

Adapters wrap the underlying database driver (psycopg, qdrant-client, neo4j)
and provide a uniform interface for the retrieval tools. Every adapter:

- Connects lazily (on first operation)
- Provides a health check
- Raises DbConnectionError on failures
- Implements close() for cleanup

Phase 2 adapters are designed to work alongside Phase 1's in-memory fallbacks:
if an adapter fails, the orchestrator degrades gracefully and uses the
in-memory knowledge base instead.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ...config.settings import Settings
from ...errors import DbConnectionError


class BaseAdapter(ABC):
    """Abstract interface for all database adapters."""

    def __init__(self, settings: Settings | None = None) -> None:
        from ...config.settings import settings as _default_settings
        self._settings = settings or _default_settings
        self._connected = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection to the database.

        Raises:
            DbConnectionError: if the connection cannot be established.
        """
        ...

    def close(self) -> None:
        """Close the database connection. No-op if already closed."""
        self._connected = False

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return a health-check dict with connection status and latency.

        Returns:
            {"status": "ok" | "error", "latency_ms": float, "detail": str}
        """
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_connected(self) -> None:
        """Raise if not connected."""
        if not self._connected:
            raise DbConnectionError(
                f"{self.__class__.__name__} is not connected. Call connect() first.",
                tool=self.__class__.__name__,
                service=self.__class__.__name__,
            )

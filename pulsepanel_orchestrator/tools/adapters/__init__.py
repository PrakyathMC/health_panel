"""Database adapters package.

Adapters abstract away the underlying database driver so the retrieval
tools can remain database-agnostic. Each adapter implements the
interface defined in .base_adapter.

Phase 2 adapters provide production-grade storage and retrieval, designed
to replace the Phase 1 in-memory implementations when the database
services are available.
"""

from .base_adapter import BaseAdapter
from .postgres_adapter import PostgresAdapter
from .qdrant_adapter import QdrantAdapter
from .neo4j_adapter import Neo4jAdapter

__all__ = [
    "BaseAdapter",
    "PostgresAdapter",
    "QdrantAdapter",
    "Neo4jAdapter",
]

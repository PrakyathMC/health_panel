"""Application settings loaded from environment variables.

All database connection strings and configuration values are read
from environment variables with sensible defaults for local development.
Supports .env files via python-dotenv — create a .env file in the
project root to override defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root before reading any settings.
# Resolves the path relative to this file so it works regardless
# of the current working directory.
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class Settings:
    """Orchestration layer settings.

    Values are read from environment variables or use defaults.
    """

    # --- PostgreSQL ---
    postgres_dsn: str = field(
        default_factory=lambda: os.getenv(
            "PULSEPANEL_POSTGRES_DSN",
            "postgresql://pulsepanel:pulsepanel_secret@localhost:5432/pulsepanel",
        )
    )

    # --- OpenAI ---
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    # --- Qdrant ---
    qdrant_url: str = field(
        default_factory=lambda: os.getenv(
            "PULSEPANEL_QDRANT_URL",
            "http://localhost:6333",
        )
    )
    qdrant_collection: str = field(
        default_factory=lambda: os.getenv(
            "PULSEPANEL_QDRANT_COLLECTION",
            "clinical_knowledge",
        )
    )

    # --- Neo4j ---
    neo4j_uri: str = field(
        default_factory=lambda: os.getenv(
            "PULSEPANEL_NEO4J_URI",
            "bolt://localhost:7687",
        )
    )
    neo4j_user: str = field(
        default_factory=lambda: os.getenv("PULSEPANEL_NEO4J_USER", "neo4j")
    )
    neo4j_password: str = field(
        default_factory=lambda: os.getenv("PULSEPANEL_NEO4J_PASSWORD", "pulsepanel_graph")
    )

    # --- Embedding ---
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "PULSEPANEL_EMBEDDING_MODEL",
            "text-embedding-3-large",
        )
    )
    embedding_dimensions: int = int(
        os.getenv("PULSEPANEL_EMBEDDING_DIMENSIONS", "3072")
    )

    # --- Retrieval ---
    top_k: int = int(os.getenv("PULSEPANEL_TOP_K", "10"))
    semantic_weight: float = float(os.getenv("PULSEPANEL_SEMANTIC_WEIGHT", "0.25"))
    keyword_weight: float = float(os.getenv("PULSEPANEL_KEYWORD_WEIGHT", "0.25"))
    symbolic_weight: float = float(os.getenv("PULSEPANEL_SYMBOLIC_WEIGHT", "0.35"))
    graph_weight: float = float(os.getenv("PULSEPANEL_GRAPH_WEIGHT", "0.15"))
    enable_qdrant_semantic: bool = (
        os.getenv("PULSEPANEL_ENABLE_QDRANT_SEMANTIC", "false").lower()
        in ("true", "1", "yes")
    )

    # --- Pipeline ---
    tool_timeout_seconds: float = float(
        os.getenv("PULSEPANEL_TOOL_TIMEOUT", "30.0")
    )
    enable_audit_log: bool = os.getenv("PULSEPANEL_ENABLE_AUDIT", "true").lower() in (
        "true",
        "1",
        "yes",
    )


# Global singleton
settings = Settings()

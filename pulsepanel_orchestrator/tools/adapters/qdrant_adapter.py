"""Qdrant Adapter — vector storage and semantic search.

Manages the Qdrant vector collection for clinical knowledge document
embeddings. Uses OpenAI's embedding API (text-embedding-3-large) for
generating vectors and qdrant-client for storage and retrieval.

Phase 2 adapter — designed to replace the in-memory SemanticRetriever
when the Qdrant service is available.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from ...errors import DbConnectionError
from ...models import KnowledgeDocument
from .base_adapter import BaseAdapter


class QdrantAdapter(BaseAdapter):
    """Vector storage and semantic search via Qdrant."""

    def __init__(
        self,
        url: str | None = None,
        collection_name: str | None = None,
        embedding_model: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._url = url or self._settings.qdrant_url
        self._collection_name = collection_name or self._settings.qdrant_collection
        self._model_name = embedding_model or self._settings.embedding_model
        self._dimensions = self._settings.embedding_dimensions
        self._client = None
        self._openai_client = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.http.exceptions import UnexpectedResponse

        try:
            self._client = QdrantClient(url=self._url, timeout=10)
            # Ping to verify connection
            self._client.get_collections()
            self._connected = True
        except UnexpectedResponse as exc:
            raise DbConnectionError(
                f"Cannot connect to Qdrant at {self._url}: {exc}",
                tool="QdrantAdapter",
                service="qdrant",
            ) from exc
        except Exception as exc:
            raise DbConnectionError(
                f"Cannot connect to Qdrant at {self._url}: {exc}",
                tool="QdrantAdapter",
                service="qdrant",
            ) from exc

    def close(self) -> None:
        self._client = None
        self._openai_client = None
        self._connected = False

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def ensure_collection(self, vector_size: int | None = None) -> None:
        """Create the knowledge collection if it doesn't exist.

        Args:
            vector_size: Dimension of the embedding vectors.
                         Defaults to settings.embedding_dimensions.
        """
        if vector_size is None:
            vector_size = self._dimensions
        self._require_connected()
        from qdrant_client.http.exceptions import UnexpectedResponse
        from qdrant_client.models import Distance, VectorParams

        try:
            collections = self._client.get_collections().collections
            exists = any(c.name == self._collection_name for c in collections)
            if not exists:
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
        except UnexpectedResponse as exc:
            raise DbConnectionError(
                f"Failed to create Qdrant collection '{self._collection_name}': {exc}",
                tool="QdrantAdapter",
                service="qdrant",
            ) from exc

    def delete_collection(self) -> None:
        """Delete the knowledge collection. Use with caution."""
        self._require_connected()
        try:
            self._client.delete_collection(collection_name=self._collection_name)
        except Exception as exc:
            raise DbConnectionError(
                f"Failed to delete collection '{self._collection_name}': {exc}",
                tool="QdrantAdapter",
                service="qdrant",
            ) from exc

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _get_openai_client(self):
        """Lazy-load the OpenAI client."""
        if self._openai_client is None:
            from openai import OpenAI
            api_key = self._settings.openai_api_key
            if not api_key:
                raise DbConnectionError(
                    "OPENAI_API_KEY is not set. Set it in your environment or .env file.",
                    tool="QdrantAdapter",
                    service="openai",
                )
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    def encode(self, text: str) -> list[float]:
        """Generate an embedding vector using OpenAI's embedding API."""
        client = self._get_openai_client()
        response = client.embeddings.create(
            model=self._model_name,
            input=text,
            dimensions=self._dimensions,
        )
        return response.data[0].embedding

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def ingest_document(self, document: KnowledgeDocument, embedding_text: str) -> None:
        """Ingest a single knowledge document into the vector store.

        Args:
            document: The knowledge document to store.
            embedding_text: The clinical text to embed (from EmbeddingTextBuilder).
        """
        self._require_connected()
        from qdrant_client.models import PointStruct

        vector = self.encode(embedding_text or document.text)

        point = PointStruct(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, document.doc_id).int % (2**63),
            vector=vector,
            payload={
                "doc_id": document.doc_id,
                "title": document.title,
                "condition": document.condition,
                "text": document.text,
                "keywords": document.keywords,
                "labels": document.labels,
                "risk_concepts": document.risk_concepts,
            },
        )

        try:
            self._client.upsert(
                collection_name=self._collection_name,
                points=[point],
            )
        except Exception as exc:
            raise DbConnectionError(
                f"Failed to ingest document '{document.doc_id}': {exc}",
                tool="QdrantAdapter",
                service="qdrant",
            ) from exc

    def ingest_documents(
        self, documents: list[KnowledgeDocument], embedding_texts: list[str] | None = None
    ) -> None:
        """Ingest multiple knowledge documents in batch."""
        for i, doc in enumerate(documents):
            text = embedding_texts[i] if embedding_texts and i < len(embedding_texts) else doc.text
            self.ingest_document(doc, text)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self, query_text: str, top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Search the vector store for documents similar to the query text.

        Args:
            query_text: The clinical text to search for.
            top_k: Maximum number of results.

        Returns:
            List of dicts with keys: doc_id, title, condition, score, payload.
        """
        self._require_connected()
        query_vector = self.encode(query_text)

        try:
            results = self._client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
            )
        except Exception as exc:
            raise DbConnectionError(
                f"Failed to search Qdrant: {exc}",
                tool="QdrantAdapter",
                service="qdrant",
            ) from exc

        return [
            {
                "doc_id": r.payload.get("doc_id", ""),
                "title": r.payload.get("title", ""),
                "condition": r.payload.get("condition", ""),
                "score": round(r.score, 4),
                "payload": r.payload,
            }
            for r in results
        ]

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        started = time.monotonic()
        try:
            if not self._connected or self._client is None:
                return {"status": "error", "latency_ms": 0, "detail": "not connected"}
            self._client.get_collections()
            latency = (time.monotonic() - started) * 1000
            return {
                "status": "ok",
                "latency_ms": round(latency, 2),
                "detail": f"connected to {self._url}, collection '{self._collection_name}'",
            }
        except Exception as exc:
            return {
                "status": "error",
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
                "detail": str(exc),
            }

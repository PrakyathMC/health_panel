"""Tests for the Qdrant seed script."""

from __future__ import annotations

from scripts.seed_qdrant import main, seed_qdrant
from pulsepanel_orchestrator.models import KnowledgeDocument


class FakeQdrantAdapter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.connected = False
        self.collection_ready = False
        self.ingested: list[KnowledgeDocument] = []
        self.closed = False
        self.search_query = ""

    def connect(self):
        self.connected = True

    def ensure_collection(self):
        self.collection_ready = True

    def ingest_documents(self, documents):
        self.ingested.extend(documents)

    def search(self, query, top_k=3):
        self.search_query = query
        return [
            {
                "title": "Possible acute coronary syndrome",
                "condition": "acs",
                "score": 0.91,
            }
        ][:top_k]

    def close(self):
        self.closed = True


def _doc() -> KnowledgeDocument:
    return KnowledgeDocument(
        doc_id="kb_test",
        title="Test clinical document",
        condition="test_condition",
        text="Clinical testing text",
    )


def test_seed_qdrant_connects_creates_collection_and_ingests_docs():
    adapter = FakeQdrantAdapter()
    count = seed_qdrant(adapter, [_doc()])

    assert count == 1
    assert adapter.connected
    assert adapter.collection_ready
    assert adapter.ingested[0].doc_id == "kb_test"


def test_main_supports_smoke_query_with_injected_adapter(capsys):
    adapters: list[FakeQdrantAdapter] = []

    def factory(**kwargs):
        adapter = FakeQdrantAdapter(**kwargs)
        adapters.append(adapter)
        return adapter

    exit_code = main(
        [
            "--url",
            ":memory:",
            "--collection",
            "test_collection",
            "--smoke-query",
            "chest pain",
        ],
        adapter_factory=factory,
        documents=[_doc()],
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Seeded 1 knowledge document" in captured.out
    assert "Possible acute coronary syndrome" in captured.out
    assert adapters[0].kwargs["url"] == ":memory:"
    assert adapters[0].kwargs["collection_name"] == "test_collection"
    assert adapters[0].search_query == "chest pain"
    assert adapters[0].closed

r"""Seed Qdrant with PulsePanel clinical knowledge embeddings.

This is a one-time or repeatable setup step for semantic retrieval:

    py scripts\seed_qdrant.py
    py scripts\seed_qdrant.py --smoke-query "chest pain and low oxygen"

The script reads OPENAI_API_KEY and Qdrant settings through the normal
PulsePanel settings loader. It does not print secrets.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pulsepanel_orchestrator.config.settings import settings
from pulsepanel_orchestrator.data.knowledge_base import KNOWLEDGE_DOCUMENTS
from pulsepanel_orchestrator.errors import DbConnectionError
from pulsepanel_orchestrator.models import KnowledgeDocument
from pulsepanel_orchestrator.tools.adapters import QdrantAdapter


AdapterFactory = Callable[..., QdrantAdapter]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Embed PulsePanel knowledge documents and store them in Qdrant.",
    )
    parser.add_argument(
        "--url",
        default=settings.qdrant_url,
        help=f"Qdrant URL. Defaults to {settings.qdrant_url!r}.",
    )
    parser.add_argument(
        "--collection",
        default=settings.qdrant_collection,
        help=f"Qdrant collection name. Defaults to {settings.qdrant_collection!r}.",
    )
    parser.add_argument(
        "--smoke-query",
        default=None,
        help="Optional query to run after seeding, to verify semantic search.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of smoke-query matches to print. Defaults to 3.",
    )
    return parser


def seed_qdrant(
    adapter: QdrantAdapter,
    documents: Sequence[KnowledgeDocument] = KNOWLEDGE_DOCUMENTS,
) -> int:
    """Connect to Qdrant, create the collection if needed, and upsert docs."""
    adapter.connect()
    adapter.ensure_collection()
    adapter.ingest_documents(list(documents))
    return len(documents)


def print_smoke_results(
    adapter: QdrantAdapter,
    query: str,
    top_k: int,
) -> None:
    """Print a compact semantic-search smoke test result."""
    matches = adapter.search(query, top_k=top_k)
    if not matches:
        print("Smoke query returned no matches.")
        return

    print("Smoke query results:")
    for rank, match in enumerate(matches, start=1):
        print(
            f"{rank}. {match['title']} "
            f"({match['condition']}) score={match['score']}"
        )


def main(
    argv: Sequence[str] | None = None,
    adapter_factory: AdapterFactory = QdrantAdapter,
    documents: Sequence[KnowledgeDocument] = KNOWLEDGE_DOCUMENTS,
) -> int:
    args = build_parser().parse_args(argv)
    adapter = adapter_factory(
        url=args.url,
        collection_name=args.collection,
    )

    try:
        count = seed_qdrant(adapter, documents)
        print(
            f"Seeded {count} knowledge document(s) into "
            f"Qdrant collection '{args.collection}'."
        )
        if args.smoke_query:
            print_smoke_results(adapter, args.smoke_query, top_k=args.top_k)
    except DbConnectionError as exc:
        print(f"Qdrant seeding failed: {exc}", file=sys.stderr)
        return 1
    finally:
        adapter.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI entry point for the PulsePanel orchestrator.

Usage:
    # From a JSON file
    python -m pulsepanel_orchestrator.cli --file input.json

    # From stdin
    echo '{"record_id":"...","patient_id":"...","query":"..."}' | python -m pulsepanel_orchestrator.cli

    # With a raw JSON string
    python -m pulsepanel_orchestrator.cli --json '{"record_id":"..."}'

    # Pretty-print output
    python -m pulsepanel_orchestrator.cli --file input.json --pretty

    # Save output to file
    python -m pulsepanel_orchestrator.cli --file input.json --output results.json
"""

from __future__ import annotations

import json
import sys
import argparse
from typing import Any

from .orchestrator import PulsePanelOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PulsePanel Clinical RAG Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--file", "-f",
        type=str,
        help="Path to a JSON file containing the clinical record.",
    )
    input_group.add_argument(
        "--json", "-j",
        type=str,
        help="Inline JSON string of the clinical record.",
    )
    input_group.add_argument(
        "--stdin", "-s",
        action="store_true",
        help="Read JSON from stdin (pipe).",
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Write output JSON to a file instead of stdout.",
    )
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        default=True,
        help="Pretty-print the output JSON (default: on).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Maximum number of results to return (default: 10).",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact (non-pretty) JSON.",
    )

    return parser


def load_input(args: argparse.Namespace) -> dict[str, Any]:
    """Load the clinical record JSON from the specified source."""
    if args.file:
        with open(args.file, "r") as f:
            return json.load(f)
    elif args.json:
        return json.loads(args.json)
    elif args.stdin:
        return json.load(sys.stdin)
    else:
        raise ValueError("No input source specified.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        raw_input = load_input(args)
    except FileNotFoundError as exc:
        print(f"Error: File not found — {exc.filename}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON — {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: Failed to read input — {exc}", file=sys.stderr)
        return 1

    orchestrator = PulsePanelOrchestrator(top_k=args.top_k)

    try:
        bundle = orchestrator.run(raw_input)
    except Exception as exc:
        print(f"Error: Pipeline failed — {exc}", file=sys.stderr)
        return 1

    output = bundle
    indent = 2 if args.pretty and not args.compact else None
    output_str = json.dumps(
        _serialize(output),
        indent=indent,
        default=str,
    )

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_str)
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output_str)

    # Return non-zero if there were errors
    return 1 if bundle.errors else 0


def _serialize(obj: Any) -> Any:
    """Convert dataclass objects to serializable dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        return {field: _serialize(getattr(obj, field)) for field in obj.__dataclass_fields__}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(value) for key, value in obj.items()}
    return obj


if __name__ == "__main__":
    sys.exit(main())

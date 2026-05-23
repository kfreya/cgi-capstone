"""Run Sprint 3 issue #38 RFP validation and export handoff artifacts.

Run from repository root:
    python scripts/validate_rfp_data_and_export_samples.py

Outputs:
    outputs/rfp_validation/rfp_validation_summary.json
    outputs/rfp_validation/rfp_sample_chunks.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rfp_data_validator import (
    build_validation_report,
    generate_sample_chunk_rows,
    load_proposals_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate proposals_responses.json and export chunk samples."
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "proposals_responses.json",
        help="Path to proposals_responses.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "rfp_validation",
        help="Directory for summary and sample outputs.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Chunk size passed to preprocess_proposals().",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Chunk overlap passed to preprocess_proposals().",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=10,
        help="Number of chunk rows to export in sample output.",
    )
    parser.add_argument(
        "--include-text",
        action="store_true",
        help="Include text previews in sample chunk output.",
    )
    parser.add_argument(
        "--keep-original-ids",
        action="store_true",
        help="Keep original proposal/document/chunk IDs in sample output.",
    )
    parser.add_argument(
        "--max-text-chars",
        type=int,
        default=180,
        help="Maximum number of text characters to include per sample row.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    proposals = load_proposals_json(args.json_path)

    report = build_validation_report(
        proposals,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    sample_chunks = generate_sample_chunk_rows(
        proposals,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        sample_size=args.sample_size,
        include_text=args.include_text,
        max_text_chars=args.max_text_chars,
        anonymize_ids=not args.keep_original_ids,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "rfp_validation_summary.json"
    samples_path = args.output_dir / "rfp_sample_chunks.json"

    summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    samples_path.write_text(json.dumps(sample_chunks, indent=2), encoding="utf-8")

    print(f"Loaded records: {report['structure_summary']['total_records']}")
    print(f"Extracted documents: {report['document_length_summary']['total_documents']}")
    print(
        "Owner/opportunity linkage available: "
        f"{report['chunk_metadata_validation']['can_link_to_owner_or_opportunity']}"
    )
    print(f"Wrote validation summary -> {_display_path(summary_path)}")
    print(f"Wrote sample chunks -> {_display_path(samples_path)}")


def _display_path(path: Path) -> str:
    """Print relative paths when possible, absolute otherwise."""

    resolved_path = path.resolve()
    try:
        return str(resolved_path.relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(resolved_path)


if __name__ == "__main__":
    main()

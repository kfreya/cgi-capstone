"""Generate Sprint 4 RFP retrieval evidence artifacts.

Run from the repository root:
    python scripts/generate_rfp_retrieval_evidence.py --output-dir outputs/rfp_evidence
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.azure_client import missing_azure_config
from src.rfp_data_validator import load_proposals_json
from src.rfp_evidence_validator import (
    assess_claim_support,
    compare_retrieval_paths,
    evaluate_retrieval_example,
    summarize_chunk_evidence_support,
)
from src.rfp_preprocessor import DEFAULT_PROPOSAL_JSON_PATH, preprocess_proposals
from src.vector_store import build_chroma_from_chunks, build_vector_store, query_chroma


DEFAULT_OUTPUT_DIR = Path("outputs/rfp_evidence")
DEFAULT_CHROMA_DIR = Path("data/vector_store/rfp_evidence")
DEFAULT_COLLECTION_NAME = "rfp_evidence_chunks"


QUERY_THEMES = [
    {
        "query_theme": "cloud migration",
        "input_text": (
            "RFP theme: cloud migration, Azure infrastructure modernization, "
            "managed transition planning, and platform operations support."
        ),
        "expected_terms": ["cloud", "azure", "migration", "managed", "operations"],
    },
    {
        "query_theme": "managed services",
        "input_text": (
            "RFP theme: managed services support model, service desk operations, "
            "transition planning, and ongoing application support."
        ),
        "expected_terms": ["managed", "services", "support", "operations", "transition"],
    },
    {
        "query_theme": "data analytics dashboard",
        "input_text": (
            "RFP theme: data analytics, dashboard reporting, KPI visualization, "
            "and executive performance insights."
        ),
        "expected_terms": ["data", "analytics", "dashboard", "reporting", "kpi"],
    },
    {
        "query_theme": "cybersecurity compliance",
        "input_text": (
            "RFP theme: cybersecurity assessment, privacy compliance, risk "
            "controls, and remediation planning."
        ),
        "expected_terms": ["cybersecurity", "security", "compliance", "risk", "privacy"],
    },
    {
        "query_theme": "application modernization",
        "input_text": (
            "RFP theme: application modernization, systems integration, architecture "
            "review, and legacy platform migration."
        ),
        "expected_terms": ["application", "modernization", "integration", "architecture"],
    },
    {
        "query_theme": "service desk support",
        "input_text": (
            "RFP theme: service desk support, incident management, operational "
            "handover, and user support model."
        ),
        "expected_terms": ["service", "desk", "support", "incident", "operational"],
    },
    {
        "query_theme": "change management training",
        "input_text": (
            "RFP theme: change management, stakeholder engagement, training, "
            "adoption planning, and communications."
        ),
        "expected_terms": ["change", "training", "stakeholder", "adoption"],
    },
    {
        "query_theme": "short vague request",
        "input_text": "Need implementation help for a public-sector technology project.",
        "expected_terms": ["implementation", "technology", "public", "sector"],
    },
]


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    proposals = load_proposals_json(args.json_path)
    raw_chunks = [chunk.to_dict() for chunk in preprocess_proposals(proposals)]
    chunks = _anonymize_chunks(raw_chunks)
    chunk_summary = summarize_chunk_evidence_support(chunks)
    claim_support = assess_claim_support(chunk_summary)

    local_results_by_theme = _run_local_retrieval(chunks, top_k=args.top_k)
    azure_status, azure_results_by_theme = _run_azure_retrieval(
        chunks=chunks,
        top_k=args.top_k,
        chroma_dir=Path(args.chroma_dir),
        collection_name=args.collection_name,
        azure_max_chunks=args.azure_max_chunks,
        azure_batch_size=args.azure_batch_size,
        azure_retry_seconds=args.azure_retry_seconds,
    )

    evidence_examples = _build_evidence_examples(
        azure_status=azure_status,
        azure_results_by_theme=azure_results_by_theme,
        local_results_by_theme=local_results_by_theme,
    )
    path_comparison = _build_path_comparison(
        azure_results_by_theme=azure_results_by_theme,
        local_results_by_theme=local_results_by_theme,
        comparison_count=args.comparison_count,
    )
    summary = {
        "artifact": "Sprint 4 issue #53 final RFP evidence validation summary",
        "proposal_json_path": str(Path(args.json_path)),
        "total_chunks_evaluated": len(chunks),
        "chunk_metadata_support": chunk_summary,
        "claim_support": claim_support,
        "azure_chroma_status": azure_status,
        "query_theme_count": len(QUERY_THEMES),
        "query_themes": [
            {
                "query_theme": query["query_theme"],
                "expected_terms": query["expected_terms"],
            }
            for query in QUERY_THEMES
        ],
        "final_wording_guidance": (
            "Use 'semantically similar historical proposal/response chunks' for "
            "retrieval claims. Do not state proven director experience or CRM "
            "opportunity linkage unless validated linkage fields are present."
        ),
    }

    _write_json(output_dir / "rfp_retrieval_evidence_examples.json", evidence_examples)
    _write_json(output_dir / "rfp_retrieval_path_comparison.json", path_comparison)
    _write_json(output_dir / "rfp_final_validation_summary.json", summary)

    print(f"Wrote evidence examples: {_display_path(output_dir / 'rfp_retrieval_evidence_examples.json')}")
    print(f"Wrote path comparison: {_display_path(output_dir / 'rfp_retrieval_path_comparison.json')}")
    print(f"Wrote validation summary: {_display_path(output_dir / 'rfp_final_validation_summary.json')}")
    print(f"Azure/Chroma status: {azure_status['status']}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate final RFP retrieval evidence artifacts for Sprint 4 issue #53."
    )
    parser.add_argument("--json-path", default=str(DEFAULT_PROPOSAL_JSON_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--comparison-count", type=int, default=3)
    parser.add_argument("--chroma-dir", default=str(DEFAULT_CHROMA_DIR))
    parser.add_argument("--collection-name", default=DEFAULT_COLLECTION_NAME)
    parser.add_argument("--azure-max-chunks", type=int, default=160)
    parser.add_argument("--azure-batch-size", type=int, default=16)
    parser.add_argument("--azure-retry-seconds", type=int, default=65)
    return parser.parse_args()


def _run_local_retrieval(
    chunks: list[dict[str, Any]],
    *,
    top_k: int,
) -> dict[str, list[dict[str, Any]]]:
    store = build_vector_store(chunks)
    results_by_theme: dict[str, list[dict[str, Any]]] = {}
    for query in QUERY_THEMES:
        results_by_theme[query["query_theme"]] = [
            result.to_retrieved_example()
            for result in store.query(query["input_text"], top_k=top_k)
        ]
    return results_by_theme


def _run_azure_retrieval(
    *,
    chunks: list[dict[str, Any]],
    top_k: int,
    chroma_dir: Path,
    collection_name: str,
    azure_max_chunks: int,
    azure_batch_size: int,
    azure_retry_seconds: int,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    missing = missing_azure_config(require_embedding=True)
    if missing:
        return (
            {
                "status": "unavailable",
                "reason": "Missing Azure embedding configuration.",
                "missing_config": missing,
            },
            {},
        )

    try:
        shutil.rmtree(PROJECT_ROOT / chroma_dir, ignore_errors=True)
        azure_chunks = _representative_chunk_sample(chunks, max_chunks=azure_max_chunks)
        embedding_function = _batched_azure_embedder(
            batch_size=azure_batch_size,
            retry_seconds=azure_retry_seconds,
        )
        build_chroma_from_chunks(
            azure_chunks,
            persist_directory=str(chroma_dir),
            collection_name=collection_name,
            embedding_function=embedding_function,
        )
        results_by_theme = {
            query["query_theme"]: query_chroma(
                query["input_text"],
                persist_directory=str(chroma_dir),
                collection_name=collection_name,
                top_k=top_k,
                embedding_function=embedding_function,
            )
            for query in QUERY_THEMES
        }
    except Exception as exc:  # pragma: no cover - depends on local Azure/Chroma setup
        return (
            {
                "status": "failed",
                "reason": f"{type(exc).__name__}: {exc}",
                "missing_config": [],
            },
            {},
        )

    return (
        {
            "status": "available",
            "reason": (
                "Azure embeddings and Chroma query path returned evidence rows "
                f"over a representative {len(azure_chunks)}-chunk subset."
            ),
            "missing_config": [],
            "indexed_chunks": len(azure_chunks),
            "indexing_note": (
                "Representative subset used to avoid Azure S0 embedding rate limits "
                "during evidence generation."
            ),
        },
        results_by_theme,
    )


def _build_evidence_examples(
    *,
    azure_status: dict[str, Any],
    azure_results_by_theme: dict[str, list[dict[str, Any]]],
    local_results_by_theme: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for query in QUERY_THEMES:
        query_theme = query["query_theme"]
        expected_terms = query["expected_terms"]
        azure_results = azure_results_by_theme.get(query_theme, [])
        local_results = local_results_by_theme.get(query_theme, [])
        primary_mode = (
            "azure_chroma"
            if azure_status["status"] == "available" and azure_results
            else "local_fallback"
        )
        primary_results = azure_results if primary_mode == "azure_chroma" else local_results
        evaluated_results = [
            evaluate_retrieval_example(query_theme, result, expected_terms)
            for result in primary_results
        ]
        examples.append(
            {
                "input_query_theme": query_theme,
                "input_query_text": query["input_text"],
                "retrieval_mode": primary_mode,
                "azure_chroma_status": azure_status["status"],
                "top_retrieved_chunk_ids": [
                    str(result.get("chunk_id"))
                    for result in primary_results
                    if result.get("chunk_id")
                ],
                "looks_relevant": any(row["looks_relevant"] for row in evaluated_results),
                "supports_displayed_summary_or_match_reason": any(
                    row["supports_summary_or_match_reason"]
                    for row in evaluated_results
                ),
                "weak_or_misleading_results": [
                    row
                    for row in evaluated_results
                    if row["weak_or_misleading_note"]
                ],
                "evaluated_results": evaluated_results,
            }
        )
    return examples


def _build_path_comparison(
    *,
    azure_results_by_theme: dict[str, list[dict[str, Any]]],
    local_results_by_theme: dict[str, list[dict[str, Any]]],
    comparison_count: int,
) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    for query in QUERY_THEMES[:comparison_count]:
        query_theme = query["query_theme"]
        comparisons.append(
            compare_retrieval_paths(
                query_theme=query_theme,
                azure_results=azure_results_by_theme.get(query_theme, []),
                local_results=local_results_by_theme.get(query_theme, []),
                expected_terms=query["expected_terms"],
            )
        )
    return comparisons


def _representative_chunk_sample(
    chunks: list[dict[str, Any]],
    *,
    max_chunks: int,
) -> list[dict[str, Any]]:
    if max_chunks <= 0 or len(chunks) <= max_chunks:
        return chunks

    by_proposal: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        by_proposal.setdefault(str(chunk.get("proposal_id", "unknown")), []).append(chunk)

    sample: list[dict[str, Any]] = []
    proposal_ids = sorted(by_proposal)
    cursor = 0
    while len(sample) < max_chunks:
        added = False
        for proposal_id in proposal_ids:
            proposal_chunks = by_proposal[proposal_id]
            if cursor < len(proposal_chunks):
                sample.append(proposal_chunks[cursor])
                added = True
                if len(sample) >= max_chunks:
                    break
        if not added:
            break
        cursor += 1

    return sample


def _batched_azure_embedder(*, batch_size: int, retry_seconds: int):
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    from src.azure_client import embed_texts

    def embed_in_batches(texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            try:
                embeddings.extend(embed_texts(batch))
            except Exception as exc:
                if "RateLimit" not in type(exc).__name__ and "rate limit" not in str(exc).lower():
                    raise
                time.sleep(retry_seconds)
                embeddings.extend(embed_texts(batch))
        return embeddings

    return embed_in_batches


def _anonymize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    proposal_aliases: dict[str, str] = {}
    document_aliases: dict[str, str] = {}
    anonymized: list[dict[str, Any]] = []

    for index, chunk in enumerate(chunks, start=1):
        metadata = dict(chunk.get("metadata") or {})
        proposal_id = str(
            chunk.get("proposal_id")
            or metadata.get("proposal_id")
            or f"proposal_{index:03d}"
        )
        document_id = str(
            chunk.get("document_id")
            or metadata.get("document_id")
            or proposal_id
        )
        proposal_alias = proposal_aliases.setdefault(
            proposal_id,
            f"proposal_{len(proposal_aliases) + 1:03d}",
        )
        document_alias = document_aliases.setdefault(
            document_id,
            f"{proposal_alias}__document_{len(document_aliases) + 1:03d}",
        )
        source_type = str(
            chunk.get("source_type")
            or metadata.get("source_type")
            or chunk.get("section")
            or "unknown"
        )
        chunk_index = int(chunk.get("chunk_index", metadata.get("chunk_index", 0)))
        chunk_alias = f"{document_alias}__chunk_{chunk_index + 1:03d}"

        anonymized.append(
            {
                "proposal_id": proposal_alias,
                "document_id": document_alias,
                "title": proposal_alias,
                "section": source_type,
                "source_type": source_type,
                "chunk_id": chunk_alias,
                "chunk_index": chunk_index,
                "text": str(chunk.get("text", "")),
                "opportunity_owner": metadata.get("opportunity_owner"),
                "opportunity_id": metadata.get("opportunity_id"),
                "metadata": {
                    "proposal_id": proposal_alias,
                    "chunk_id": chunk_alias,
                    "document_id": document_alias,
                    "source_type": source_type,
                    "chunk_index": chunk_index,
                    "opportunity_owner": metadata.get("opportunity_owner"),
                    "opportunity_id": metadata.get("opportunity_id"),
                    "approx_tokens": metadata.get("approx_tokens"),
                },
            }
        )

    return anonymized


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()

"""Evidence helpers for Sprint 4 RFP retrieval validation.

These functions keep Kian's final validation artifacts deterministic and
separate from live Azure calls. They answer whether retrieved chunks support
semantic similarity claims, and whether current metadata supports stronger
director or opportunity linkage claims.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

try:
    from src.rfp_preprocessor import RFPChunk
except ModuleNotFoundError:  # pragma: no cover
    from rfp_preprocessor import RFPChunk


TERM_PATTERN = re.compile(r"[A-Za-z0-9]+")


def summarize_chunk_evidence_support(chunks: Iterable[Any]) -> dict[str, Any]:
    """Summarize metadata fields available for retrieval-evidence claims."""

    chunk_list = list(chunks)
    source_type_counts: Counter[str] = Counter()
    proposal_ids: set[str] = set()
    document_ids: set[str] = set()
    chunks_with_text = 0
    chunks_with_proposal_id = 0
    chunks_with_document_id = 0
    chunks_with_opportunity_owner = 0
    chunks_with_opportunity_id = 0

    for chunk in chunk_list:
        text = str(_chunk_value(chunk, "text", "") or "").strip()
        proposal_id = _chunk_value(chunk, "proposal_id")
        document_id = _chunk_value(chunk, "document_id")
        source_type = _chunk_value(chunk, "source_type")
        opportunity_owner = _chunk_value(chunk, "opportunity_owner")
        opportunity_id = _chunk_value(chunk, "opportunity_id")

        if text:
            chunks_with_text += 1
        if proposal_id:
            chunks_with_proposal_id += 1
            proposal_ids.add(str(proposal_id))
        if document_id:
            chunks_with_document_id += 1
            document_ids.add(str(document_id))
        if source_type:
            source_type_counts[str(source_type)] += 1
        if opportunity_owner:
            chunks_with_opportunity_owner += 1
        if opportunity_id:
            chunks_with_opportunity_id += 1

    return {
        "total_chunks": len(chunk_list),
        "chunks_with_text": chunks_with_text,
        "chunks_with_proposal_id": chunks_with_proposal_id,
        "chunks_with_document_id": chunks_with_document_id,
        "chunks_with_opportunity_owner": chunks_with_opportunity_owner,
        "chunks_with_opportunity_id": chunks_with_opportunity_id,
        "unique_proposal_ids": len(proposal_ids),
        "unique_document_ids": len(document_ids),
        "source_type_counts": dict(sorted(source_type_counts.items())),
    }


def assess_claim_support(chunk_summary: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Assess which final-report claims the current chunk metadata supports."""

    total_chunks = _as_int(chunk_summary.get("total_chunks"))
    chunks_with_text = _as_int(chunk_summary.get("chunks_with_text"))
    chunks_with_source = sum(
        _as_int(count)
        for count in dict(chunk_summary.get("source_type_counts") or {}).values()
    )
    chunks_with_owner = _as_int(chunk_summary.get("chunks_with_opportunity_owner"))
    chunks_with_opportunity = _as_int(chunk_summary.get("chunks_with_opportunity_id"))

    similar_supported = (
        total_chunks > 0
        and chunks_with_text == total_chunks
        and chunks_with_source == total_chunks
    )
    director_supported = total_chunks > 0 and chunks_with_owner == total_chunks
    opportunity_supported = total_chunks > 0 and chunks_with_opportunity == total_chunks

    return {
        "similar_historical_rfp_claim": {
            "supported": similar_supported,
            "wording": (
                "Retrieved chunks can support semantic similarity to historical "
                "proposal/response text."
            ),
            "caveat": (
                "" if similar_supported else
                "Semantic similarity is weak because some chunks lack text or source type."
            ),
        },
        "director_experience_claim": {
            "supported": director_supported,
            "wording": (
                "Only claim proven director experience when every retrieved chunk "
                "has validated director linkage."
            ),
            "caveat": (
                "" if director_supported else
                "Retrieved chunks are not proven director experience because "
                "opportunity_owner/director linkage is missing or incomplete."
            ),
        },
        "opportunity_linkage_claim": {
            "supported": opportunity_supported,
            "wording": (
                "Only claim opportunity linkage when retrieved chunks have CRM "
                "opportunity IDs."
            ),
            "caveat": (
                "" if opportunity_supported else
                "Retrieved chunks are not linked to CRM opportunity IDs, so "
                "opportunity-level claims remain unsupported."
            ),
        },
    }


def evaluate_retrieval_example(
    query_theme: str,
    result: Mapping[str, Any],
    expected_terms: Iterable[str],
) -> dict[str, Any]:
    """Create a report-ready evidence row for one retrieved chunk."""

    expected = sorted(_normalize_terms(expected_terms))
    supporting_text = str(result.get("supporting_text", "") or "")
    text_terms = _text_terms(supporting_text)
    matched_terms = sorted(term for term in expected if term in text_terms)
    looks_relevant = bool(matched_terms)
    supports_reason = looks_relevant and bool(supporting_text.strip())
    weak_note = _weak_note(
        expected_terms=expected,
        matched_terms=matched_terms,
        supporting_text=supporting_text,
        similarity_score=result.get("similarity_score"),
    )

    return {
        "query_theme": query_theme,
        "proposal_id": result.get("proposal_id", "unknown"),
        "chunk_id": result.get("chunk_id", ""),
        "similarity_score": result.get("similarity_score"),
        "matched_expected_terms": matched_terms,
        "looks_relevant": looks_relevant,
        "supports_summary_or_match_reason": supports_reason,
        "weak_or_misleading_note": weak_note,
        "supporting_text_preview": _safe_text_preview(
            supporting_text=supporting_text,
            matched_terms=matched_terms,
        ),
    }


def compare_retrieval_paths(
    query_theme: str,
    azure_results: list[Mapping[str, Any]],
    local_results: list[Mapping[str, Any]],
    expected_terms: Iterable[str],
) -> dict[str, Any]:
    """Compare Azure/Chroma retrieval against local fallback retrieval."""

    azure_ids = _chunk_ids(azure_results)
    local_ids = _chunk_ids(local_results)
    overlap = sorted(set(azure_ids).intersection(local_ids))
    azure_available = bool(azure_results)
    local_available = bool(local_results)
    top_result_agrees = bool(
        azure_ids and local_ids and azure_ids[0] == local_ids[0]
    )

    azure_top = (
        evaluate_retrieval_example(query_theme, azure_results[0], expected_terms)
        if azure_results else None
    )
    local_top = (
        evaluate_retrieval_example(query_theme, local_results[0], expected_terms)
        if local_results else None
    )

    return {
        "query_theme": query_theme,
        "azure_available": azure_available,
        "local_available": local_available,
        "azure_top_chunk_ids": azure_ids,
        "local_top_chunk_ids": local_ids,
        "overlap_chunk_ids": overlap,
        "overlap_count": len(overlap),
        "top_result_agrees": top_result_agrees,
        "azure_top_evidence": azure_top,
        "local_top_evidence": local_top,
        "quality_note": _comparison_note(
            azure_available=azure_available,
            local_available=local_available,
            top_result_agrees=top_result_agrees,
            overlap_count=len(overlap),
        ),
    }


def _chunk_value(chunk: Any, field: str, default: Any = None) -> Any:
    """Read a field from either a chunk dict, RFPChunk, or metadata."""

    if isinstance(chunk, Mapping):
        if field in chunk:
            return chunk[field]
        metadata = chunk.get("metadata")
        if isinstance(metadata, Mapping):
            return metadata.get(field, default)
        return default

    if isinstance(chunk, RFPChunk):
        if hasattr(chunk, field):
            return getattr(chunk, field)
        return chunk.metadata.get(field, default)

    return default


def _text_terms(text: str) -> set[str]:
    return {match.group(0).lower() for match in TERM_PATTERN.finditer(text)}


def _normalize_terms(terms: Iterable[str]) -> set[str]:
    normalized: set[str] = set()
    for term in terms:
        normalized.update(_text_terms(str(term)))
    return normalized


def _weak_note(
    *,
    expected_terms: list[str],
    matched_terms: list[str],
    supporting_text: str,
    similarity_score: Any,
) -> str:
    if not supporting_text.strip():
        return "Retrieved chunk has no supporting text."
    if not matched_terms:
        return "No expected theme terms found in supporting text."
    score = _as_float(similarity_score)
    if score is not None and score < 0.25:
        return "Similarity score is low despite partial theme overlap."
    if expected_terms and len(matched_terms) == 1 and len(expected_terms) >= 3:
        return "Only one expected theme term matched; review manually."
    return ""


def _chunk_ids(results: list[Mapping[str, Any]]) -> list[str]:
    return [
        str(result.get("chunk_id"))
        for result in results
        if result.get("chunk_id")
    ]


def _comparison_note(
    *,
    azure_available: bool,
    local_available: bool,
    top_result_agrees: bool,
    overlap_count: int,
) -> str:
    if not azure_available and not local_available:
        return "Neither retrieval path returned results."
    if not azure_available:
        return "Azure/Chroma retrieval unavailable; local fallback result is the only evidence."
    if not local_available:
        return "Local fallback retrieval unavailable; Azure/Chroma result is the only evidence."
    if top_result_agrees:
        return "Top Azure/Chroma and local fallback result agree."
    if overlap_count:
        return "Retrieval paths share some results but rank them differently."
    return "Retrieval paths returned different evidence; review before using in final wording."


def _safe_text_preview(
    *,
    supporting_text: str,
    matched_terms: list[str],
) -> str:
    """Describe retrieved text without exporting raw proposal content."""

    char_count = len(supporting_text)
    return (
        f"[redacted: {char_count} chars, "
        f"{len(matched_terms)} matched expected terms]"
    )


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

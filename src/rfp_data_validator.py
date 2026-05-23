"""Validation helpers for historical RFP JSON and chunk metadata.

This module provides reproducible checks for Sprint 3 issue #38:
- profile `proposals_responses.json` structure
- summarize proposal/response document lengths
- detect malformed or unusual records
- validate required chunk metadata fields for retrieval handoff
"""

from __future__ import annotations

import json
import hashlib
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from src.rfp_preprocessor import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_OVERLAP,
    DEFAULT_PROPOSAL_JSON_PATH,
    RFPChunk,
    estimate_token_count,
    extract_rfp_documents,
    normalize_text_content,
    preprocess_proposals,
)

SHORT_DOCUMENT_TOKENS = 80
LONG_DOCUMENT_TOKENS = 1200
MALFORMED_TEXT_TYPES = {"none", "empty", "scalar"}
REQUIRED_CHUNK_FIELDS = (
    "proposal_id",
    "chunk_id",
    "document_id",
    "source_type",
    "chunk_index",
    "text",
    "opportunity_owner",
    "opportunity_id",
)


def load_proposals_json(path: str | Path = DEFAULT_PROPOSAL_JSON_PATH) -> dict[str, Any]:
    """Load proposal JSON from disk with a consistent mapping contract."""

    json_path = Path(path)
    with json_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise TypeError(
            "proposals_responses.json must be a JSON object of title -> record mappings"
        )
    return payload


def summarize_structure(proposals: dict[str, Any]) -> dict[str, Any]:
    """Return shape and consistency counters for top-level proposal records."""

    total_records = len(proposals)
    valid_mapping_records = 0
    non_mapping_records = 0
    records_with_proposal_key = 0
    records_with_response_key = 0
    response_key_distribution: Counter[str] = Counter()
    malformed_record_refs: list[str] = []

    for record_index, (title, entry) in enumerate(proposals.items()):
        record_ref = f"record_{record_index + 1:03d}"
        if not isinstance(entry, dict):
            non_mapping_records += 1
            malformed_record_refs.append(record_ref)
            continue

        valid_mapping_records += 1
        if "proposal" in entry:
            records_with_proposal_key += 1
        proposal_block = entry.get("proposal", entry)
        if isinstance(proposal_block, dict):
            if "proposal_response" in proposal_block or "proposal_responses" in proposal_block:
                records_with_response_key += 1
            if "proposal_response" in proposal_block:
                response_key_distribution["proposal_response"] += 1
            if "proposal_responses" in proposal_block:
                response_key_distribution["proposal_responses"] += 1

    return {
        "total_records": total_records,
        "valid_mapping_records": valid_mapping_records,
        "non_mapping_records": non_mapping_records,
        "records_with_proposal_key": records_with_proposal_key,
        "records_with_response_key": records_with_response_key,
        "response_key_distribution": dict(sorted(response_key_distribution.items())),
        "malformed_record_count": len(malformed_record_refs),
        "malformed_record_refs": sorted(malformed_record_refs),
    }


def profile_documents(proposals: dict[str, Any]) -> list[dict[str, Any]]:
    """Create one profile row per extracted proposal/response document."""

    profiles: list[dict[str, Any]] = []
    for document in extract_rfp_documents(proposals):
        token_count = estimate_token_count(document.text)
        profiles.append(
            {
                "document_id": document.document_id,
                "proposal_id": document.metadata.get("proposal_id"),
                "source_title": document.title,
                "section": document.section,
                "source_type": document.metadata.get("source_type"),
                "char_count": len(document.text),
                "token_count_estimate": token_count,
                "is_empty": token_count == 0,
                "is_short": 0 < token_count < SHORT_DOCUMENT_TOKENS,
                "is_long": token_count > LONG_DOCUMENT_TOKENS,
                "opportunity_owner": document.metadata.get("opportunity_owner"),
                "opportunity_id": document.metadata.get("opportunity_id"),
            }
        )
    return profiles


def summarize_document_lengths(document_profiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute distribution statistics for document length quality checks."""

    if not document_profiles:
        return {
            "total_documents": 0,
            "proposal_documents": 0,
            "response_documents": 0,
            "empty_documents": 0,
            "short_documents": 0,
            "long_documents": 0,
            "token_count": {},
            "char_count": {},
        }

    token_lengths = [int(item["token_count_estimate"]) for item in document_profiles]
    char_lengths = [int(item["char_count"]) for item in document_profiles]
    source_type_counter = Counter(str(item.get("source_type", "unknown")) for item in document_profiles)

    return {
        "total_documents": len(document_profiles),
        "proposal_documents": int(source_type_counter.get("proposal", 0)),
        "response_documents": int(source_type_counter.get("proposal_response", 0)),
        "empty_documents": sum(1 for item in document_profiles if item["is_empty"]),
        "short_documents": sum(1 for item in document_profiles if item["is_short"]),
        "long_documents": sum(1 for item in document_profiles if item["is_long"]),
        "token_count": _numeric_summary(token_lengths),
        "char_count": _numeric_summary(char_lengths),
    }


def find_malformed_records(
    proposals: dict[str, Any],
    *,
    include_sensitive_fields: bool = False,
) -> list[dict[str, Any]]:
    """Return records with potentially problematic content shapes."""

    issues: list[dict[str, Any]] = []
    for record_index, (title, entry) in enumerate(proposals.items()):
        record_ref = f"record_{record_index + 1:03d}"
        title_hash = _hash_text(str(title))
        if not isinstance(entry, dict):
            issues.append(
                {
                    "record_ref": record_ref,
                    "title_hash": title_hash,
                    "issue": "entry_not_mapping",
                    "details": str(type(entry).__name__),
                }
            )
            if include_sensitive_fields:
                issues[-1]["title"] = str(title)
            continue

        proposal_block = entry.get("proposal", entry)
        if not isinstance(proposal_block, dict):
            issues.append(
                {
                    "record_ref": record_ref,
                    "title_hash": title_hash,
                    "issue": "proposal_not_mapping",
                    "details": str(type(proposal_block).__name__),
                }
            )
            if include_sensitive_fields:
                issues[-1]["title"] = str(title)
            continue

        proposal_content_issue = _classify_text_shape(proposal_block.get("content"))
        if proposal_content_issue in MALFORMED_TEXT_TYPES:
            issues.append(
                {
                    "record_ref": record_ref,
                    "title_hash": title_hash,
                    "issue": "proposal_content_unusable",
                    "details": proposal_content_issue,
                }
            )
            if include_sensitive_fields:
                issues[-1]["title"] = str(title)

        responses = proposal_block.get(
            "proposal_response",
            proposal_block.get("proposal_responses"),
        )
        if responses is None:
            continue
        if not isinstance(responses, (dict, list)):
            issues.append(
                {
                    "record_ref": record_ref,
                    "title_hash": title_hash,
                    "issue": "proposal_response_unsupported_shape",
                    "details": str(type(responses).__name__),
                }
            )
            if include_sensitive_fields:
                issues[-1]["title"] = str(title)

    return sorted(issues, key=lambda item: (item["record_ref"], item["issue"]))


def summarize_proposal_response_separation(proposals: dict[str, Any]) -> dict[str, Any]:
    """Check whether proposal and response text are separated consistently."""

    total_records = len(proposals)
    records_with_proposal_text = 0
    records_with_response_container = 0
    records_with_nonempty_response_text = 0
    records_missing_both = 0

    for entry in proposals.values():
        if not isinstance(entry, dict):
            continue
        proposal_block = entry.get("proposal", entry)
        if not isinstance(proposal_block, dict):
            continue

        proposal_tokens = estimate_token_count(
            str(proposal_block.get("content", "") or "")
        )
        has_proposal_text = proposal_tokens > 0
        if has_proposal_text:
            records_with_proposal_text += 1

        responses = proposal_block.get(
            "proposal_response",
            proposal_block.get("proposal_responses"),
        )
        has_response_container = isinstance(responses, (dict, list)) and len(responses) > 0
        if has_response_container:
            records_with_response_container += 1

        if has_response_container:
            response_text_found = False
            response_items = (
                responses.values() if isinstance(responses, dict) else responses
            )
            for response_item in response_items:
                if estimate_token_count(normalize_text_content(response_item)) > 0:
                    response_text_found = True
                    break
            if response_text_found:
                records_with_nonempty_response_text += 1

        if not has_proposal_text and not has_response_container:
            records_missing_both += 1

    return {
        "total_records": total_records,
        "records_with_proposal_text": records_with_proposal_text,
        "records_with_response_container": records_with_response_container,
        "records_with_nonempty_response_text": records_with_nonempty_response_text,
        "records_missing_both": records_missing_both,
    }


def generate_sample_chunk_rows(
    proposals: dict[str, Any],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    sample_size: int = 8,
    include_text: bool = False,
    max_text_chars: int = 180,
    anonymize_ids: bool = False,
) -> list[dict[str, Any]]:
    """Create sample chunk rows for handoff to retrieval/assignment owners."""

    chunks = preprocess_proposals(proposals, chunk_size=chunk_size, overlap=overlap)
    proposal_aliases = _stable_alias_lookup(
        [str(chunk.metadata.get("proposal_id") or "") for chunk in chunks],
        prefix="proposal",
    )
    document_aliases = _stable_alias_lookup(
        [str(chunk.document_id) for chunk in chunks],
        prefix="document",
    )
    sample_rows: list[dict[str, Any]] = []

    for chunk in chunks[: max(sample_size, 0)]:
        sample_rows.append(
            _sample_row_from_chunk(
                chunk,
                include_text=include_text,
                max_text_chars=max_text_chars,
                anonymize_ids=anonymize_ids,
                proposal_aliases=proposal_aliases,
                document_aliases=document_aliases,
            )
        )

    return sample_rows


def validate_chunk_metadata_fields(
    proposals: dict[str, Any],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> dict[str, Any]:
    """Validate required chunk metadata fields and nullability patterns."""

    chunks = preprocess_proposals(proposals, chunk_size=chunk_size, overlap=overlap)
    missing_counts = {field: 0 for field in REQUIRED_CHUNK_FIELDS}
    null_counts = {field: 0 for field in REQUIRED_CHUNK_FIELDS}
    source_type_counts: Counter[str] = Counter()

    for chunk in chunks:
        row = _chunk_to_required_fields(chunk)
        expected_presence = {
            "proposal_id": "proposal_id" in chunk.metadata,
            "chunk_id": bool(chunk.chunk_id),
            "document_id": bool(chunk.document_id),
            "source_type": "source_type" in chunk.metadata,
            "chunk_index": True,
            "text": True,
            "opportunity_owner": "opportunity_owner" in chunk.metadata,
            "opportunity_id": "opportunity_id" in chunk.metadata,
        }
        source_type_counts[str(row.get("source_type") or "unknown")] += 1
        for field in REQUIRED_CHUNK_FIELDS:
            if not expected_presence[field]:
                missing_counts[field] += 1
                continue
            value = row.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                null_counts[field] += 1

    return {
        "total_chunks": len(chunks),
        "required_fields": list(REQUIRED_CHUNK_FIELDS),
        "missing_field_counts": missing_counts,
        "null_field_counts": null_counts,
        "source_type_counts": dict(sorted(source_type_counts.items())),
        "can_link_to_owner_or_opportunity": (
            null_counts["opportunity_owner"] < len(chunks)
            or null_counts["opportunity_id"] < len(chunks)
        ),
    }


def build_validation_report(
    proposals: dict[str, Any],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> dict[str, Any]:
    """Build the full issue #38 validation payload."""

    document_profiles = profile_documents(proposals)
    metadata_validation = validate_chunk_metadata_fields(
        proposals, chunk_size=chunk_size, overlap=overlap
    )

    return {
        "structure_summary": summarize_structure(proposals),
        "document_length_summary": summarize_document_lengths(document_profiles),
        "proposal_response_separation": summarize_proposal_response_separation(proposals),
        "malformed_records": find_malformed_records(proposals),
        "chunk_metadata_validation": metadata_validation,
        "linkage_limitations": _build_linkage_notes(metadata_validation),
    }


def _numeric_summary(values: list[int]) -> dict[str, float | int]:
    ordered = sorted(values)
    if not ordered:
        return {}
    return {
        "min": ordered[0],
        "max": ordered[-1],
        "mean": round(mean(ordered), 2),
        "median": float(median(ordered)),
        "p25": float(_percentile(ordered, 0.25)),
        "p75": float(_percentile(ordered, 0.75)),
    }


def _percentile(ordered: list[int], ratio: float) -> float:
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return float(ordered[0])
    index = ratio * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _classify_text_shape(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, str):
        return "string" if value.strip() else "empty"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "mapping"
    return "scalar"


def _chunk_to_required_fields(chunk: RFPChunk) -> dict[str, Any]:
    return {
        "proposal_id": chunk.metadata.get("proposal_id"),
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "source_type": chunk.metadata.get("source_type"),
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "opportunity_owner": chunk.metadata.get("opportunity_owner"),
        "opportunity_id": chunk.metadata.get("opportunity_id"),
    }


def _sample_row_from_chunk(
    chunk: RFPChunk,
    *,
    include_text: bool,
    max_text_chars: int,
    anonymize_ids: bool,
    proposal_aliases: dict[str, str],
    document_aliases: dict[str, str],
) -> dict[str, Any]:
    row = _chunk_to_required_fields(chunk)
    if anonymize_ids:
        proposal_key = str(chunk.metadata.get("proposal_id") or "")
        document_key = str(chunk.document_id)
        proposal_alias = proposal_aliases.get(proposal_key, "proposal_000")
        document_alias = document_aliases.get(document_key, "document_000")
        row["proposal_id"] = proposal_alias
        row["document_id"] = document_alias
        row["chunk_id"] = f"{document_alias}__chunk_{chunk.chunk_index:04d}"
        row["opportunity_owner"] = None
        row["opportunity_id"] = None
    row["text_char_count"] = len(chunk.text)
    row["text_token_count_estimate"] = estimate_token_count(chunk.text)
    if include_text:
        row["text"] = chunk.text[:max_text_chars].strip()
    else:
        row["text"] = "<redacted; use --include-text to export preview>"
    return row


def _stable_alias_lookup(values: list[str], *, prefix: str) -> dict[str, str]:
    ordered_unique = sorted({value for value in values if value})
    return {
        value: f"{prefix}_{index + 1:03d}"
        for index, value in enumerate(ordered_unique)
    }


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _build_linkage_notes(metadata_validation: dict[str, Any]) -> list[str]:
    if metadata_validation.get("can_link_to_owner_or_opportunity"):
        return [
            "At least one chunk contains non-null opportunity linkage fields.",
            "Treat linkage as partial and verify joins before ranking directors.",
        ]

    return [
        "Chunks do not currently carry reliable opportunity_owner/opportunity_id values.",
        "Proposal-to-director mapping cannot be inferred from chunk metadata alone.",
        "Director ranking should rely on retrieval evidence + separate capacity tables until linkage is provided.",
    ]

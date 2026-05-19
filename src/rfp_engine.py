"""Dashboard-facing RFP assignment interface for the Week 2 prototype.

This module connects the RFP chunking and local retrieval wrappers into one
function the Streamlit dashboard can call. The director recommendation is still
mock/basic for now, but the output shape matches the Week 2 work plan.

Run project files from the repository root so imports resolve consistently.
For example: `python src/rfp_engine.py`.
"""

from __future__ import annotations

from typing import Any

try:
    from src.rfp_preprocessor import load_sample_rfp_text, prepare_rfp_chunks
    from src.vector_store import build_vector_store
except ModuleNotFoundError:
    from rfp_preprocessor import load_sample_rfp_text, prepare_rfp_chunks
    from vector_store import build_vector_store


def generate_assignment_context(
    rfp_text: str,
    director_df: Any = None,
    historical_chunks: list[dict[str, Any]] | None = None,
):
    """Generate the RFP assignment context used by the dashboard.

    This is not the final recommendation model. It prepares RFP chunks, runs
    local retrieval, and returns a stable prototype payload so the dashboard can
    be wired to the Role 5 interface while Azure/Chroma work is still pending.

    @param rfp_text: New RFP text pasted or uploaded in the dashboard.
    @param director_df: Optional director/capacity dataframe or similar object.
    @param historical_chunks: Optional prebuilt historical/sample chunk corpus.
    @return: Week 2 dashboard-ready RFP assignment context.
    """

    used_sample_corpus = historical_chunks is None
    chunks = (
        historical_chunks
        if historical_chunks is not None
        else _default_historical_chunks()
    )
    retrieved_examples = _retrieve_from_chunks(
        chunks=chunks,
        query=rfp_text,
        top_k=3,
    )
    supporting_chunk_ids = [
        example["chunk_id"] for example in retrieved_examples
    ]
    risk_flags = _risk_flags(
        retrieved_examples,
        used_sample_corpus=used_sample_corpus,
    )
    recommended_directors = _director_recommendations(
        director_df,
        supporting_chunk_ids,
        risk_flags,
    )

    return {
        "rfp_summary": _summarize_rfp_text(rfp_text),
        "effort": _effort_estimate(rfp_text, retrieved_examples),
        "similar_rfps": _similar_rfps(retrieved_examples),
        "retrieved_examples": retrieved_examples,
        "recommended_directors": recommended_directors,
        "risk_flags": risk_flags,
        "notes": _notes(used_sample_corpus=used_sample_corpus),
    }


def _default_historical_chunks() -> list[dict[str, Any]]:
    """Build a small historical/sample corpus when no persisted store is ready."""

    sample_text = load_sample_rfp_text()
    chunks = prepare_rfp_chunks(sample_text)
    for chunk in chunks:
        chunk["proposal_id"] = "historical_sample"
        chunk["chunk_id"] = (
            f"historical_sample_chunk_{int(chunk['chunk_index']) + 1:03d}"
        )
        chunk["source_type"] = "historical_sample"
    return chunks


def _retrieve_from_chunks(
    chunks: list[dict[str, Any]] | None,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    """Build a fresh store from the retrieval corpus and query it directly."""

    store = build_vector_store(chunks or [])
    return [
        result.to_retrieved_example()
        for result in store.query(query, top_k=top_k)
    ]


def _summarize_rfp_text(rfp_text: str, max_chars: int = 180) -> str:
    """Create a short placeholder summary from the RFP text.

    @param rfp_text: New RFP text from the dashboard.
    @param max_chars: Maximum number of characters to keep in the summary.
    @return: Short summary string for the dashboard.
    """

    clean_text = " ".join(str(rfp_text).split())
    if not clean_text:
        return "Short summary of the input RFP"
    if len(clean_text) <= max_chars:
        return clean_text
    return f"{clean_text[:max_chars].rstrip()}..."


def _director_recommendations(
    director_df: Any,
    supporting_chunks: list[str],
    risk_flags: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Create prototype director recommendation records.

    The real capacity scoring module will own the final ranking later. For
    Week 2, this function uses the first few director records if provided and a
    small mock director if not.

    @param director_df: Optional dataframe/list of director capacity records.
    @param supporting_chunks: Chunk IDs supporting the prototype match.
    @return: Dashboard-ready director recommendation dictionaries.
    """

    records = _director_records(director_df) or [_mock_director_record()]
    flags = [flag["message"] for flag in risk_flags or []]

    return [
        _director_record(
            record=record,
            supporting_chunks=supporting_chunks,
            risk_flags=flags,
        )
        for record in records[:3]
    ]


def _director_record(
    record: dict[str, Any],
    supporting_chunks: list[str],
    risk_flags: list[str],
) -> dict[str, Any]:
    """Normalize and score one prototype director recommendation."""

    capacity_score = _as_float(record.get("capacity_score"), default=0.72)
    relative_load = _as_float(record.get("relative_load"), default=0.65)
    assignment_score = _as_float(
        record.get("assignment_score"),
        default=round((capacity_score * 0.45) + (0.35 if supporting_chunks else 0.15), 3),
    )
    director_name = str(
        record.get(
            "director_name",
            record.get("opportunity_owner", record.get("name", "Director A")),
        )
    )
    capacity_label = str(record.get("capacity_label", "Available"))
    match_reason = str(
        record.get(
            "match_reason",
            "Relevant historical experience and available capacity",
        )
    )

    return {
        "director_name": director_name,
        "capacity_label": capacity_label,
        "capacity_score": capacity_score,
        "relative_load": relative_load,
        "assignment_score": assignment_score,
        "match_reason": match_reason,
        "capacity_explanation": record.get(
            "capacity_explanation",
            f"{director_name} is currently labeled {capacity_label} "
            f"with capacity score {capacity_score:.2f} and relative load {relative_load:.2f}.",
        ),
        "experience_match_explanation": record.get(
            "experience_match_explanation",
            "Prototype fit is based on the retrieved historical/sample RFP chunks.",
        ),
        "risk_flags": list(record.get("risk_flags", risk_flags)),
        "supporting_chunks": list(record.get("supporting_chunks", supporting_chunks[:2])),
    }


def _director_records(director_df: Any) -> list[dict[str, Any]]:
    """Convert common dataframe-like inputs into a list of dictionaries.

    @param director_df: Optional pandas dataframe, list, tuple, or dictionary.
    @return: Director records as plain dictionaries.
    """

    if director_df is None:
        return []
    if hasattr(director_df, "empty") and director_df.empty:
        return []
    if hasattr(director_df, "to_dict"):
        try:
            return list(director_df.to_dict(orient="records"))
        except TypeError:
            pass
    if isinstance(director_df, dict):
        return [director_df]
    if isinstance(director_df, (list, tuple)):
        return [
            dict(record)
            for record in director_df
            if isinstance(record, dict)
        ]
    return []


def _risk_flags(
    retrieved_examples: list[dict[str, Any]],
    used_sample_corpus: bool = False,
) -> list[dict[str, str]]:
    """Create simple prototype risk flags for the dashboard.

    @param retrieved_examples: Retrieved chunks from the local baseline.
    @return: Risk flag dictionaries.
    """

    flags = []
    if used_sample_corpus:
        flags.append(
            {
                "level": "Medium",
                "message": (
                    "Built-in sample historical corpus was used because real "
                    "historical proposal data was unavailable."
                ),
            }
        )
    if len(retrieved_examples) < 3:
        flags.append(
            {
                "level": "Medium",
                "message": "Limited historical examples found for this RFP type.",
            }
        )
    return flags


def _notes(used_sample_corpus: bool = False) -> str:
    if used_sample_corpus:
        return (
            "Prototype output for dashboard integration. Built-in sample "
            "historical corpus used because real historical proposal data was unavailable."
        )
    return "Prototype output for dashboard integration."


def _effort_estimate(
    rfp_text: str,
    retrieved_examples: list[dict[str, Any]],
) -> dict[str, str]:
    """Create a deterministic placeholder effort estimate for the dashboard."""

    word_count = len(str(rfp_text).split())
    if word_count >= 800:
        level = "High"
        duration = "6-8 weeks"
    elif word_count >= 250:
        level = "Medium"
        duration = "3-5 weeks"
    else:
        level = "Low"
        duration = "1-2 weeks"

    rationale = (
        "Prototype estimate based on RFP length and retrieved historical/sample "
        f"examples ({len(retrieved_examples)} matches)."
    )
    return {
        "level": level,
        "estimated_duration": duration,
        "rationale": rationale,
    }


def _similar_rfps(retrieved_examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose retrieved examples under the dashboard's similar-RFP contract."""

    return [
        {
            "title": example.get("proposal_id", "Historical proposal"),
            "similarity_score": example.get("similarity_score", 0.0),
            "matched_chunk": example.get("supporting_text", ""),
            "source": example.get("chunk_id", ""),
        }
        for example in retrieved_examples
    ]


def _mock_director_record() -> dict[str, Any]:
    """Return the fallback director record used when capacity data is missing."""

    return {
        "director_name": "Director A",
        "capacity_label": "Available",
        "capacity_score": 0.72,
        "relative_load": 0.65,
        "match_reason": "Relevant historical experience and available capacity",
    }


def _as_float(value: Any, default: float) -> float:
    """Convert numeric dashboard fields without failing on missing values."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default

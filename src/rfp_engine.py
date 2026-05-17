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
    from src.rfp_preprocessor import prepare_rfp_chunks
    from src.vector_store import build_vector_store, retrieve_relevant_chunks
except ModuleNotFoundError:
    from rfp_preprocessor import prepare_rfp_chunks
    from vector_store import build_vector_store, retrieve_relevant_chunks


def generate_assignment_context(
    rfp_text: str,
    director_df: Any = None,
):
    """Generate the RFP assignment context used by the dashboard.

    This is not the final recommendation model. It prepares RFP chunks, runs
    local retrieval, and returns a stable prototype payload so the dashboard can
    be wired to the Role 5 interface while Azure/Chroma work is still pending.

    @param rfp_text: New RFP text pasted or uploaded in the dashboard.
    @param director_df: Optional director/capacity dataframe or similar object.
    @return: Week 2 dashboard-ready RFP assignment context.
    """

    chunks = prepare_rfp_chunks(rfp_text)
    build_vector_store(chunks)
    retrieved_examples = retrieve_relevant_chunks(rfp_text, top_k=3)
    supporting_chunk_ids = [
        example["chunk_id"] for example in retrieved_examples
    ]

    return {
        "rfp_summary": _summarize_rfp_text(rfp_text),
        "retrieved_examples": retrieved_examples,
        "recommended_directors": _director_recommendations(
            director_df,
            supporting_chunk_ids,
        ),
        "risk_flags": _risk_flags(retrieved_examples),
        "notes": "Prototype output for dashboard integration.",
    }


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

    return [
        {
            "director_name": str(
                record.get(
                    "director_name",
                    record.get("opportunity_owner", record.get("name", "Director A")),
                )
            ),
            "capacity_label": str(record.get("capacity_label", "Available")),
            "capacity_score": _as_float(record.get("capacity_score"), default=0.72),
            "relative_load": _as_float(record.get("relative_load"), default=0.65),
            "match_reason": str(
                record.get(
                    "match_reason",
                    "Relevant historical experience and available capacity",
                )
            ),
            "supporting_chunks": list(
                record.get("supporting_chunks", supporting_chunks[:2])
            ),
        }
        for record in records[:3]
    ]


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


def _risk_flags(retrieved_examples: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Create simple prototype risk flags for the dashboard.

    @param retrieved_examples: Retrieved chunks from the local baseline.
    @return: Risk flag dictionaries.
    """

    if len(retrieved_examples) >= 3:
        return []
    return [
        {
            "level": "Medium",
            "message": "Limited historical examples found for this RFP type.",
        }
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

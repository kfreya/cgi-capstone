"""Dashboard-facing RFP assignment interface.

This module keeps the Week 1 RFP output shape aligned with the Streamlit
placeholder. The logic is still mock/basic for now, but the function names and
payload match the dashboard contract so integration can happen cleanly.

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


def generate_assignment_context(rfp_text: str, director_df: Any) -> dict[str, Any]:
    """Generate the mock RFP assignment output used by the dashboard.

    This is not the final recommendation model. It prepares RFP chunks, runs
    local retrieval, and returns a stable mock payload so the dashboard can be
    wired to the Role 5 interface.

    @param rfp_text: New RFP text pasted or uploaded in the dashboard.
    @param director_df: Director/capacity dataframe or dataframe-like object.
    @return: Dashboard-ready RFP assignment context.
    """

    chunks = prepare_rfp_chunks(rfp_text)
    build_vector_store(chunks)
    retrieved_chunks = retrieve_relevant_chunks(rfp_text, top_k=2)
    supporting_chunks = [chunk["text"] for chunk in retrieved_chunks]

    return {
        "rfp_summary": _summarize_rfp_text(rfp_text),
        "recommended_directors": [
            {
                "director_name": _first_director_name(director_df),
                "match_reason": "Relevant experience and available capacity",
                "capacity_label": _first_capacity_label(director_df),
                "supporting_chunks": supporting_chunks,
            }
        ],
        "notes": "This is a mock output for dashboard integration.",
    }


def _summarize_rfp_text(rfp_text: str, max_chars: int = 180) -> str:
    """Create a short placeholder summary from the RFP text."""

    clean_text = " ".join(str(rfp_text).split())
    if not clean_text:
        return "Short summary of the RFP"
    if len(clean_text) <= max_chars:
        return clean_text
    return f"{clean_text[:max_chars].rstrip()}..."


def _first_director_name(director_df: Any) -> str:
    """Return the first available director name from a dataframe-like object."""

    if director_df is None:
        return "Director A"
    if hasattr(director_df, "empty") and director_df.empty:
        return "Director A"
    if hasattr(director_df, "columns") and "opportunity_owner" in director_df.columns:
        return str(director_df.iloc[0]["opportunity_owner"])
    if isinstance(director_df, list) and director_df:
        first = director_df[0]
        if isinstance(first, dict):
            return str(first.get("opportunity_owner", first.get("director_name", "Director A")))
    return "Director A"


def _first_capacity_label(director_df: Any) -> str:
    """Return the first capacity label from a dataframe-like object."""

    if director_df is None:
        return "Available"
    if hasattr(director_df, "empty") and director_df.empty:
        return "Available"
    if hasattr(director_df, "columns") and "capacity_label" in director_df.columns:
        return str(director_df.iloc[0]["capacity_label"])
    if isinstance(director_df, list) and director_df:
        first = director_df[0]
        if isinstance(first, dict):
            return str(first.get("capacity_label", "Available"))
    return "Available"

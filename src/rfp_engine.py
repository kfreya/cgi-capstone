"""Dashboard-facing RFP assignment interface for the Week 3 prototype.

This module connects the RFP chunking and local retrieval wrappers into one
function the Streamlit dashboard can call. The recommendation logic is still
heuristic, but it now combines retrieval evidence, capacity signals, and risk
flags while keeping the dashboard output contract stable.

Run project files from the repository root so imports resolve consistently.
For example: `python src/rfp_engine.py`.
"""

from __future__ import annotations

import json
import math
from typing import Any

try:
    from src.azure_rag_client import fallback_retrieval_report, preferred_retrieval_report
    from src.rfp_preprocessor import load_sample_rfp_text, prepare_rfp_chunks
    from src.vector_store import build_vector_store
except ModuleNotFoundError:
    from azure_rag_client import fallback_retrieval_report, preferred_retrieval_report
    from rfp_preprocessor import load_sample_rfp_text, prepare_rfp_chunks
    from vector_store import build_vector_store


_AUTO = object()
_RFP_SNIPPET_CHARS = 4000

SERVICE_KEYWORDS = {
    "cloud": {"cloud", "azure", "infrastructure", "migration"},
    "data_analytics": {"data", "analytics", "dashboard", "reporting", "forecasting"},
    "security": {"security", "privacy", "compliance", "risk"},
    "managed_services": {"managed", "service", "support", "operations"},
    "applications": {"application", "systems", "integration", "architecture"},
    "change_management": {"change", "training", "adoption", "stakeholder"},
}
COMPLEXITY_TERMS = {
    "multi-year",
    "enterprise",
    "integration",
    "migration",
    "security",
    "privacy",
    "architecture",
    "managed",
    "multiple",
    "onsite",
    "on-site",
}


def generate_assignment_context(
    rfp_text: str,
    director_df: Any = None,
    historical_chunks: list[dict[str, Any]] | None = None,
    _chat_fn: Any = _AUTO,
):
    """Generate the RFP assignment context used by the dashboard.

    This is not the final recommendation model. It runs local/fallback
    retrieval and returns a stable prototype payload so the dashboard can be
    wired to the Role 5 interface while Azure/Chroma work is still pending.

    @param rfp_text: New RFP text pasted or uploaded in the dashboard.
    @param director_df: Optional director/capacity dataframe or similar object.
    @param historical_chunks: Optional prebuilt historical/sample chunk corpus.
    @param _chat_fn: Chat function for LLM enrichment. Pass None to disable,
        or a callable to override. Defaults to auto-detect Azure chat availability.
    @return: Week 4 dashboard-ready RFP assignment context.
    """

    used_sample_corpus = historical_chunks is None
    chunks = (
        historical_chunks
        if historical_chunks is not None
        else _default_historical_chunks()
    )
    retrieval_report = _build_retrieval_report(
        chunks=chunks,
        query=rfp_text,
        top_k=3,
    )
    retrieval_mode = retrieval_report.get("retrieval_mode", retrieval_report.get("backend", "local_fallback"))
    retrieval_status = retrieval_report.get("status", {})
    retrieved_examples = retrieval_report.get("retrieved_examples", [])
    supporting_chunk_ids = [
        example["chunk_id"] for example in retrieved_examples
    ]
    director_records = _director_records(director_df)

    chat_fn = _resolve_chat_fn(_chat_fn)
    llm_data: dict[str, Any] | None = None
    llm_failed = False
    if chat_fn is not None and rfp_text.strip():
        llm_data = _llm_enrich(rfp_text, director_records, chat_fn)
        if llm_data is None:
            llm_failed = True
    llm_used = llm_data is not None

    risk_flags = _risk_flags(
        retrieved_examples,
        used_sample_corpus=used_sample_corpus,
        director_records=director_records,
        llm_failed=llm_failed,
    )
    recommended_directors = _director_recommendations(
        director_records or [_mock_director_record()],
        supporting_chunk_ids,
        risk_flags,
        rfp_text,
        retrieved_examples,
    )

    if llm_used:
        rfp_summary = llm_data.get("rfp_summary") or _summarize_rfp_text(rfp_text)
        effort = llm_data.get("effort") or _effort_estimate(rfp_text, retrieved_examples)
        if isinstance(effort, dict) and "reason" in effort and "rationale" not in effort:
            effort["rationale"] = effort["reason"]
        match_reasons = llm_data.get("director_match_reasons") or {}
        if match_reasons:
            _inject_llm_match_reasons(recommended_directors, match_reasons)
    else:
        rfp_summary = _summarize_rfp_text(rfp_text)
        effort = _effort_estimate(rfp_text, retrieved_examples)

    return {
        "rfp_summary": rfp_summary,
        "effort": effort,
        "similar_rfps": _similar_rfps(retrieved_examples),
        "retrieved_examples": retrieved_examples,
        "recommended_directors": recommended_directors,
        "risk_flags": risk_flags,
        "retrieval_mode": retrieval_mode,
        "retrieval_status": retrieval_status,
        "notes": _notes(
            used_sample_corpus=used_sample_corpus,
            retrieval_mode=retrieval_mode,
            retrieval_status=retrieval_status,
            llm_used=llm_used,
        ),
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


def _build_retrieval_report(
    chunks: list[dict[str, Any]],
    query: str,
    top_k: int,
) -> dict[str, Any]:
    """Choose the preferred retrieval path and fall back if anything fails."""

    try:
        report = preferred_retrieval_report(
            query_text=query,
            historical_chunks=chunks,
            top_k=top_k,
        )
        if report.get("retrieved_examples"):
            return report
    except Exception as exc:
        fallback_report = fallback_retrieval_report(
            query_text=query,
            historical_chunks=chunks,
            top_k=top_k,
        )
        fallback_report.setdefault("status", {})
        fallback_report["status"]["preferred_path_error"] = str(exc)
        return fallback_report

    return fallback_retrieval_report(
        query_text=query,
        historical_chunks=chunks,
        top_k=top_k,
    )


def _summarize_rfp_text(rfp_text: str, max_chars: int = 220) -> str:
    """Create a short heuristic summary from the RFP text.

    @param rfp_text: New RFP text from the dashboard.
    @param max_chars: Maximum number of characters to keep in the summary.
    @return: Short summary string for the dashboard.
    """

    clean_text = " ".join(str(rfp_text).split())
    if not clean_text:
        return "Short summary of the input RFP"

    service_labels = _service_labels(clean_text)
    if service_labels:
        intro = f"RFP appears to request {', '.join(service_labels)} support."
    else:
        intro = "RFP summary based on the opening request text."

    first_sentence = _first_sentence(clean_text)
    summary = f"{intro} {first_sentence}"
    if len(summary) <= max_chars:
        return summary
    return f"{summary[:max_chars].rstrip()}..."


def _director_recommendations(
    director_records: list[dict[str, Any]],
    supporting_chunks: list[str],
    risk_flags: list[dict[str, str]] | None = None,
    rfp_text: str = "",
    retrieved_examples: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Create prototype director recommendation records.

    The real capacity scoring module will own the final ranking later. For
    Week 3, this heuristic ranks the provided directors using capacity fields,
    retrieval evidence, and simple service-keyword overlap.

    @param director_records: Director capacity records as plain dictionaries.
    @param supporting_chunks: Chunk IDs supporting the prototype match.
    @param risk_flags: Risk flags that should be surfaced per recommendation.
    @param rfp_text: Input RFP text used for simple service-keyword matching.
    @param retrieved_examples: Retrieved examples used for similarity signal.
    @return: Dashboard-ready director recommendation dictionaries.
    """

    flags = [flag["message"] for flag in risk_flags or []]
    examples = retrieved_examples or []
    ranked_records = [
        _director_record(
            record=record,
            supporting_chunks=supporting_chunks,
            risk_flags=flags,
            rfp_text=rfp_text,
            retrieved_examples=examples,
        )
        for record in director_records
    ]

    return sorted(
        ranked_records,
        key=lambda record: record["assignment_score"],
        reverse=True,
    )[:3]


def _director_record(
    record: dict[str, Any],
    supporting_chunks: list[str],
    risk_flags: list[str],
    rfp_text: str,
    retrieved_examples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize and score one prototype director recommendation.

    @param record: Director/capacity row from the dashboard or fallback data.
    @param supporting_chunks: Retrieved chunk IDs used as evidence.
    @param risk_flags: Risk flag messages to surface with the recommendation.
    @param rfp_text: Input RFP text used for simple service-keyword matching.
    @param retrieved_examples: Retrieved examples used for similarity signal.
    @return: Dashboard-ready director recommendation dictionary.
    """

    capacity_score = _as_float(record.get("capacity_score"), default=0.45)
    relative_load = _as_float(record.get("relative_load"), default=1.0)
    similarity_signal = _max_similarity(retrieved_examples)
    keyword_overlap = _director_keyword_overlap(record, rfp_text)
    label_bonus = _capacity_label_bonus(record.get("capacity_label"))
    assignment_score = _as_float(
        record.get("assignment_score"),
        default=round(
            max(
                0.0,
                min(
                    1.0,
                    (capacity_score * 0.45)
                    + (similarity_signal * 0.25)
                    + (keyword_overlap * 0.15)
                    + label_bonus,
                ),
            ),
            3,
        ),
    )
    director_name = str(
        record.get(
            "director_name",
            record.get("opportunity_owner", record.get("name", "Director A")),
        )
    )
    capacity_label = str(record.get("capacity_label", "Available"))
    match_reason = str(record.get("match_reason") or _match_reason(
        capacity_label=capacity_label,
        similarity_signal=similarity_signal,
        keyword_overlap=keyword_overlap,
        supporting_chunks=supporting_chunks,
    ))

    return {
        "director_name": director_name,
        "capacity_label": capacity_label,
        "capacity_score": capacity_score,
        "relative_load": relative_load,
        "assignment_score": assignment_score,
        "match_reason": match_reason,
        "capacity_explanation": record.get(
            "capacity_explanation",
            _capacity_explanation(
                director_name=director_name,
                capacity_label=capacity_label,
                capacity_score=capacity_score,
                relative_load=relative_load,
            ),
        ),
        "experience_match_explanation": record.get(
            "experience_match_explanation",
            _experience_explanation(
                keyword_overlap=keyword_overlap,
                retrieved_examples=retrieved_examples,
            ),
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
    director_records: list[dict[str, Any]] | None = None,
    llm_failed: bool = False,
) -> list[dict[str, str]]:
    """Create simple prototype risk flags for the dashboard.

    @param retrieved_examples: Retrieved chunks from the local baseline.
    @param used_sample_corpus: Whether built-in fallback historical text was used.
    @param director_records: Director records passed into the assignment logic.
    @param llm_failed: Whether an LLM enrichment attempt was made but failed.
    @return: Risk flag dictionaries.
    """

    flags = []
    if used_sample_corpus:
        flags.append(
            {
                "level": "Medium",
                "message": (
                    "Built-in sample historical corpus was used because real "
                    "historical proposal data was unavailable. Treat retrieval "
                    "evidence as a prototype signal until the approved proposal "
                    "data is connected."
                ),
            }
        )
    if len(retrieved_examples) < 3:
        flags.append(
            {
                "level": "Medium",
                "message": (
                    "Limited historical examples found for this RFP type. The "
                    "dashboard should show this recommendation carefully until "
                    "more historical examples are indexed."
                ),
            }
        )
    if retrieved_examples and _max_similarity(retrieved_examples) < 0.2:
        flags.append(
            {
                "level": "Medium",
                "message": (
                    "Top retrieved example has low similarity to the input RFP. "
                    "The recommendation may need human review before it is used."
                ),
            }
        )
    if not director_records:
        flags.append(
            {
                "level": "Medium",
                "message": (
                    "Director capacity data was unavailable, so mock director "
                    "data was used. Replace this with real capacity output "
                    "before making staffing decisions."
                ),
            }
        )
    else:
        if any(_missing_capacity_fields(record) for record in director_records):
            flags.append(
                {
                    "level": "Medium",
                    "message": (
                        "Some director capacity fields are missing and were "
                        "filled with heuristic defaults. Confirm these fields "
                        "before trusting the ranking."
                    ),
                }
            )
        if any(_is_overextended(record) for record in director_records):
            flags.append(
                {
                    "level": "High",
                    "message": (
                        "At least one candidate director is overextended based "
                        "on capacity signals. This should be reviewed before "
                        "assignment."
                    ),
                }
            )
    if llm_failed:
        flags.append(
            {
                "level": "Low",
                "message": (
                    "Azure OpenAI chat enrichment was attempted but failed. "
                    "Heuristic RFP summary, effort estimate, and match reasons "
                    "are shown instead."
                ),
            }
        )
    return flags


def _notes(
    used_sample_corpus: bool = False,
    retrieval_mode: str = "local_fallback",
    retrieval_status: dict[str, Any] | None = None,
    llm_used: bool = False,
) -> str:
    """Create a short note describing the current prototype mode.

    @param used_sample_corpus: Whether built-in fallback historical text was used.
    @param retrieval_mode: Which retrieval path was used.
    @param retrieval_status: Status details from the retrieval backend.
    @param llm_used: Whether LLM enrichment succeeded.
    @return: Dashboard note string.
    """

    status_bits = []
    if retrieval_mode:
        status_bits.append(f"retrieval mode: {retrieval_mode}")
    if retrieval_status and retrieval_status.get("preferred_path_error"):
        status_bits.append("preferred path fell back after an error")
    if llm_used:
        base = (
            "Prototype output enriched with Azure OpenAI chat analysis. "
            "Retrieval remains local fallback."
        )
        if used_sample_corpus:
            return (
                base + " Built-in sample historical corpus used because real "
                "historical proposal data was unavailable."
            )
        return base
    if used_sample_corpus:
        return (
            "Prototype output for dashboard integration. Built-in sample "
            "historical corpus used because real historical proposal data was unavailable. "
            + ("; ".join(status_bits) + "." if status_bits else "")
        )
    if status_bits:
        return "Prototype output for dashboard integration. " + "; ".join(status_bits) + "."
    return "Prototype output for dashboard integration."


def _effort_estimate(
    rfp_text: str,
    retrieved_examples: list[dict[str, Any]],
) -> dict[str, str]:
    """Create a deterministic heuristic effort estimate for the dashboard.

    @param rfp_text: Input RFP text.
    @param retrieved_examples: Retrieved examples used as supporting signal.
    @return: Effort object with level, reason, estimated duration, and rationale.
    """

    clean_text = " ".join(str(rfp_text).split())
    word_count = len(clean_text.split())
    services = _service_labels(clean_text)
    complexity_hits = _matched_terms(clean_text, COMPLEXITY_TERMS)
    best_similarity = _max_similarity(retrieved_examples)

    # The effort score is intentionally simple for Week 3. It gives the
    # dashboard a stable prototype estimate without pretending to be final.
    effort_points = 0
    effort_points += 2 if word_count >= 800 else 1 if word_count >= 250 else 0
    effort_points += 1 if len(services) >= 2 else 0
    effort_points += 1 if len(complexity_hits) >= 2 else 0
    effort_points += 1 if best_similarity < 0.2 else 0

    if effort_points >= 3:
        level = "High"
        duration = "6-8 weeks"
    elif effort_points >= 1:
        level = "Medium"
        duration = "3-5 weeks"
    else:
        level = "Low"
        duration = "1-2 weeks"

    reason = (
        "Heuristic estimate based on RFP length "
        f"({word_count} words), service areas "
        f"({', '.join(services) if services else 'none detected'}), "
        f"complexity terms ({', '.join(complexity_hits) if complexity_hits else 'none detected'}), "
        f"and retrieved examples ({len(retrieved_examples)} matches)."
    )
    return {
        "level": level,
        "reason": reason,
        "estimated_duration": duration,
        "rationale": reason,
    }


def _similar_rfps(retrieved_examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose retrieved examples under the dashboard's similar-RFP contract.

    @param retrieved_examples: Local retrieval results from the vector store.
    @return: Similar RFP records using the dashboard field names.
    """

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
    """Return the fallback director record used when capacity data is missing.

    @return: Mock director record with the fields the dashboard expects.
    """

    return {
        "director_name": "Director A",
        "capacity_label": "Available",
        "capacity_score": 0.72,
        "relative_load": 0.65,
        "match_reason": "Relevant historical experience and available capacity",
    }


def _as_float(value: Any, default: float) -> float:
    """Convert numeric dashboard fields without failing on missing values.

    @param value: Raw value from a director record or retrieval result.
    @param default: Value to use when conversion fails.
    @return: Float value for scoring.
    """

    try:
        converted = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(converted):
        return default
    return converted


def _is_missing_value(value: Any) -> bool:
    """Return True for null-like scalar values from Python, pandas, or NumPy."""

    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped in {"", "nan", "none", "<na>", "inf", "+inf", "-inf"}:
            return True
    try:
        converted = float(value)
    except (TypeError, ValueError):
        pass
    else:
        if not math.isfinite(converted):
            return True
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return str(value).strip().lower() in {"<na>", "nan"}


def _service_labels(text: str) -> list[str]:
    """Return service labels detected in the RFP text.

    @param text: RFP text or director expertise text.
    @return: Service labels found from the keyword map.
    """

    lower_text = str(text).lower()
    labels = [
        label.replace("_", " ")
        for label, keywords in SERVICE_KEYWORDS.items()
        if any(keyword in lower_text for keyword in keywords)
    ]
    return labels


def _matched_terms(text: str, terms: set[str]) -> list[str]:
    """Return matching terms in stable alphabetical order.

    @param text: Input text to search.
    @param terms: Terms to look for.
    @return: Matching terms sorted alphabetically.
    """

    lower_text = str(text).lower()
    return sorted(term for term in terms if term in lower_text)


def _first_sentence(text: str) -> str:
    """Return the first useful sentence-like span from the RFP text.

    @param text: Cleaned RFP text.
    @return: First sentence-like span, or a short text prefix.
    """

    for separator in (". ", "\n", "? ", "! "):
        if separator in text:
            return text.split(separator, maxsplit=1)[0].strip()
    return text[:160].strip()


def _max_similarity(retrieved_examples: list[dict[str, Any]]) -> float:
    """Return the strongest retrieved similarity score, or zero if missing.

    @param retrieved_examples: Retrieved RFP chunk records.
    @return: Highest similarity score found.
    """

    scores = [
        _as_float(example.get("similarity_score"), default=0.0)
        for example in retrieved_examples
        if isinstance(example, dict)
    ]
    return max(scores, default=0.0)


def _director_keyword_overlap(record: dict[str, Any], rfp_text: str) -> float:
    """Estimate simple service fit between a director record and the RFP.

    @param record: Director record with optional expertise/service fields.
    @param rfp_text: New RFP text from the dashboard.
    @return: Fraction of RFP service labels also found in the director record.
    """

    rfp_labels = set(_service_labels(rfp_text))
    if not rfp_labels:
        return 0.0

    record_text = " ".join(
        str(record.get(field, ""))
        for field in (
            "service_domain",
            "service_domains",
            "expertise",
            "experience_keywords",
            "match_reason",
        )
    )
    director_labels = set(_service_labels(record_text))
    if not director_labels:
        return 0.0
    return len(rfp_labels & director_labels) / len(rfp_labels)


def _capacity_label_bonus(capacity_label: Any) -> float:
    """Translate capacity labels into a small scoring adjustment.

    @param capacity_label: Capacity label from the capacity engine/dashboard.
    @return: Small positive or negative score adjustment.
    """

    label = str(capacity_label or "").strip().lower()
    if label == "available":
        return 0.15
    if label == "near historical norm":
        return 0.08
    if label == "high load":
        return -0.05
    if label == "overextended":
        return -0.2
    if label == "no baseline":
        return -0.05
    return 0.0


def _match_reason(
    capacity_label: str,
    similarity_signal: float,
    keyword_overlap: float,
    supporting_chunks: list[str],
) -> str:
    """Create a short reason for the prototype director recommendation.

    @param capacity_label: Director capacity label.
    @param similarity_signal: Best retrieved similarity score.
    @param keyword_overlap: Simple service-keyword overlap score.
    @param supporting_chunks: Retrieved chunk IDs used as evidence.
    @return: Short match explanation for the dashboard.
    """

    evidence = (
        "retrieved historical examples"
        if supporting_chunks
        else "limited retrieval evidence"
    )
    return (
        f"Capacity is labelled {capacity_label}; {evidence} produced a top "
        f"similarity score of {similarity_signal:.2f}; service keyword overlap is "
        f"{keyword_overlap:.2f}."
    )


def _capacity_explanation(
    director_name: str,
    capacity_label: str,
    capacity_score: float,
    relative_load: float,
) -> str:
    """Create the capacity explanation displayed in the dashboard.

    @param director_name: Director name shown in the recommendation.
    @param capacity_label: Capacity label from the capacity engine/dashboard.
    @param capacity_score: Numeric capacity score used in assignment scoring.
    @param relative_load: Director relative load used in assignment scoring.
    @return: Plain-language capacity explanation.
    """

    return (
        f"{director_name} is labelled {capacity_label} with capacity score "
        f"{capacity_score:.2f} and relative load {relative_load:.2f}. "
        "This is a heuristic input to the assignment score, not a final staffing decision."
    )


def _experience_explanation(
    keyword_overlap: float,
    retrieved_examples: list[dict[str, Any]],
) -> str:
    """Create the experience-match explanation displayed in the dashboard.

    @param keyword_overlap: Simple service-keyword overlap score.
    @param retrieved_examples: Retrieved RFP chunk records.
    @return: Plain-language experience explanation.
    """

    if not retrieved_examples:
        return "No retrieved examples were available, so experience fit is weak."
    return (
        "Experience fit is estimated from retrieved historical/sample RFP chunks "
        f"and simple service-keyword overlap ({keyword_overlap:.2f})."
    )


def _missing_capacity_fields(record: dict[str, Any]) -> bool:
    """Check whether a director record is missing key capacity fields.

    @param record: Director record from real or mock capacity data.
    @return: True if capacity fields are missing.
    """

    required_fields = ("capacity_label", "capacity_score", "relative_load")
    return any(_is_missing_value(record.get(field)) for field in required_fields)


def _is_overextended(record: dict[str, Any]) -> bool:
    """Check whether a director record looks overextended.

    @param record: Director record from real or mock capacity data.
    @return: True if the label/load suggests the director is overextended.
    """

    label = str(record.get("capacity_label", "")).strip().lower()
    relative_load = _as_float(record.get("relative_load"), default=0.0)
    return label == "overextended" or relative_load >= 2.0


def _resolve_chat_fn(chat_fn_param: Any):
    """Return a callable chat function or None from the _chat_fn parameter.

    - None  → LLM disabled
    - _AUTO → auto-detect Azure chat availability
    - other → use directly as the chat callable
    """

    if chat_fn_param is None:
        return None
    if chat_fn_param is not _AUTO:
        return chat_fn_param
    try:
        from src.azure_client import azure_chat_available, chat_completion
    except ImportError:
        try:
            from azure_client import azure_chat_available, chat_completion  # type: ignore
        except ImportError:
            return None
    if azure_chat_available():
        return chat_completion
    return None


def _build_llm_messages(
    rfp_text: str,
    director_records: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build the chat messages list for the LLM enrichment call."""

    snippet = rfp_text[:_RFP_SNIPPET_CHARS]
    director_names = [
        str(r.get("director_name", r.get("opportunity_owner", r.get("name", "Director A"))))
        for r in director_records
    ] or ["Director A"]
    system_msg = (
        "You are an RFP analysis assistant for a consulting firm. "
        "Analyze the RFP text and return a JSON object with exactly these fields:\n"
        '  "rfp_summary": string (2-3 sentence summary of what the RFP is requesting)\n'
        '  "effort": object with "level" (one of: Low, Medium, High), '
        '"reason" (1-2 sentences explaining the estimate), '
        '"estimated_duration" (e.g. "3-5 weeks")\n'
        '  "director_match_reasons": object mapping each director name to a '
        "1-2 sentence explanation of why they may be a good fit\n"
        "Return ONLY valid JSON. Do not include markdown code fences."
    )
    user_msg = (
        f"RFP TEXT:\n{snippet}\n\n"
        f"CANDIDATE DIRECTORS: {', '.join(director_names)}\n\n"
        "Return your analysis as JSON."
    )
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def _llm_enrich(
    rfp_text: str,
    director_records: list[dict[str, Any]],
    chat_fn,
) -> dict[str, Any] | None:
    """Call the LLM and return enriched fields, or None on any failure."""

    try:
        messages = _build_llm_messages(rfp_text, director_records)
        raw = chat_fn(messages)
        if not raw or not raw.strip():
            return None
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            cleaned = "\n".join(lines[1:end])
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            return None
        normalized: dict[str, Any] = {}
        summary = data.get("rfp_summary")
        if isinstance(summary, str) and summary.strip():
            normalized["rfp_summary"] = summary.strip()
        effort = data.get("effort")
        if isinstance(effort, dict):
            normalized_effort = dict(effort)
            if normalized_effort.get("level") not in {"Low", "Medium", "High"}:
                normalized_effort["level"] = "Medium"
            normalized_effort["reason"] = str(normalized_effort.get("reason") or "")
            normalized_effort["estimated_duration"] = str(
                normalized_effort.get("estimated_duration") or ""
            )
            normalized_effort["rationale"] = normalized_effort["reason"]
            normalized["effort"] = normalized_effort
        match_reasons = data.get("director_match_reasons")
        if isinstance(match_reasons, dict):
            normalized["director_match_reasons"] = {
                str(name): str(reason)
                for name, reason in match_reasons.items()
                if reason
            }
        if not normalized:
            return None
        return normalized
    except Exception:
        return None


def _inject_llm_match_reasons(
    recommended_directors: list[dict[str, Any]],
    match_reasons: dict[str, str],
) -> None:
    """Overwrite heuristic match_reason values with LLM-generated ones in place."""

    for director in recommended_directors:
        name = director.get("director_name", "")
        if name in match_reasons and match_reasons[name]:
            director["match_reason"] = str(match_reasons[name])

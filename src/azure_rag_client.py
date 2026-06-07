"""Azure and fallback RFP retrieval helpers for the Week 4 prototype."""

from __future__ import annotations

import math
import os
import time
from typing import Any

from src.azure_embedding_client import embedding_ready
from src.rfp_preprocessor import load_sample_rfp_text, prepare_rfp_chunks
from src.vector_store import (
    build_chroma_from_chunks,
    build_retrieval_context,
    build_vector_store,
    get_vector_store_status,
    query_chroma,
    retrieve_examples_from_query_chunks,
)

def _historical_sample_chunks() -> list[dict[str, Any]]:
    chunks = prepare_rfp_chunks(load_sample_rfp_text())
    for chunk in chunks:
        chunk["proposal_id"] = "historical_sample"
        chunk["chunk_id"] = f"historical_sample_chunk_{int(chunk['chunk_index']) + 1:03d}"
        chunk["source_type"] = "historical_sample"
    return chunks


def fallback_retrieval_report(
    query_text: str,
    historical_chunks: list[dict[str, Any]] | None = None,
    top_k: int = 3,
    query_chunks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    total_start = time.perf_counter()
    timings: dict[str, float] = {}
    chunks = historical_chunks if historical_chunks is not None else _historical_sample_chunks()

    start = time.perf_counter()
    retrieved_examples = retrieve_examples_from_query_chunks(
        chunks,
        query_text,
        query_chunks=query_chunks,
        top_k=top_k,
    )
    timings["local_retrieval_query_seconds"] = round(time.perf_counter() - start, 4)

    start = time.perf_counter()
    store = build_vector_store(chunks)
    retrieval_context = build_retrieval_context(
        store.query(_first_query_text(query_text, query_chunks), top_k=top_k)
    )
    timings["local_retrieval_context_seconds"] = round(time.perf_counter() - start, 4)
    status = get_vector_store_status()
    status["query_chunk_count"] = _query_chunk_count(query_text, query_chunks)
    timings["fallback_retrieval_total_seconds"] = round(time.perf_counter() - total_start, 4)
    status["timings"] = timings
    return {
        "backend": "fallback",
        "retrieval_mode": "local_fallback",
        "status": status,
        "retrieved_examples": retrieved_examples,
        "retrieval_context": retrieval_context,
    }


def preferred_retrieval_report(
    query_text: str,
    historical_chunks: list[dict[str, Any]] | None = None,
    top_k: int = 3,
    persist_directory: str = "data/vector_store",
    collection_name: str = "rfp_chunks",
    query_chunks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not embedding_ready():
        return _fallback_with_preferred_status(
            query_text,
            historical_chunks=historical_chunks,
            top_k=top_k,
            query_chunks=query_chunks,
            fallback_reason=(
                "Azure embedding configuration is unavailable; local fallback used."
            ),
        )

    total_start = time.perf_counter()
    timings: dict[str, float] = {}
    chunks = historical_chunks if historical_chunks is not None else _historical_sample_chunks()
    rebuild_requested = _rebuild_chroma_requested()

    try:
        if rebuild_requested:
            start = time.perf_counter()
            build_chroma_from_chunks(
                chunks,
                persist_directory=persist_directory,
                collection_name=collection_name,
                reset_collection=True,
            )
            timings["chroma_build_seconds"] = round(time.perf_counter() - start, 4)

        start = time.perf_counter()
        retrieved_examples = _query_chroma_with_chunks(
            query_text,
            query_chunks=query_chunks,
            persist_directory=persist_directory,
            collection_name=collection_name,
            top_k=top_k,
            require_existing_collection=not rebuild_requested,
        )
        timings[
            "chroma_query_after_rebuild_seconds"
            if rebuild_requested
            else "chroma_reuse_query_seconds"
        ] = round(time.perf_counter() - start, 4)
        if not retrieved_examples:
            raise ValueError(
                f"Reusable Chroma collection returned no results: {collection_name}"
            )

        start = time.perf_counter()
        store = build_vector_store(chunks)
        retrieval_context = build_retrieval_context(
            store.query(_first_query_text(query_text, query_chunks), top_k=top_k)
        )
        timings["local_retrieval_context_seconds"] = round(time.perf_counter() - start, 4)
        status = get_vector_store_status()
        status["preferred_path_ready"] = True
        status["chroma_reused"] = not rebuild_requested
        status["chroma_rebuild_requested"] = rebuild_requested
        status["query_chunk_count"] = _query_chunk_count(query_text, query_chunks)
        timings["preferred_retrieval_total_seconds"] = round(time.perf_counter() - total_start, 4)
        status["timings"] = timings
        return {
            "backend": "azure_chroma",
            "retrieval_mode": "azure_chroma",
            "status": status,
            "retrieved_examples": retrieved_examples,
            "retrieval_context": retrieval_context,
        }
    except Exception as exc:
        fallback_report = _fallback_with_preferred_status(
            query_text,
            historical_chunks=chunks,
            top_k=top_k,
            query_chunks=query_chunks,
            fallback_reason=(
                "Chroma reuse failed; local fallback used."
                if not rebuild_requested
                else "Chroma rebuild/query failed; local fallback used."
            ),
            preferred_path_error=str(exc),
        )
        fallback_report["status"].setdefault("timings", {}).update(
            {
                **timings,
                "chroma_rebuild_requested": rebuild_requested,
                "preferred_retrieval_failed_after_seconds": round(
                    time.perf_counter() - total_start,
                    4,
                ),
            }
        )
        return fallback_report


def _fallback_with_preferred_status(
    query_text: str,
    *,
    historical_chunks: list[dict[str, Any]] | None = None,
    top_k: int = 3,
    query_chunks: list[dict[str, Any]] | None = None,
    fallback_reason: str,
    preferred_path_error: str | None = None,
) -> dict[str, Any]:
    report = fallback_retrieval_report(
        query_text,
        historical_chunks=historical_chunks,
        top_k=top_k,
        query_chunks=query_chunks,
    )
    report["backend"] = "fallback"
    report["retrieval_mode"] = "local_fallback"
    report.setdefault("status", {})
    report["status"]["preferred_path_fallback_reason"] = fallback_reason
    report["status"]["chroma_rebuild_requested"] = _rebuild_chroma_requested()
    if preferred_path_error:
        report["status"]["preferred_path_error"] = preferred_path_error
    return report


def _rebuild_chroma_requested() -> bool:
    return str(os.getenv("RFP_REBUILD_CHROMA", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _query_chroma_with_chunks(
    query_text: str,
    *,
    query_chunks: list[dict[str, Any]] | None = None,
    persist_directory: str,
    collection_name: str,
    top_k: int,
    require_existing_collection: bool = False,
) -> list[dict[str, Any]]:
    best_by_chunk_id: dict[str, dict[str, Any]] = {}
    for query in _query_texts(query_text, query_chunks):
        for example in query_chroma(
            query,
            persist_directory=persist_directory,
            collection_name=collection_name,
            top_k=top_k,
            require_existing_collection=require_existing_collection,
        ):
            chunk_id = str(example.get("chunk_id") or "")
            if not chunk_id:
                continue
            previous = best_by_chunk_id.get(chunk_id)
            if previous is None or _similarity_value(example) > _similarity_value(previous):
                best_by_chunk_id[chunk_id] = example

    return sorted(
        best_by_chunk_id.values(),
        key=lambda example: (_similarity_value(example), str(example.get("chunk_id") or "")),
        reverse=True,
    )[:top_k]


def _query_texts(
    query_text: str,
    query_chunks: list[dict[str, Any]] | None = None,
) -> list[str]:
    texts = [
        str(chunk.get("text") or "").strip()
        for chunk in query_chunks or []
        if isinstance(chunk, dict) and str(chunk.get("text") or "").strip()
    ]
    if texts:
        return texts
    return [str(query_text or "").strip()] if str(query_text or "").strip() else []


def _first_query_text(
    query_text: str,
    query_chunks: list[dict[str, Any]] | None = None,
) -> str:
    texts = _query_texts(query_text, query_chunks)
    return texts[0] if texts else ""


def _query_chunk_count(
    query_text: str,
    query_chunks: list[dict[str, Any]] | None = None,
) -> int:
    return len(_query_texts(query_text, query_chunks))


def _similarity_value(example: dict[str, Any]) -> float:
    try:
        value = float(example.get("similarity_score"))
    except (TypeError, ValueError, OverflowError):
        return float("-inf")
    return value if math.isfinite(value) else float("-inf")

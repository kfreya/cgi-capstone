"""Azure and fallback RFP retrieval helpers for the Week 4 prototype."""

from __future__ import annotations

import math
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
    chunks = historical_chunks if historical_chunks is not None else _historical_sample_chunks()
    retrieved_examples = retrieve_examples_from_query_chunks(
        chunks,
        query_text,
        query_chunks=query_chunks,
        top_k=top_k,
    )
    store = build_vector_store(chunks)
    retrieval_context = build_retrieval_context(
        store.query(_first_query_text(query_text, query_chunks), top_k=top_k)
    )
    status = get_vector_store_status()
    status["query_chunk_count"] = _query_chunk_count(query_text, query_chunks)
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
        return fallback_retrieval_report(
            query_text,
            historical_chunks=historical_chunks,
            top_k=top_k,
            query_chunks=query_chunks,
        )

    chunks = historical_chunks if historical_chunks is not None else _historical_sample_chunks()

    try:
        build_chroma_from_chunks(
            chunks,
            persist_directory=persist_directory,
            collection_name=collection_name,
            reset_collection=True,
        )
        retrieved_examples = _query_chroma_with_chunks(
            query_text,
            query_chunks=query_chunks,
            persist_directory=persist_directory,
            collection_name=collection_name,
            top_k=top_k,
        )
        store = build_vector_store(chunks)
        retrieval_context = build_retrieval_context(
            store.query(_first_query_text(query_text, query_chunks), top_k=top_k)
        )
        status = get_vector_store_status()
        status["preferred_path_ready"] = True
        status["query_chunk_count"] = _query_chunk_count(query_text, query_chunks)
        return {
            "backend": "azure_chroma",
            "retrieval_mode": "azure_chroma",
            "status": status,
            "retrieved_examples": retrieved_examples,
            "retrieval_context": retrieval_context,
        }
    except Exception as exc:
        fallback_report = fallback_retrieval_report(
            query_text,
            historical_chunks=chunks,
            top_k=top_k,
            query_chunks=query_chunks,
        )
        fallback_report["backend"] = "fallback"
        fallback_report["retrieval_mode"] = "local_fallback"
        fallback_report.setdefault("status", {})
        fallback_report["status"]["preferred_path_error"] = str(exc)
        return fallback_report


def _query_chroma_with_chunks(
    query_text: str,
    *,
    query_chunks: list[dict[str, Any]] | None = None,
    persist_directory: str,
    collection_name: str,
    top_k: int,
) -> list[dict[str, Any]]:
    best_by_chunk_id: dict[str, dict[str, Any]] = {}
    for query in _query_texts(query_text, query_chunks):
        for example in query_chroma(
            query,
            persist_directory=persist_directory,
            collection_name=collection_name,
            top_k=top_k,
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

"""Azure and fallback RFP retrieval helpers for the Week 4 prototype."""

from __future__ import annotations

from typing import Any

from src.azure_embedding_client import embedding_ready, smoke_test_embedding
from src.rfp_preprocessor import load_sample_rfp_text, prepare_rfp_chunks
from src.vector_store import (
    build_chroma_from_chunks,
    build_retrieval_context,
    build_vector_store,
    get_vector_store_status,
    query_chroma,
    retrieve_examples_from_chunks,
)


def _historical_sample_chunks() -> list[dict[str, Any]]:
    chunks = prepare_rfp_chunks(load_sample_rfp_text())
    for chunk in chunks:
        chunk["proposal_id"] = "historical_sample"
        chunk["chunk_id"] = f"historical_sample_chunk_{int(chunk['chunk_index']) + 1:03d}"
        chunk["source_type"] = "historical_sample"
    return chunks


def fallback_retrieval_report(query_text: str, historical_chunks: list[dict[str, Any]] | None = None, top_k: int = 3) -> dict[str, Any]:
    chunks = historical_chunks if historical_chunks is not None else _historical_sample_chunks()
    retrieved_examples = retrieve_examples_from_chunks(chunks, query_text, top_k=top_k)
    store = build_vector_store(chunks)
    retrieval_context = build_retrieval_context(store.query(query_text, top_k=top_k))
    return {
        "backend": "fallback",
        "retrieval_mode": "local_fallback",
        "status": get_vector_store_status(),
        "retrieved_examples": retrieved_examples,
        "retrieval_context": retrieval_context,
    }


def preferred_retrieval_report(
    query_text: str,
    historical_chunks: list[dict[str, Any]] | None = None,
    top_k: int = 3,
    persist_directory: str = "data/vector_store",
    collection_name: str = "rfp_chunks",
) -> dict[str, Any]:
    if not embedding_ready():
        return fallback_retrieval_report(query_text, historical_chunks=historical_chunks, top_k=top_k)

    chunks = historical_chunks if historical_chunks is not None else _historical_sample_chunks()
    try:
        build_chroma_from_chunks(
            chunks,
            persist_directory=persist_directory,
            collection_name=collection_name,
            reset_collection=True,
        )
        retrieved_examples = query_chroma(
            query_text,
            persist_directory=persist_directory,
            collection_name=collection_name,
            top_k=top_k,
        )
        store = build_vector_store(chunks)
        retrieval_context = build_retrieval_context(store.query(query_text, top_k=top_k))
        return {
            "backend": "azure_chroma",
            "retrieval_mode": "azure_chroma",
            "status": smoke_test_embedding(),
            "retrieved_examples": retrieved_examples,
            "retrieval_context": retrieval_context,
        }
    except Exception as exc:
        fallback_report = fallback_retrieval_report(
            query_text,
            historical_chunks=chunks,
            top_k=top_k,
        )
        fallback_report["backend"] = "fallback"
        fallback_report["retrieval_mode"] = "local_fallback"
        fallback_report.setdefault("status", {})
        fallback_report["status"]["preferred_path_error"] = str(exc)
        return fallback_report

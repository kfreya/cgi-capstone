"""Azure embedding compatibility helpers for the Week 4 prototype."""

from __future__ import annotations

from typing import Any

from src.azure_client import (
    azure_embedding_available,
    embed_texts,
    get_azure_environment_status,
    get_azure_embeddings_client,
    get_embedding_function,
    missing_azure_config,
    try_validate_azure_config,
    validate_azure_config,
)


def embedding_ready() -> bool:
    return azure_embedding_available()


def embedding_status() -> dict[str, Any]:
    return get_azure_environment_status(require_embedding=True)


def embedding_missing_keys() -> list[str]:
    return missing_azure_config(require_embedding=True)


def embedding_client():
    return get_azure_embeddings_client()


def embedding_callable(prefer_azure: bool = True):
    return get_embedding_function(prefer_azure=prefer_azure)


def smoke_test_embedding(sample_text: str = "This is a minimal Azure embedding smoke test.") -> dict[str, Any]:
    status = embedding_status()
    if not status["ready"]:
        return {
            "status": "blocked",
            "missing": status["missing"],
            "vector_count": 0,
            "dimension": 0,
        }
    vectors = embed_texts([sample_text])
    return {
        "status": "ok",
        "missing": [],
        "vector_count": len(vectors),
        "dimension": len(vectors[0]) if vectors else 0,
    }

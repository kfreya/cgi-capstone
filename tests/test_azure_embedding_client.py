"""Tests for Azure embedding compatibility helpers."""

from types import SimpleNamespace

from src import azure_embedding_client


def test_embedding_status_reports_blocked_when_env_missing(monkeypatch):
    monkeypatch.setattr(
        azure_embedding_client,
        "embedding_status",
        lambda: {
            "ready": False,
            "require_embedding": True,
            "missing": [
                "AZURE_OPENAI_API_VERSION",
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
            ],
            "can_create_client": False,
            "can_embed": False,
        },
    )

    result = azure_embedding_client.smoke_test_embedding()

    assert result["status"] == "blocked"
    assert result["vector_count"] == 0
    assert result["dimension"] == 0


def test_smoke_test_embedding_returns_vector_shape(monkeypatch):
    monkeypatch.setattr(
        azure_embedding_client,
        "embedding_status",
        lambda: {
            "ready": True,
            "require_embedding": True,
            "missing": [],
            "can_create_client": True,
            "can_embed": True,
        },
    )
    monkeypatch.setattr(
        azure_embedding_client,
        "embed_texts",
        lambda texts: [[0.1, 0.2, 0.3] for _ in texts],
    )

    result = azure_embedding_client.smoke_test_embedding("hello")

    assert result["status"] == "ok"
    assert result["vector_count"] == 1
    assert result["dimension"] == 3

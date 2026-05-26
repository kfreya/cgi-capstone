"""Tests for Azure and fallback RFP retrieval helpers."""

from src import azure_rag_client


def test_fallback_retrieval_report_returns_dashboard_shape():
    result = azure_rag_client.fallback_retrieval_report(
        "Need Azure migration and dashboard support.",
        historical_chunks=[
            {
                "proposal_id": "historical_sample",
                "chunk_id": "historical_sample_chunk_001",
                "source_type": "proposal",
                "text": "Prior Azure migration proposal with dashboard reporting.",
                "chunk_index": 0,
                "opportunity_owner": None,
                "opportunity_id": None,
            }
        ],
        top_k=1,
    )

    assert result["backend"] == "fallback"
    assert "local_store_ready" in result["status"]
    assert result["retrieved_examples"][0]["chunk_id"] == "historical_sample_chunk_001"
    assert "Azure migration proposal" in result["retrieval_context"]


def test_preferred_retrieval_report_falls_back_when_azure_unavailable(monkeypatch):
    monkeypatch.setattr(azure_rag_client, "embedding_ready", lambda: False)
    monkeypatch.setattr(
        azure_rag_client,
        "fallback_retrieval_report",
        lambda query_text, historical_chunks=None, top_k=3: {
            "backend": "fallback",
            "status": {"local_store_ready": True},
            "retrieved_examples": [{"chunk_id": "chunk_1"}],
            "retrieval_context": "fallback-context",
        },
    )

    result = azure_rag_client.preferred_retrieval_report("Need Azure security")

    assert result["backend"] == "fallback"
    assert result["retrieval_context"] == "fallback-context"


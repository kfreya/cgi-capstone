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
        lambda query_text, historical_chunks=None, top_k=3, query_chunks=None: {
            "backend": "fallback",
            "status": {"local_store_ready": True},
            "retrieved_examples": [{"chunk_id": "chunk_1"}],
            "retrieval_context": "fallback-context",
        },
    )

    result = azure_rag_client.preferred_retrieval_report("Need Azure security")

    assert result["backend"] == "fallback"
    assert result["retrieval_context"] == "fallback-context"


def test_preferred_retrieval_report_uses_azure_chroma_path(monkeypatch):
    monkeypatch.setattr(azure_rag_client, "embedding_ready", lambda: True)
    build_call = {}
    monkeypatch.setattr(
        azure_rag_client,
        "build_chroma_from_chunks",
        lambda *args, **kwargs: build_call.update(kwargs) or object(),
    )
    monkeypatch.setattr(
        azure_rag_client,
        "query_chroma",
        lambda *args, **kwargs: [
            {
                "proposal_id": "historical_sample",
                "chunk_id": "historical_sample_chunk_001",
                "source_type": "proposal",
                "supporting_text": "Prior Azure migration and dashboard reporting proposal.",
                "similarity_score": 0.91,
            }
        ],
    )

    class FakeResult:
        def to_retrieved_example(self):
            return {
                "proposal_id": "historical_sample",
                "chunk_id": "historical_sample_chunk_001",
                "source_type": "proposal",
                "supporting_text": "Prior Azure migration and dashboard reporting proposal.",
                "similarity_score": 0.91,
            }

    class FakeStore:
        def query(self, *_args, **_kwargs):
            return [FakeResult()]

    monkeypatch.setattr(azure_rag_client, "build_vector_store", lambda chunks: FakeStore())
    monkeypatch.setattr(azure_rag_client, "build_retrieval_context", lambda results: "azure-context")
    monkeypatch.setattr(azure_rag_client, "get_vector_store_status", lambda: {"local_store_ready": True})

    result = azure_rag_client.preferred_retrieval_report(
        "Need Azure migration and dashboard support.",
        historical_chunks=[
            {
                "proposal_id": "historical_sample",
                "chunk_id": "historical_sample_chunk_001",
                "source_type": "proposal",
                "text": "Prior Azure migration and dashboard reporting proposal.",
                "chunk_index": 0,
                "opportunity_owner": None,
                "opportunity_id": None,
            }
        ],
        top_k=1,
    )

    assert result["backend"] == "azure_chroma"
    assert result["retrieval_mode"] == "azure_chroma"
    assert result["status"]["preferred_path_ready"] is True
    assert result["retrieved_examples"][0]["chunk_id"] == "historical_sample_chunk_001"
    assert result["retrieval_context"] == "azure-context"
    assert build_call["reset_collection"] is True


def test_preferred_retrieval_report_rebuilds_large_corpus(monkeypatch):
    monkeypatch.setattr(azure_rag_client, "embedding_ready", lambda: True)
    build_call = {}
    monkeypatch.setattr(
        azure_rag_client,
        "build_chroma_from_chunks",
        lambda *args, **kwargs: build_call.update(kwargs) or object(),
    )
    monkeypatch.setattr(
        azure_rag_client,
        "query_chroma",
        lambda *args, **kwargs: [
            {
                "proposal_id": "historical_large",
                "chunk_id": "historical_large_chunk_001",
                "source_type": "proposal",
                "supporting_text": "Azure migration dashboard support.",
                "similarity_score": 0.84,
            }
        ],
    )

    class FakeResult:
        def to_retrieved_example(self):
            return {
                "proposal_id": "historical_large",
                "chunk_id": "historical_large_chunk_001",
                "source_type": "proposal",
                "supporting_text": "Azure migration dashboard support.",
                "similarity_score": 0.84,
            }

    class FakeStore:
        def query(self, *_args, **_kwargs):
            return [FakeResult()]

    monkeypatch.setattr(azure_rag_client, "build_vector_store", lambda chunks: FakeStore())
    monkeypatch.setattr(azure_rag_client, "build_retrieval_context", lambda results: "azure-context")
    monkeypatch.setattr(azure_rag_client, "get_vector_store_status", lambda: {"local_store_ready": True})

    chunks = [
        {
            "proposal_id": "historical_large",
            "chunk_id": f"historical_large_chunk_{index:03d}",
            "source_type": "proposal",
            "text": "Azure migration dashboard support.",
            "chunk_index": index,
            "opportunity_owner": None,
            "opportunity_id": None,
        }
        for index in range(1216)
    ]

    result = azure_rag_client.preferred_retrieval_report(
        "Need Azure migration support.",
        historical_chunks=chunks,
        top_k=1,
    )

    assert result["backend"] == "azure_chroma"
    assert result["retrieval_mode"] == "azure_chroma"
    assert result["status"]["preferred_path_ready"] is True
    assert result["retrieved_examples"][0]["chunk_id"] == "historical_large_chunk_001"
    assert result["retrieval_context"] == "azure-context"
    assert build_call["reset_collection"] is True


def test_fallback_retrieval_report_searches_query_chunks():
    chunks = [
        {
            "proposal_id": "historical_cloud",
            "chunk_id": "historical_cloud_chunk_001",
            "source_type": "proposal",
            "text": "Azure migration and cloud infrastructure support.",
            "chunk_index": 0,
            "opportunity_owner": None,
            "opportunity_id": None,
        },
        {
            "proposal_id": "historical_security",
            "chunk_id": "historical_security_chunk_001",
            "source_type": "proposal",
            "text": "Cybersecurity privacy compliance and risk review.",
            "chunk_index": 1,
            "opportunity_owner": None,
            "opportunity_id": None,
        },
    ]

    result = azure_rag_client.fallback_retrieval_report(
        "Need Azure migration plus privacy risk review.",
        historical_chunks=chunks,
        query_chunks=[
            {"text": "Azure migration and cloud infrastructure."},
            {"text": "Cybersecurity privacy risk review."},
        ],
        top_k=2,
    )

    chunk_ids = {example["chunk_id"] for example in result["retrieved_examples"]}
    assert "historical_cloud_chunk_001" in chunk_ids
    assert "historical_security_chunk_001" in chunk_ids
    assert result["status"]["query_chunk_count"] == 2

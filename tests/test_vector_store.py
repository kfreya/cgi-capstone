"""Tests for local vector retrieval utilities used by the RFP workflow.

The production pipeline will use Azure embeddings and Chroma persistence. These
tests use a tiny fake embedding function so the retrieval behavior can be tested
without API access or sensitive project data.

Run tests from the repository root so imports resolve consistently. For example:
`python -m pytest tests/test_vector_store.py`.
"""

import pytest

from src.rfp_preprocessor import RFPChunk
from src.vector_store import (
    InMemoryVectorStore,
    build_vector_store,
    build_dashboard_payload,
    build_retrieval_context,
    cosine_similarity,
    retrieve_relevant_chunks,
)


def fake_embedding(texts):
    """Create simple keyword embeddings for deterministic tests.

    @param texts: Text strings to embed.
    @return: Keyword indicator vectors for each input text.
    """

    vocabulary = ["azure", "dashboard", "security", "forecasting"]
    return [
        [float(term in text.lower()) for term in vocabulary]
        for text in texts
    ]


def make_chunk(chunk_id, title, text):
    """Build a small RFP chunk for vector-store tests.

    @param chunk_id: ID to assign to the test chunk.
    @param title: RFP title to attach to the chunk.
    @param text: Chunk text used for fake embedding.
    @return: RFPChunk with minimal metadata.
    """

    return RFPChunk(
        chunk_id=chunk_id,
        document_id=f"{chunk_id}_doc",
        title=title,
        section="proposal",
        chunk_index=0,
        text=text,
        metadata={"source_type": "proposal"},
    )


def make_dashboard_chunk(chunk_id, text):
    """Build the flat chunk shape used by the Week 2 dashboard API.

    @param chunk_id: ID to assign to the test chunk.
    @param text: Chunk text used for fake embedding.
    @return: Flat dictionary matching `prepare_rfp_chunks()`.
    """

    return {
        "proposal_id": "proposal_001",
        "chunk_id": chunk_id,
        "source_type": "proposal",
        "text": text,
        "chunk_index": 0,
        "opportunity_owner": None,
        "opportunity_id": None,
    }


def test_cosine_similarity_prefers_matching_vectors():
    """Check that cosine similarity is higher for matching directions."""

    assert cosine_similarity([1, 0], [0, 1]) == 0.0
    assert cosine_similarity([1, 0], [1, 0]) == 1.0


def test_cosine_similarity_validates_vector_lengths():
    """Check that mismatched vector dimensions raise a clear error."""

    with pytest.raises(ValueError, match="same length"):
        cosine_similarity([1, 0], [1, 0, 1])


def test_in_memory_store_returns_ranked_results():
    """Check that the most relevant historical chunk is ranked first."""

    chunks = [
        make_chunk("chunk_1", "Cloud", "Azure migration and security"),
        make_chunk("chunk_2", "Dashboard", "Executive dashboard reporting"),
    ]
    store = InMemoryVectorStore(fake_embedding)
    store.add_chunks(chunks)

    results = store.query("Need an Azure security proposal", top_k=1)

    # The query mentions Azure/security, so it should match the cloud chunk.
    assert results[0].chunk.chunk_id == "chunk_1"
    assert len(store) == 2


def test_in_memory_store_validates_embedding_dimensions():
    """Check that inconsistent embedding dimensions are rejected."""

    def bad_embedding(texts):
        return [[1.0], [1.0, 0.0]][: len(texts)]

    store = InMemoryVectorStore(bad_embedding)

    with pytest.raises(ValueError, match="same length"):
        store.add_chunks(
            [
                make_chunk("chunk_1", "One", "first"),
                make_chunk("chunk_2", "Two", "second"),
            ]
        )


def test_build_retrieval_context_formats_citations():
    """Check that retrieved chunks can be formatted for RAG context."""

    store = InMemoryVectorStore(fake_embedding)
    store.add_chunks([make_chunk("chunk_1", "Cloud", "Azure security")])

    context = build_retrieval_context(store.query("azure", top_k=1))

    assert "[1] Cloud | proposal" in context
    assert "Azure security" in context


def test_build_dashboard_payload_has_stable_output_shape():
    """Check the payload shape expected by downstream dashboard work."""

    store = InMemoryVectorStore(fake_embedding)
    store.add_chunks([make_chunk("chunk_1", "Cloud", "Azure security")])
    results = store.query("azure", top_k=1)

    payload = build_dashboard_payload(
        query_text="Need Azure delivery support",
        results=results,
        rfp_summary="Azure support request",
        recommended_directors=[
            {
                "director_name": "TBD",
                "match_reason": "mock",
                "capacity_label": "Available",
                "capacity_score": 0.72,
                "relative_load": 0.65,
            }
        ],
        risk_flags=[
            {
                "level": "Medium",
                "message": "Limited historical examples found for this RFP type.",
            }
        ],
    )

    assert set(payload) == {
        "rfp_summary",
        "effort",
        "similar_rfps",
        "retrieved_examples",
        "recommended_directors",
        "risk_flags",
        "notes",
    }
    assert payload["rfp_summary"] == "Azure support request"
    assert payload["effort"]["level"] in {"Low", "Medium", "High"}
    assert payload["similar_rfps"][0]["source"] == "chunk_1"
    assert payload["retrieved_examples"][0]["chunk_id"] == "chunk_1"
    assert "similarity_score" in payload["retrieved_examples"][0]
    assert payload["retrieved_examples"][0]["supporting_text"] == "Azure security"
    assert payload["recommended_directors"][0]["director_name"] == "TBD"
    assert payload["recommended_directors"][0]["match_reason"] == "mock"
    assert payload["recommended_directors"][0]["capacity_label"] == "Available"
    assert payload["recommended_directors"][0]["capacity_score"] == 0.72
    assert payload["recommended_directors"][0]["relative_load"] == 0.65
    assert "assignment_score" in payload["recommended_directors"][0]
    assert "capacity_explanation" in payload["recommended_directors"][0]
    assert "experience_match_explanation" in payload["recommended_directors"][0]
    assert payload["recommended_directors"][0]["supporting_chunks"] == [
        "chunk_1"
    ]
    assert payload["risk_flags"][0]["level"] == "Medium"
    assert payload["notes"] == "Prototype output for dashboard integration."


def test_build_and_retrieve_vector_store_match_dashboard_interface():
    """Check Freya's expected vector-store wrapper functions."""

    chunks = [
        make_dashboard_chunk("proposal_001_chunk_001", "Azure migration and security"),
        make_dashboard_chunk("proposal_001_chunk_002", "Executive dashboard reporting"),
    ]

    build_vector_store(chunks)
    results = retrieve_relevant_chunks("Need Azure security", top_k=1)

    assert results[0]["proposal_id"] == "proposal_001"
    assert results[0]["chunk_id"] == "proposal_001_chunk_001"
    assert "similarity_score" in results[0]
    assert results[0]["supporting_text"] == "Azure migration and security"

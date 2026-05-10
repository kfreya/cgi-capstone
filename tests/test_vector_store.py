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
    build_dashboard_payload,
    build_retrieval_context,
    cosine_similarity,
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
        recommended_directors=[{"name": "TBD", "reason": "mock"}],
    )

    assert payload["rfp_summary"] == "Azure support request"
    assert payload["supporting_chunks"][0]["chunk_id"] == "chunk_1"
    assert payload["recommended_directors"][0]["name"] == "TBD"

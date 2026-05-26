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
    assert payload["effort"]["reason"]
    assert payload["effort"]["rationale"] == payload["effort"]["reason"]
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


def test_optional_chroma_helpers_do_not_require_azure_credentials(tmp_path):
    """If Chroma helper APIs exist, they should be testable with a fake embedder."""

    build_chroma_from_chunks = getattr(
        __import__("src.vector_store", fromlist=["build_chroma_from_chunks"]),
        "build_chroma_from_chunks",
        None,
    )
    query_chroma = getattr(
        __import__("src.vector_store", fromlist=["query_chroma"]),
        "query_chroma",
        None,
    )
    if build_chroma_from_chunks is None or query_chroma is None:
        pytest.skip("Chroma helper APIs not present in src.vector_store")

    # If chromadb is not installed in this environment, the helpers should raise ImportError.
    try:
        import chromadb  # noqa: F401
    except ImportError:
        with pytest.raises(ImportError):
            build_chroma_from_chunks(
                [make_dashboard_chunk("proposal_001_chunk_001", "Azure migration and security")],
                persist_directory=str(tmp_path),
                collection_name="rfp_chunks_test",
                embedding_function=lambda texts: [[0.0, 1.0, 2.0] for _ in texts],
            )
        return

    # When chromadb is available, helpers should work with a fake embedder (no Azure calls).
    chunks = [
        make_dashboard_chunk("proposal_001_chunk_001", "Azure migration and security"),
        make_dashboard_chunk("proposal_001_chunk_002", "Executive dashboard reporting"),
    ]

    build_chroma_from_chunks(
        chunks,
        persist_directory=str(tmp_path),
        collection_name="rfp_chunks_test",
        embedding_function=lambda texts: [[0.0, 1.0, 2.0] for _ in texts],
    )
    results = query_chroma(
        "Need Azure security",
        persist_directory=str(tmp_path),
        collection_name="rfp_chunks_test",
        top_k=1,
        embedding_function=lambda texts: [[0.0, 1.0, 2.0]],
    )
    assert isinstance(results, list)
    if results:
        assert set(results[0]).issuperset(
            {"proposal_id", "chunk_id", "similarity_score", "supporting_text"}
        )


def test_chunk_from_dict_accepts_week3_flat_contract_shape():
    """Week 3 chunk contract should accept Kian's validated sample shape."""

    from src.vector_store import build_vector_store

    flat_chunk = {
        "chunk_id": "p1__proposal__chunk_0000",
        "document_id": "p1__proposal",
        "proposal_id": "p1",
        "title": "p1",
        "source_type": "proposal",
        "section": "proposal",
        "chunk_index": 0,
        "text": "Need cloud migration and analytics support.",
        "opportunity_owner": None,
        "opportunity_id": None,
    }

    store = build_vector_store([flat_chunk])
    results = store.query("cloud migration", top_k=1)
    assert isinstance(results, list)
    assert len(results) == 1


def test_build_vector_store_defaults_partial_chunk_identifiers():
    """Partial chunk dictionaries should still be indexable when text exists."""

    store = build_vector_store(
        [
            {
                "proposal_id": "historical_partial",
                "source_type": "proposal",
                "text": "Azure migration and dashboard support",
            }
        ]
    )

    results = store.query("Azure dashboard", top_k=1)

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "historical_partial_chunk_000"
    assert results[0].chunk.chunk_index == 0
    assert results[0].chunk.metadata["proposal_id"] == "historical_partial"


def test_build_vector_store_skips_empty_text_chunks():
    """Empty chunk text should not be indexed as supporting evidence."""

    store = build_vector_store(
        [
            {
                "proposal_id": "empty",
                "chunk_id": "empty_chunk_001",
                "chunk_index": 0,
                "text": "",
            },
            {
                "proposal_id": "blank",
                "chunk_id": "blank_chunk_001",
                "chunk_index": 1,
            },
            make_dashboard_chunk("valid_chunk_001", "Azure migration support"),
        ]
    )

    results = store.query("Azure migration", top_k=5)

    assert len(store) == 1
    assert [result.chunk.chunk_id for result in results] == ["valid_chunk_001"]


def test_get_vector_store_status_reflects_local_store_state():
    from src.vector_store import get_vector_store_status

    status_before = get_vector_store_status()
    assert "local_store_ready" in status_before

    build_vector_store([make_dashboard_chunk("proposal_001_chunk_001", "Azure support")])
    status_after = get_vector_store_status()

    assert status_after["local_store_ready"] is True
    assert status_after["local_store_size"] >= 1


def test_retrieve_examples_from_chunks_returns_dashboard_shape():
    from src.vector_store import retrieve_examples_from_chunks

    chunks = [
        make_dashboard_chunk("proposal_001_chunk_001", "Azure migration and security"),
        make_dashboard_chunk("proposal_001_chunk_002", "Executive dashboard reporting"),
    ]

    results = retrieve_examples_from_chunks(chunks, "Need Azure security", top_k=1)

    assert isinstance(results, list)
    assert results[0]["proposal_id"] == "proposal_001"
    assert results[0]["chunk_id"] == "proposal_001_chunk_001"
    assert "similarity_score" in results[0]
    assert results[0]["supporting_text"] == "Azure migration and security"


def test_build_dashboard_payload_defaults_non_finite_numeric_values():
    """Vector payload normalization should not leak NaN or infinity."""

    payload = build_dashboard_payload(
        query_text="Need Azure support",
        results=[],
        recommended_directors=[
            {
                "director_name": "Director Numeric",
                "capacity_label": "Available",
                "capacity_score": float("nan"),
                "relative_load": float("inf"),
                "assignment_score": float("-inf"),
            }
        ],
    )
    director = payload["recommended_directors"][0]

    assert director["capacity_score"] == 0.72
    assert director["relative_load"] == 0.65
    assert director["assignment_score"] == 0.474

"""Tests for Sprint 4 RFP retrieval evidence validation helpers."""

from src.rfp_evidence_validator import (
    assess_claim_support,
    compare_retrieval_paths,
    evaluate_retrieval_example,
    summarize_chunk_evidence_support,
)


def test_summarize_chunk_evidence_support_counts_metadata_gaps():
    """Check that metadata support separates semantic evidence from linkage."""

    chunks = [
        {
            "proposal_id": "proposal_alpha",
            "document_id": "proposal_alpha__proposal",
            "source_type": "proposal",
            "chunk_id": "proposal_alpha_chunk_001",
            "chunk_index": 0,
            "text": "Cloud migration and managed services response requirements.",
            "opportunity_owner": None,
            "opportunity_id": None,
        },
        {
            "proposal_id": "proposal_alpha",
            "document_id": "proposal_alpha__response_001",
            "source_type": "proposal_response",
            "chunk_id": "proposal_alpha_chunk_002",
            "chunk_index": 1,
            "text": "Prior response describes Azure delivery support.",
            "opportunity_owner": None,
            "opportunity_id": None,
        },
    ]

    summary = summarize_chunk_evidence_support(chunks)

    assert summary["total_chunks"] == 2
    assert summary["chunks_with_text"] == 2
    assert summary["chunks_with_proposal_id"] == 2
    assert summary["chunks_with_document_id"] == 2
    assert summary["source_type_counts"] == {
        "proposal": 1,
        "proposal_response": 1,
    }
    assert summary["chunks_with_opportunity_owner"] == 0
    assert summary["chunks_with_opportunity_id"] == 0
    assert summary["unique_proposal_ids"] == 1
    assert summary["unique_document_ids"] == 2


def test_assess_claim_support_blocks_director_and_opportunity_claims_without_linkage():
    """Check that missing linkage fields produce explicit unsupported claims."""

    chunk_summary = {
        "total_chunks": 3,
        "chunks_with_text": 3,
        "chunks_with_proposal_id": 3,
        "chunks_with_document_id": 3,
        "source_type_counts": {"proposal": 2, "proposal_response": 1},
        "chunks_with_opportunity_owner": 0,
        "chunks_with_opportunity_id": 0,
    }

    support = assess_claim_support(chunk_summary)

    assert support["similar_historical_rfp_claim"]["supported"] is True
    assert support["director_experience_claim"]["supported"] is False
    assert support["opportunity_linkage_claim"]["supported"] is False
    assert "semantic similarity" in support["similar_historical_rfp_claim"]["wording"]
    assert "not proven director experience" in support["director_experience_claim"]["caveat"]
    assert "not linked to CRM opportunity IDs" in support["opportunity_linkage_claim"]["caveat"]


def test_evaluate_retrieval_example_labels_relevant_and_weak_results():
    """Check that evidence rows flag relevant and misleading retrieved chunks."""

    relevant = evaluate_retrieval_example(
        query_theme="cloud migration",
        result={
            "proposal_id": "proposal_alpha",
            "chunk_id": "proposal_alpha_chunk_001",
            "similarity_score": 0.82,
            "supporting_text": "Azure cloud migration and managed services support.",
        },
        expected_terms={"cloud", "migration", "managed"},
    )
    weak = evaluate_retrieval_example(
        query_theme="cybersecurity compliance",
        result={
            "proposal_id": "proposal_beta",
            "chunk_id": "proposal_beta_chunk_001",
            "similarity_score": 0.21,
            "supporting_text": "Payroll workflow and office supply transition.",
        },
        expected_terms={"cybersecurity", "compliance", "risk"},
    )

    assert relevant["looks_relevant"] is True
    assert relevant["supports_summary_or_match_reason"] is True
    assert relevant["weak_or_misleading_note"] == ""
    assert relevant["matched_expected_terms"] == ["cloud", "managed", "migration"]
    assert weak["looks_relevant"] is False
    assert weak["supports_summary_or_match_reason"] is False
    assert "No expected theme terms found" in weak["weak_or_misleading_note"]


def test_compare_retrieval_paths_reports_overlap_and_quality_notes():
    """Check that Azure/local comparison records are report-ready."""

    azure_results = [
        {
            "chunk_id": "cloud_chunk_001",
            "proposal_id": "proposal_cloud",
            "similarity_score": 0.91,
            "supporting_text": "Cloud migration and managed service transition.",
        },
        {
            "chunk_id": "security_chunk_001",
            "proposal_id": "proposal_security",
            "similarity_score": 0.55,
            "supporting_text": "Security risk assessment.",
        },
    ]
    local_results = [
        {
            "chunk_id": "cloud_chunk_001",
            "proposal_id": "proposal_cloud",
            "similarity_score": 0.75,
            "supporting_text": "Cloud migration and managed service transition.",
        },
        {
            "chunk_id": "dashboard_chunk_001",
            "proposal_id": "proposal_dashboard",
            "similarity_score": 0.4,
            "supporting_text": "Dashboard reporting implementation.",
        },
    ]

    comparison = compare_retrieval_paths(
        query_theme="cloud migration",
        azure_results=azure_results,
        local_results=local_results,
        expected_terms={"cloud", "migration"},
    )

    assert comparison["query_theme"] == "cloud migration"
    assert comparison["azure_top_chunk_ids"] == ["cloud_chunk_001", "security_chunk_001"]
    assert comparison["local_top_chunk_ids"] == ["cloud_chunk_001", "dashboard_chunk_001"]
    assert comparison["overlap_chunk_ids"] == ["cloud_chunk_001"]
    assert comparison["top_result_agrees"] is True
    assert comparison["azure_available"] is True
    assert comparison["local_available"] is True
    assert comparison["quality_note"] == "Top Azure/Chroma and local fallback result agree."

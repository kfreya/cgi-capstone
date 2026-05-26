"""Tests for the dashboard-facing RFP assignment wrapper.

This file checks the public output shape that the Streamlit RFP placeholder is
expecting from Role 5.

Run tests from the repository root so imports resolve consistently. For example:
`python -m pytest tests/test_rfp_engine.py`.
"""

import pandas as pd

from src.rfp_preprocessor import prepare_rfp_chunks
from src.rfp_engine import generate_assignment_context
from src.vector_store import build_vector_store


def test_generate_assignment_context_matches_dashboard_contract():
    """Check that the assignment output matches the Week 3 contract."""

    director_df = pd.DataFrame(
        {
            "opportunity_owner": ["Director A"],
            "capacity_label": ["Available"],
            "capacity_score": [0.72],
            "relative_load": [0.65],
        }
    )

    output = generate_assignment_context(
        "Need Azure migration support and dashboard reporting.",
        director_df,
        historical_chunks=[
            {
                "proposal_id": "historical_azure",
                "chunk_id": "historical_azure_chunk_001",
                "source_type": "proposal",
                "text": "Prior Azure migration and dashboard reporting proposal.",
                "chunk_index": 0,
                "opportunity_owner": None,
                "opportunity_id": None,
            }
        ],
    )

    assert set(output) == {
        "rfp_summary",
        "effort",
        "similar_rfps",
        "retrieved_examples",
        "recommended_directors",
        "risk_flags",
        "notes",
    }
    assert output["retrieved_examples"][0]["chunk_id"] == "historical_azure_chunk_001"
    assert output["similar_rfps"][0]["source"] == "historical_azure_chunk_001"
    assert output["effort"]["level"] in {"Low", "Medium", "High"}
    assert output["effort"]["reason"]
    assert output["effort"]["rationale"] == output["effort"]["reason"]
    assert "similarity_score" in output["retrieved_examples"][0]
    assert "supporting_text" in output["retrieved_examples"][0]
    assert output["recommended_directors"][0]["director_name"] == "Director A"
    assert output["recommended_directors"][0]["match_reason"]
    assert output["recommended_directors"][0]["capacity_label"] == "Available"
    assert output["recommended_directors"][0]["capacity_score"] == 0.72
    assert output["recommended_directors"][0]["relative_load"] == 0.65
    assert "assignment_score" in output["recommended_directors"][0]
    assert "capacity_explanation" in output["recommended_directors"][0]
    assert "experience_match_explanation" in output["recommended_directors"][0]
    assert isinstance(output["recommended_directors"][0]["supporting_chunks"], list)
    assert output["notes"] == "Prototype output for dashboard integration."


def test_generate_assignment_context_uses_mock_director_when_missing():
    """Check that the prototype still runs without real director data."""

    output = generate_assignment_context("Need cloud analytics support.")

    assert output["recommended_directors"][0]["director_name"] == "Director A"
    assert output["recommended_directors"][0]["capacity_label"] == "Available"
    assert isinstance(output["risk_flags"], list)
    assert any(
        "mock director data" in flag["message"].lower()
        for flag in output["risk_flags"]
    )


def test_generate_assignment_context_returns_stable_types_for_empty_text():
    """Check that empty dashboard input still returns safe output types."""

    output = generate_assignment_context("")

    assert isinstance(output["rfp_summary"], str)
    assert isinstance(output["effort"], dict)
    assert isinstance(output["similar_rfps"], list)
    assert isinstance(output["retrieved_examples"], list)
    assert isinstance(output["recommended_directors"], list)
    assert isinstance(output["risk_flags"], list)
    assert isinstance(output["notes"], str)


def test_generate_assignment_context_does_not_retrieve_new_rfp_from_stale_store():
    """Check that the new RFP is only the query, never the retrieval corpus."""

    new_rfp_text = (
        "Need Azure migration support, analytics dashboards, and managed "
        "service transition planning for a new government RFP."
    )
    build_vector_store(prepare_rfp_chunks(new_rfp_text))

    output = generate_assignment_context(new_rfp_text)

    retrieved_examples = output["retrieved_examples"]
    assert retrieved_examples
    assert all(
        example["chunk_id"] != "proposal_001_chunk_001"
        for example in retrieved_examples
    )
    assert all(
        example["chunk_id"].startswith("historical_sample_chunk_")
        for example in retrieved_examples
    )
    assert all(
        example["supporting_text"] != new_rfp_text
        for example in retrieved_examples
    )
    assert any(
        "sample historical corpus" in flag["message"].lower()
        for flag in output["risk_flags"]
    )


def test_generate_assignment_context_ranks_directors_by_capacity_signal():
    """Check that better capacity signals move a director higher."""

    director_df = pd.DataFrame(
        {
            "opportunity_owner": ["Director Busy", "Director Ready"],
            "capacity_label": ["Overextended", "Available"],
            "capacity_score": [0.05, 0.88],
            "relative_load": [2.4, 0.4],
            "service_domain": ["Cloud Infrastructure", "Cloud Infrastructure"],
        }
    )
    historical_chunks = [
        {
            "proposal_id": "historical_cloud",
            "chunk_id": "historical_cloud_chunk_001",
            "source_type": "proposal",
            "text": "Prior Azure cloud migration and dashboard proposal.",
            "chunk_index": 0,
            "opportunity_owner": None,
            "opportunity_id": None,
        }
    ]

    output = generate_assignment_context(
        "Need Azure cloud migration and dashboard reporting.",
        director_df=director_df,
        historical_chunks=historical_chunks,
    )

    directors = output["recommended_directors"]
    assert directors[0]["director_name"] == "Director Ready"
    assert directors[0]["assignment_score"] > directors[1]["assignment_score"]
    assert any(
        "overextended" in flag["message"].lower()
        for flag in output["risk_flags"]
    )


def test_generate_assignment_context_scores_all_directors_before_top_three():
    """Check that strong candidates are not skipped by input row order."""

    director_df = pd.DataFrame(
        {
            "opportunity_owner": [f"Director {index}" for index in range(9)],
            "capacity_label": ["High Load"] * 8 + ["Available"],
            "capacity_score": [0.0] * 8 + [0.99],
            "relative_load": [1.5] * 8 + [0.1],
            "service_domain": ["Application Support"] * 8 + ["Cloud Infrastructure"],
        }
    )
    historical_chunks = [
        {
            "proposal_id": "historical_cloud",
            "chunk_id": "historical_cloud_chunk_001",
            "source_type": "proposal",
            "text": "Prior Azure cloud migration proposal.",
            "chunk_index": 0,
            "opportunity_owner": None,
            "opportunity_id": None,
        }
    ]

    output = generate_assignment_context(
        "Need Azure cloud migration support.",
        director_df=director_df,
        historical_chunks=historical_chunks,
    )

    assert output["recommended_directors"][0]["director_name"] == "Director 8"
    assert output["recommended_directors"][0]["capacity_label"] == "Available"


def test_generate_assignment_context_uses_service_domain_signal():
    """Check that matching service experience helps the director ranking."""

    director_df = pd.DataFrame(
        {
            "opportunity_owner": ["Director Data", "Director Apps"],
            "capacity_label": ["Available", "Available"],
            "capacity_score": [0.70, 0.70],
            "relative_load": [0.8, 0.8],
            "service_domain": ["Data Analytics and Reporting", "Application Development"],
        }
    )
    historical_chunks = [
        {
            "proposal_id": "historical_reporting",
            "chunk_id": "historical_reporting_chunk_001",
            "source_type": "proposal",
            "text": "Prior data analytics dashboard reporting proposal.",
            "chunk_index": 0,
            "opportunity_owner": None,
            "opportunity_id": None,
        }
    ]

    output = generate_assignment_context(
        "Need data analytics dashboard reporting.",
        director_df=director_df,
        historical_chunks=historical_chunks,
    )

    directors = output["recommended_directors"]
    assert directors[0]["director_name"] == "Director Data"
    assert directors[0]["assignment_score"] > directors[1]["assignment_score"]
    assert "service-keyword overlap" in directors[0]["experience_match_explanation"]


def test_generate_assignment_context_flags_missing_capacity_fields():
    """Check that incomplete director data is labelled as a risk."""

    director_df = pd.DataFrame(
        {
            "opportunity_owner": ["Director Partial"],
            "capacity_label": ["Available"],
            "capacity_score": [None],
            "relative_load": [None],
        }
    )

    output = generate_assignment_context(
        "Need analytics dashboard support.",
        director_df=director_df,
        historical_chunks=[
            {
                "proposal_id": "historical_dashboard",
                "chunk_id": "historical_dashboard_chunk_001",
                "source_type": "proposal",
                "text": "Prior analytics dashboard support proposal.",
                "chunk_index": 0,
                "opportunity_owner": None,
                "opportunity_id": None,
            }
        ],
    )

    assert any(
        "capacity fields are missing" in flag["message"].lower()
        for flag in output["risk_flags"]
    )


def test_generate_assignment_context_treats_nan_capacity_fields_as_missing():
    """Check that No-baseline capacity rows do not produce NaN scores."""

    director_df = pd.DataFrame(
        {
            "opportunity_owner": ["Director No Baseline", "Director Ready"],
            "capacity_label": ["No baseline", "Available"],
            "capacity_score": [float("nan"), 0.7],
            "relative_load": [float("nan"), 0.8],
            "service_domain": ["Cloud Infrastructure", "Cloud Infrastructure"],
        }
    )

    output = generate_assignment_context(
        "Need Azure cloud migration support.",
        director_df=director_df,
        historical_chunks=[
            {
                "proposal_id": "historical_cloud",
                "chunk_id": "historical_cloud_chunk_001",
                "source_type": "proposal",
                "text": "Prior Azure cloud migration support proposal.",
                "chunk_index": 0,
                "opportunity_owner": None,
                "opportunity_id": None,
            }
        ],
    )

    no_baseline = next(
        director
        for director in output["recommended_directors"]
        if director["director_name"] == "Director No Baseline"
    )
    assert no_baseline["capacity_score"] == 0.45
    assert no_baseline["relative_load"] == 1.0
    assert no_baseline["assignment_score"] < 1.0
    assert "nan" not in no_baseline["capacity_explanation"].lower()
    assert any(
        "capacity fields are missing" in flag["message"].lower()
        for flag in output["risk_flags"]
    )


def test_generate_assignment_context_treats_inf_capacity_fields_as_missing():
    """Check that non-finite capacity values use safe defaults."""

    director_df = pd.DataFrame(
        {
            "opportunity_owner": ["Director Infinite"],
            "capacity_label": ["Available"],
            "capacity_score": [float("inf")],
            "relative_load": [float("-inf")],
            "service_domain": ["Cloud Infrastructure"],
        }
    )

    output = generate_assignment_context(
        "Need Azure cloud migration support.",
        director_df=director_df,
        historical_chunks=[
            {
                "proposal_id": "historical_cloud",
                "chunk_id": "historical_cloud_chunk_001",
                "source_type": "proposal",
                "text": "Prior Azure cloud migration support proposal.",
                "chunk_index": 0,
                "opportunity_owner": None,
                "opportunity_id": None,
            }
        ],
    )

    director = output["recommended_directors"][0]
    assert director["capacity_score"] == 0.45
    assert director["relative_load"] == 1.0
    assert director["assignment_score"] < 1.0
    assert any(
        "capacity fields are missing" in flag["message"].lower()
        for flag in output["risk_flags"]
    )


def test_generate_assignment_context_flags_low_similarity():
    """Check that weak retrieval evidence is labelled as a risk."""

    output = generate_assignment_context(
        "Need Azure migration and dashboard reporting.",
        historical_chunks=[
            {
                "proposal_id": "historical_legal",
                "chunk_id": "historical_legal_chunk_001",
                "source_type": "proposal",
                "text": "General procurement terms and contract instructions.",
                "chunk_index": 0,
                "opportunity_owner": None,
                "opportunity_id": None,
            }
        ],
    )

    assert any(
        "low similarity" in flag["message"].lower()
        for flag in output["risk_flags"]
    )


def test_generate_assignment_context_effort_uses_complexity_signals():
    """Check that service breadth and complexity can raise effort."""

    long_complex_rfp = " ".join(
        ["enterprise Azure migration security integration managed services"]
        * 70
    )

    output = generate_assignment_context(
        long_complex_rfp,
        historical_chunks=[
            {
                "proposal_id": "historical_complex",
                "chunk_id": "historical_complex_chunk_001",
                "source_type": "proposal",
                "text": "Azure migration security integration managed services.",
                "chunk_index": 0,
                "opportunity_owner": None,
                "opportunity_id": None,
            }
        ],
    )

    assert output["effort"]["level"] == "High"
    assert "service areas" in output["effort"]["reason"]
    assert "complexity terms" in output["effort"]["reason"]

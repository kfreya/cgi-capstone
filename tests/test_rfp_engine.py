"""Tests for the dashboard-facing RFP assignment wrapper.

This file checks the public output shape that the Streamlit RFP placeholder is
expecting from Role 5.

Run tests from the repository root so imports resolve consistently. For example:
`python -m pytest tests/test_rfp_engine.py`.
"""

import pandas as pd

from src.rfp_engine import generate_assignment_context


def test_generate_assignment_context_matches_dashboard_contract():
    """Check that the assignment output matches the Week 2 contract."""

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

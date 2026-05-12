"""Tests for preprocessing historical RFP proposal text.

These tests use small synthetic records because the real CGI proposal data is
not committed to Git. The goal is to check the behavior that matters for the
RFP retrieval pipeline: text normalization, proposal/response extraction,
overlapping chunks, and traceable chunk metadata.

Run tests from the repository root so imports resolve consistently. For example:
`python -m pytest tests/test_rfp_preprocessor.py`.
"""

import pytest

from src.rfp_preprocessor import (
    chunk_text,
    estimate_token_count,
    extract_rfp_documents,
    normalize_text_content,
    preprocess_proposals,
)


def test_normalize_text_content_handles_common_json_shapes():
    """Check that raw JSON text shapes become one clean text string."""

    content = [
        " first paragraph ",
        "",
        {"content": ["second paragraph", " third paragraph "]},
    ]

    assert (
        normalize_text_content(content)
        == "first paragraph\nsecond paragraph\nthird paragraph"
    )


def test_extract_rfp_documents_reads_proposal_and_responses():
    """Check that one RFP can produce both proposal and response documents."""

    proposals = {
        "Sample RFP": {
            "proposal": {
                "content": ["Need cloud migration support."],
                "proposal_response": {
                    "Technical": {"content": ["We propose Azure delivery."]},
                },
            }
        }
    }

    documents = extract_rfp_documents(proposals)

    assert len(documents) == 2
    assert documents[0].section == "proposal"
    assert documents[1].section == "response:Technical"
    assert documents[1].metadata["response_name"] == "Technical"


def test_chunk_text_uses_approx_token_overlap():
    """Check that chunks stay within size limits and preserve overlap."""

    text = " ".join(f"token_{number}" for number in range(12))

    chunks = chunk_text(text, max_tokens=5, overlap_tokens=2)

    assert len(chunks) == 4
    # The end of one chunk should be repeated at the start of the next chunk.
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]
    assert max(estimate_token_count(chunk) for chunk in chunks) <= 5


def test_chunk_text_validates_settings():
    """Check that invalid chunk settings fail before preprocessing starts."""

    with pytest.raises(ValueError, match="overlap_tokens"):
        chunk_text("text", max_tokens=5, overlap_tokens=5)


def test_preprocess_proposals_returns_traceable_chunk_metadata():
    """Check the full preprocessing path from proposal JSON to RFP chunks."""

    proposals = {
        "Analytics RFP": {
            "proposal": {
                "content": [
                    "Build a dashboard and forecasting workflow for directors."
                ],
                "proposal_response": {},
            }
        }
    }

    chunks = preprocess_proposals(proposals, max_tokens=4, overlap_tokens=1)

    assert len(chunks) >= 1
    assert chunks[0].metadata["source_type"] == "proposal"
    assert "chunk_start_token" in chunks[0].metadata
    assert "approx_tokens" in chunks[0].metadata
    assert chunks[0].chunk_id.endswith("__chunk_0000")

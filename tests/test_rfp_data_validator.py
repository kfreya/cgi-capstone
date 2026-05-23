"""Tests for Sprint 3 RFP validation helpers."""

from __future__ import annotations

import json

import pytest

from src.rfp_data_validator import (
    REQUIRED_CHUNK_FIELDS,
    build_validation_report,
    find_malformed_records,
    generate_sample_chunk_rows,
    load_proposals_json,
    profile_documents,
    summarize_document_lengths,
    summarize_proposal_response_separation,
    summarize_structure,
    validate_chunk_metadata_fields,
)
from src.rfp_preprocessor import RFPChunk


def _sample_proposals() -> dict[str, object]:
    return {
        "Analytics RFP": {
            "proposal": {
                "content": (
                    "Need cloud migration, reporting, and managed services support."
                ),
                "proposal_response": {
                    "Technical": {"content": "CGI can deliver phased migration."},
                    "Delivery": {"content": "Dedicated PM and governance cadence."},
                },
            }
        },
        "Malformed Entry": "unexpected scalar record",
        "No Proposal Text": {
            "proposal": {
                "content": "",
                "proposal_response": {"Ops": {"content": ""}},
            }
        },
    }


def test_summarize_structure_counts_mapping_and_response_keys():
    summary = summarize_structure(_sample_proposals())

    assert summary["total_records"] == 3
    assert summary["valid_mapping_records"] == 2
    assert summary["non_mapping_records"] == 1
    assert summary["records_with_proposal_key"] == 2
    assert summary["response_key_distribution"]["proposal_response"] == 2
    assert summary["malformed_record_count"] == 1
    assert summary["malformed_record_refs"] == ["record_002"]


def test_find_malformed_records_flags_non_mapping_and_empty_content():
    issues = find_malformed_records(_sample_proposals())
    issue_types = {issue["issue"] for issue in issues}

    assert "entry_not_mapping" in issue_types
    assert "proposal_content_unusable" in issue_types


def test_find_malformed_records_can_opt_in_sensitive_titles():
    issues = find_malformed_records(_sample_proposals(), include_sensitive_fields=True)

    assert any("title" in issue for issue in issues)


def test_document_length_summary_handles_empty_input():
    summary = summarize_document_lengths([])

    assert summary["total_documents"] == 0
    assert summary["token_count"] == {}
    assert summary["char_count"] == {}


def test_validate_chunk_metadata_fields_reports_required_fields():
    validation = validate_chunk_metadata_fields(_sample_proposals(), chunk_size=20, overlap=5)

    assert validation["total_chunks"] > 0
    assert validation["required_fields"] == list(REQUIRED_CHUNK_FIELDS)
    assert all(count == 0 for count in validation["missing_field_counts"].values())
    assert validation["null_field_counts"]["opportunity_owner"] == validation["total_chunks"]
    assert validation["can_link_to_owner_or_opportunity"] is False


def test_generate_sample_chunk_rows_redacts_text_by_default():
    rows = generate_sample_chunk_rows(_sample_proposals(), chunk_size=20, overlap=5, sample_size=2)

    assert len(rows) == 2
    assert rows[0]["text"] == "<redacted; use --include-text to export preview>"
    assert rows[0]["text_token_count_estimate"] > 0


def test_generate_sample_chunk_rows_anonymization_preserves_grouping():
    raw_rows = generate_sample_chunk_rows(
        _sample_proposals(),
        chunk_size=20,
        overlap=5,
        sample_size=12,
        anonymize_ids=False,
    )
    anon_rows = generate_sample_chunk_rows(
        _sample_proposals(),
        chunk_size=20,
        overlap=5,
        sample_size=12,
        anonymize_ids=True,
    )

    proposal_map: dict[str, str] = {}
    document_map: dict[str, str] = {}

    for raw_row, anon_row in zip(raw_rows, anon_rows, strict=True):
        raw_proposal = str(raw_row["proposal_id"])
        raw_document = str(raw_row["document_id"])
        anon_proposal = str(anon_row["proposal_id"])
        anon_document = str(anon_row["document_id"])

        if raw_proposal in proposal_map:
            assert proposal_map[raw_proposal] == anon_proposal
        else:
            proposal_map[raw_proposal] = anon_proposal

        if raw_document in document_map:
            assert document_map[raw_document] == anon_document
        else:
            document_map[raw_document] = anon_document

    assert all(row["opportunity_owner"] is None for row in anon_rows)
    assert all(row["opportunity_id"] is None for row in anon_rows)
    assert all("title" in row for row in anon_rows)
    assert all("section" in row for row in anon_rows)


def test_generate_sample_chunk_rows_includes_text_when_requested():
    rows = generate_sample_chunk_rows(
        _sample_proposals(),
        chunk_size=20,
        overlap=5,
        sample_size=1,
        include_text=True,
        max_text_chars=24,
    )

    assert len(rows[0]["text"]) <= 24
    assert rows[0]["text_char_count"] >= len(rows[0]["text"])


def test_generate_sample_chunk_rows_samples_across_documents():
    rows = generate_sample_chunk_rows(
        _sample_proposals(),
        chunk_size=2,
        overlap=0,
        sample_size=6,
    )

    document_ids = {str(row["document_id"]) for row in rows}
    source_types = {str(row["source_type"]) for row in rows}

    assert len(document_ids) >= 3
    assert "proposal" in source_types
    assert "proposal_response" in source_types


def test_profile_documents_returns_source_types():
    profiles = profile_documents(_sample_proposals())

    assert len(profiles) > 0
    assert {item["source_type"] for item in profiles} == {
        "proposal",
        "proposal_response",
    }


def test_load_proposals_json_raises_on_non_mapping_payload(tmp_path):
    sample_path = tmp_path / "bad_payload.json"
    sample_path.write_text(json.dumps([{"invalid": "shape"}]), encoding="utf-8")

    with pytest.raises(TypeError, match="JSON object"):
        load_proposals_json(sample_path)


def test_summarize_proposal_response_separation_counts_records():
    separation = summarize_proposal_response_separation(_sample_proposals())

    assert separation["total_records"] == 3
    assert separation["records_with_proposal_text"] == 1
    assert separation["records_with_response_container"] == 2


def test_build_validation_report_has_required_sections():
    report = build_validation_report(_sample_proposals(), chunk_size=20, overlap=5)

    assert "structure_summary" in report
    assert "document_length_summary" in report
    assert "chunk_metadata_validation" in report
    assert "sample_chunks" not in report


def test_validate_chunk_metadata_fields_detects_missing_owner_and_opportunity_keys(monkeypatch):
    chunk = RFPChunk(
        chunk_id="chunk_1",
        document_id="doc_1",
        title="T",
        section="proposal",
        chunk_index=0,
        text="hello world",
        metadata={"proposal_id": "p_1", "source_type": "proposal"},
    )

    monkeypatch.setattr("src.rfp_data_validator.preprocess_proposals", lambda *args, **kwargs: [chunk])
    validation = validate_chunk_metadata_fields({"A": {"proposal": {"content": "text"}}})

    assert validation["missing_field_counts"]["opportunity_owner"] == 1
    assert validation["missing_field_counts"]["opportunity_id"] == 1

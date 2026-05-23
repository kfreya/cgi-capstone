# RFP Data Validation Notes (Sprint 3, Issue #38)

## Scope

This note documents Week 3 validation work for:

- `data/proposals_responses.json` structure and consistency
- RFP document text quality for chunking/retrieval
- chunk metadata contract and linkage limitations
- sample chunk outputs for Lyken and Jai handoff

Validation is implemented in:

- `src/rfp_data_validator.py`
- `scripts/validate_rfp_data_and_export_samples.py`

Generated artifacts:

- `outputs/rfp_validation/rfp_validation_summary.json`
- `outputs/rfp_validation/rfp_sample_chunks.json`

Both outputs are generated with safe defaults: sample text is redacted and
sample IDs are anonymized unless flags explicitly opt out.

## Repro Command

Run from repo root in the project environment:

```bash
python scripts/validate_rfp_data_and_export_samples.py
```

Optional (only when local data sharing is explicitly approved):

```bash
python scripts/validate_rfp_data_and_export_samples.py --include-text --keep-original-ids
```

## Structure Summary

From `outputs/rfp_validation/rfp_validation_summary.json`:

- Total top-level records: `19`
- Valid mapping records: `19`
- Non-mapping records: `0`
- Records with `proposal` key: `19`
- Records with response key: `19`
- Response key usage: `proposal_response` on all records
- Malformed top-level records: none

Interpretation: the JSON follows a consistent container shape and can be parsed
deterministically for preprocessing.

## Document Length Distribution

Extracted via `extract_rfp_documents()`:

- Total extracted documents: `46`
  - Proposal documents: `19`
  - Response documents: `27`
- Empty documents: `0`
- Short documents (`<80` token estimate): `0`
- Long documents (`>1200` token estimate): `43`

Token estimate distribution:

- Min: `1106`
- P25: `6427.25`
- Median: `11777.0`
- Mean: `11688.7`
- P75: `15342.5`
- Max: `29060`

Interpretation: almost all records are long; chunking is required before
embedding/retrieval.

## Data Quality and Malformed Checks

Current validation flags:

- non-mapping entry records
- non-mapping proposal blocks
- empty/unusable proposal content
- unsupported response container types
- proposal/response separation consistency
- sensitive-title-safe malformed reporting (`record_ref` + `title_hash`)

Current run result:

- Malformed record list: empty
- Records with proposal text: `19`
- Records with response container: `19`
- Records with non-empty response text: `19`
- Records missing both proposal/response text: `0`

Interpretation: proposal and response text are separated consistently in the
current local JSON.

## Chunk Metadata Dictionary (Validated Fields)

The Sprint 3 validation checks these required chunk-level fields:

- `proposal_id`: stable proposal identifier used for grouping and traceability
- `chunk_id`: unique chunk identifier
- `document_id`: parent proposal/response document ID
- `source_type`: `proposal` or `proposal_response`
- `chunk_index`: zero-based chunk position within source document
- `text`: chunk text payload (redacted in exported sample by default)
- `opportunity_owner`: nullable linkage field
- `opportunity_id`: nullable linkage field

Validation summary from current run:

- Total chunks validated: `1216`
- Missing required fields: `0` for all fields
- Null fields:
  - `opportunity_owner`: `1216`
  - `opportunity_id`: `1216`
  - all other required fields: `0`

## Proposal-to-Director Linkage Limitation

Current chunks do **not** contain reliable `opportunity_owner` or
`opportunity_id` values. Therefore:

- proposal chunks cannot be linked to directors/opportunities from metadata alone
- director recommendation must combine retrieval evidence with external capacity
  tables, not inferred direct joins from chunk metadata
- this should remain explicitly documented in assignment logic notes until a
  trusted crosswalk is provided

## Sample Chunk Output for Handoff

`outputs/rfp_validation/rfp_sample_chunks.json` contains handoff-ready sample
rows (default: text redacted, IDs anonymized), including:

- `proposal_id`
- `chunk_id`
- `document_id`
- `source_type`
- `chunk_index`
- `text` (redacted by default)
- `opportunity_owner`
- `opportunity_id`
- `text_char_count`
- `text_token_count_estimate`

Anonymization keeps stable grouping (same source proposal/document retains the
same anonymized ID across chunks).

Use `--include-text` and `--keep-original-ids` only for controlled local review.

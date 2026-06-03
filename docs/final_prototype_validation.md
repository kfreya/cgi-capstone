# Final Prototype Validation

Date: May 31, 2026

This document records the fixes implemented in the end of Sprint 4 to stabilize the final prototype. 

## Scope

The final prototype now represents an architecture-complete stakeholder demo, not a production-ready assignment system. It supports the Director Capacity Dashboard, the RFP Assignment Tool, capacity-aware recommendations, upload or paste RFP input, Azure OpenAI chat enrichment when configured, Azure/Chroma retrieval when available, and documented fallback behavior.

## Implemented Fixes

### RFP Input Workflow

- Enabled RFP upload in the Streamlit RFP page.
- Supported uploaded `.txt`, `.docx`, and text-based `.pdf` files.
- Added text extraction helpers for TXT, DOCX, and PDF inputs.
- Preserved manual paste input as the fallback path.
- Added upload success/error handling in session state.
- Added `pypdf` to `requirements.txt` and `environment.yml`.
- Updated RFP UI wording so it no longer describes upload as unavailable.

Remaining boundary: scanned PDFs may still require manual paste or OCR because only text-based PDF extraction is supported.

### Streamlit Dashboard Polish

- Replaced deprecated Streamlit `use_container_width=True` usage with `width="stretch"`.
- Kept the RFP page status banners aligned with final prototype behavior.
- Displayed retrieval mode, capacity source, corpus source, corpus chunk count, query chunk count, and retrieval caveats.
- Preserved severity-specific risk flag rendering.
- Added a separate LLM enrichment caption so users can distinguish local retrieval fallback from Azure OpenAI chat enrichment status.
- Renamed the retrieved-evidence section to "Retrieved Supporting Examples" to avoid implying that each row is a full distinct historical RFP.
- Rounded recommendation metrics for stakeholder display (`capacity_score`, `relative_load`, and `assignment_score`).

### Retrieval Path

- Updated the RFP engine to load the full local `data/proposals_responses.json` proposal corpus when available.
- Kept the smaller sample corpus as a fallback only when the proposal corpus is unavailable.
- Chunked the newly submitted RFP query before retrieval.
- Added query-chunk support to Azure/Chroma retrieval.
- Added multi-query local fallback retrieval in `vector_store.py`.
- Added an on-demand Azure/Chroma build cap for large corpora.
- Changed full-corpus Azure/Chroma skip behavior from an error to an explicit fallback notice.
- Kept local retrieval over the same corpus as the stable fallback when Azure/Chroma is unavailable or skipped.

Remaining boundary: retrieved proposal chunks do not include reliable `opportunity_owner` or `opportunity_id` linkage, so retrieval evidence should be treated as semantic similarity evidence, not proof of a director's prior experience.

### Capacity and Service Fit

- Added owner-level `service_solution` profiles to `director_capacity_df`.
- Built `service_solution` profiles only from open/won opportunities.
- Added `service_solution` to the dashboard column dictionary and mock capacity data.
- Updated RFP director matching to use service/profile fields, including `service_solution`.
- Changed service-overlap explanations so `0.00` is shown only when a director service profile exists but does not overlap with the RFP.
- Added clearer states for missing RFP service labels and missing director service profiles.

Remaining boundary: `service_solution` is a lightweight service-fit proxy, not a validated expertise or historical-performance measure.

### RFP Assignment Logic

- Kept `generate_assignment_context()` capacity-aware by passing loaded `capacity_df` into the RFP engine.
- Scored all candidate directors before selecting the top three.
- Ranked recommendations using capacity score, retrieval similarity, service fit, and capacity label bonus.
- Kept heuristic defaults for missing/non-finite capacity values so `NaN` and `inf` do not leak into dashboard output.
- Improved risk flag wording for `No baseline` directors:
  - Directors with no historical baseline now get a baseline-specific warning.
  - Truly missing or non-finite capacity rows still get a generic missing-fields warning.

### Azure OpenAI Chat Enrichment

- Kept Azure chat enrichment for RFP summary, effort estimate, and director match reasons.
- Added JSON response-format support to the Azure chat client.
- Added fallback behavior when an Azure deployment does not support the response-format parameter.
- Reduced and tightened the LLM prompt to limit truncated JSON responses.
- Limited director match-reason candidates passed to the LLM.
- Wrapped LLM-generated director match wording with a prototype-fit caveat when real director records are used, preventing unsupported claims of proven prior director experience.
- Logged Azure chat enrichment failures while preserving deterministic heuristic fallback.

Remaining boundary: LLM output is prototype explanation text, not authoritative staffing guidance.

### Documentation

- Updated `docs/architecture.md` to match the final prototype.
- Updated integration and QA docs to remove stale statements that Azure/Chroma was not integrated.
- Updated docs to reflect upload support, full proposal-corpus retrieval, query chunking, service-solution profiles, LLM enrichment, and current fallback behavior.
- Added or updated caveats for missing proposal-to-director linkage, No-baseline directors, scanned PDFs, and prototype-only recommendation status.

### Tests

- Added Azure chat client tests for JSON response-format behavior and fallback.
- Added Azure/Chroma retrieval tests for query chunks and full-corpus fallback notice.
- Added capacity-engine tests for `service_solution` aggregation and open/won filtering.
- Added RFP-engine tests for full proposal corpus loading, query chunking, retrieval linkage caveats, service-overlap states, LLM prompt limiting, and updated capacity warning wording.

## Validation Results

Commands run in the `cgi-capstone` conda environment:

```bash
conda run -n cgi-capstone python -m pytest
```

Result:

```text
148 passed, 1 warning
```

```bash
conda run -n cgi-capstone python -m py_compile app/app.py src/rfp_engine.py src/azure_client.py src/azure_rag_client.py src/capacity_engine.py src/vector_store.py
```

Result:

```text
passed
```

```bash
git diff --check
```

Result:

```text
passed
```

## Final Prototype Claims

Safe claims:

- The Director Capacity Dashboard runs on real or pre-built capacity data.
- The RFP Assignment Tool can accept pasted text or uploaded TXT/DOCX/text-based PDF input.
- RFP recommendations are capacity-aware when `capacity_df` is available.
- Retrieval uses the local proposal corpus when available, with sample fallback only when needed.
- Azure/Chroma is the preferred retrieval path when available, with local retrieval fallback.
- Azure OpenAI chat enrichment is used when configured, with heuristic fallback on failure.
- The app labels fallback, prototype, linkage, and capacity caveats in the dashboard output.

Claims to avoid:

- Do not claim the system is production-ready.
- Do not claim recommendations are business-validated staffing decisions.
- Do not claim retrieved proposal chunks prove a director's prior experience.
- Do not claim scanned PDF parsing/OCR is supported.
- Do not claim `service_solution` is a complete expertise model.

## Files Changed

- `app/app.py`
- `app/mock_data.py`
- `docs/architecture.md`
- `docs/director_capacity_dashboard_column_dictionary.md`
- `docs/final_integration_qa.md`
- `docs/llm_enriched_rfp_output_&_dashboard.md`
- `docs/rfp_dashboard_integration.md`
- `docs/rfp_week4_status.md`
- `environment.yml`
- `requirements.txt`
- `src/azure_client.py`
- `src/azure_rag_client.py`
- `src/capacity_engine.py`
- `src/rfp_engine.py`
- `src/vector_store.py`
- `tests/test_azure_client.py`
- `tests/test_azure_rag_client.py`
- `tests/test_capacity_engine.py`
- `tests/test_rfp_engine.py`

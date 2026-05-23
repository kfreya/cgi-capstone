# RFP Dashboard Integration Notes — Week 3

**Role 4 owner: Freya**

## Purpose

This document records the Week 3 Streamlit RFP Assignment Tool page
integration. It covers the page structure, the `assignment_context`
field mapping, empty/error state handling, prototype labelling, and
current limitations.

------------------------------------------------------------------------

## Page Structure

The RFP Assignment Tool is Page 2 in `app/app.py`. It is reached via the
sidebar radio button labelled **"RFP Assignment Tool"**.

The page uses a two-column layout:

| Column | Contents |
|------------------------------------|------------------------------------|
| Left (input) | File upload (disabled), RFP text area, Territory / Service Domain dropdowns, Analyze RFP button |
| Right (results) | Prototype notice banner, then one section per `assignment_context` key |

The file upload widget is disabled because RFP document parsing is a
Role 5 (Jai) responsibility. The territory and service domain selectors
are UI context only — they are not passed into backend scoring yet.

------------------------------------------------------------------------

## assignment_context Field Mapping

Every field from `generate_assignment_context()` is displayed. The table
below lists each field and its UI treatment.

| `assignment_context` key | UI Section Header | Display Treatment |
|------------------------|------------------------|------------------------|
| `rfp_summary` | **RFP Summary** | `st.write()` — plain text |
| `effort.level` | **Estimated Effort** | Colour-coded badge (`effort-high`, `effort-medium`, `effort-low` CSS classes) |
| `effort.estimated_duration` | (under Estimated Effort) | `st.caption()` |
| `effort.rationale` | (under Estimated Effort) | `st.write()` — plain text |
| `retrieved_examples` | **Similar Historical RFPs** | One entry per chunk: `proposal_id` bold, `chunk_id` and `similarity_score` in code format, `supporting_text` truncated at 320 chars |
| `recommended_directors` | **Recommended Directors** | One `st.expander()` per director, first expanded by default |
| ↳ `director_name` | Expander title | Text |
| ↳ `capacity_label` | Inside expander | Bold label |
| ↳ `capacity_score` | Inside expander | Numeric |
| ↳ `relative_load` | Inside expander | Numeric |
| ↳ `assignment_score` | Inside expander | Numeric (shown if present) |
| ↳ `match_reason` | Inside expander | `st.write()` |
| ↳ `capacity_explanation` | Inside expander | `st.write()` under bold sub-header |
| ↳ `experience_match_explanation` | Inside expander | `st.write()` under bold sub-header |
| ↳ `supporting_chunks` | Inside expander | `st.caption()` — comma-separated chunk IDs |
| `risk_flags` | **Risk Flags** | One `st.warning()` per flag; shows `level: message` |
| `notes` | **Notes** | `st.caption()` — shown only when non-empty |

The backend key is `effort`, not `estimated_effort`. The dashboard
displays it under the heading **"Estimated Effort"** as agreed with
Yixiao (see `docs/rfp_integration_qa.md`, naming decision section).

The `similar_rfps` key is returned by the engine but is not separately
displayed. It duplicates `retrieved_examples` in a different shape and
was not required by the dashboard spec.

------------------------------------------------------------------------

## Empty / Placeholder State

When no analysis has been run (no `rfp_assignment_context` in session
state), each results section shows a dashed placeholder box with a label
indicating:

-   what will appear there
-   which `assignment_context` key feeds it (e.g.
    `generate_assignment_context() → effort`)

This makes it clear to reviewers that the sections are wired and waiting
for backend output, not broken.

------------------------------------------------------------------------

## Error / API Failure State

If `generate_assignment_context()` raises an exception (for example, if
a dependency import fails or retrieval throws unexpectedly), the error
is caught and stored in `st.session_state["rfp_assignment_error"]`. The
results column then shows an `st.error()` banner with the exception
message and a suggestion to check project dependencies.

The session context is cleared on error so stale results are not shown
alongside the error message.

The local fallback path (`rfp_engine.py` → `rfp_preprocessor.py` →
`InMemoryVectorStore`) does not require Azure credentials and should not
raise under normal conditions. If the error state fires, the likely
cause is a missing package or an import failure, not an API timeout.

------------------------------------------------------------------------

## Prototype / Mock / Fallback Labels

Two visible labels distinguish prototype output from real results:

1.  **Top-of-page notice** (always shown on the RFP page):

    > "This page uses the current **fallback RFP assignment pipeline**.
    > Results are generated from local retrieval and heuristic/prototype
    > assignment logic while Azure-backed retrieval is pending."

2.  **Above results** (`st.info()`, shown once analysis has run):

    > "Prototype fallback output: this analysis uses local fallback
    > retrieval and heuristic assignment logic while Azure-backed
    > retrieval is pending. Do not treat it as final CGI assignment
    > guidance."

These labels satisfy the Week 3 requirement that the dashboard clearly
mark which outputs are real API-backed, fallback, heuristic, or mock.

------------------------------------------------------------------------

## Required Fields from Backend

The following `assignment_context` fields are load-bearing for the UI.
If any are missing or wrongly typed, the section degrades gracefully
(shows an info message or falls back to a default string) rather than
crashing.

| Field | Required type | Graceful fallback |
|------------------------|------------------------|------------------------|
| `rfp_summary` | `str` | `"No summary returned."` |
| `effort` | `dict` | empty dict; badge shows "Unknown" |
| `effort.level` | `str` — one of Low / Medium / High | badge class defaults to plain `badge` |
| `effort.rationale` | `str` | `None` is silently skipped |
| `effort.estimated_duration` | `str` | `None` is silently skipped |
| `retrieved_examples` | `list[dict]` | `st.info("No retrieved examples returned.")` |
| `recommended_directors` | `list[dict]` | `st.info("No recommended directors returned.")` |
| `risk_flags` | `list[dict \| str]` | `st.info("No risk flags returned.")` |
| `notes` | `str` | section omitted if falsy |

All list fields handle `None`, empty list, and non-list gracefully.

------------------------------------------------------------------------

## Current Limitations

-   **File upload is disabled.** RFP document parsing (PDF / DOCX) is
    not yet connected. Users must paste RFP text manually. This is a
    Role 5 dependency.

-   **Territory and service domain are not passed to the backend.** The
    dropdowns are UI context only. Jai's assignment logic does not yet
    accept these as inputs.

-   **Director recommendations use mock/heuristic data.** When
    `director_df` is not passed to `generate_assignment_context()`, the
    engine returns a single mock "Director A" record. Real capacity data
    from the dashboard's `capacity_df` is not yet wired into the RFP
    engine call. This is the next integration step.

-   **Similarity scores are local fallback scores.** The
    `similarity_score` values come from the deterministic local
    embedding, not Azure OpenAI embeddings. Scores are relative rankings
    within the fallback corpus, not absolute semantic similarity values.

-   **The historical corpus is synthetic.** When
    `proposals_responses.json` is not available locally, the engine
    falls back to a small built-in sample RFP text. All retrieved
    examples in this case come from that single sample document.

------------------------------------------------------------------------

## Week 3 Integration Status

| Item | Status |
|------------------------------------|------------------------------------|
| RFP text input and Analyze button | Done |
| `generate_assignment_context()` wired to button | Done |
| All `assignment_context` fields displayed | Done |
| Empty / placeholder state | Done |
| Error / exception state | Done |
| Prototype / fallback labels | Done |
| `effort` displayed as "Estimated Effort" | Done |
| `similarity_score` formatted to 2 decimal places | Done |
| File upload (document parsing) | Pending — Role 5 (Jai) |
| Territory / service domain passed to backend | Pending — Role 5 (Jai) |
| Real director capacity data wired to RFP engine | Pending — requires `capacity_df` plumbing |
| Azure-backed retrieval | Pending — Role 3 (Lyken), blocked on API version / deployment name |

------------------------------------------------------------------------

## Validation

``` bash
python -m py_compile app/app.py
```

Passes with no errors. The RFP fallback pipeline tests also pass:

``` bash
python -m pytest tests/test_rfp_preprocessor.py tests/test_vector_store.py tests/test_rfp_engine.py
```

Expected: `18 passed` (confirmed in Yixiao's QA notes,
`docs/rfp_integration_qa.md`).

------------------------------------------------------------------------

## Related Documents

-   [`docs/rfp_pipeline.md`](rfp_pipeline.md) — RFP preprocessing and
    vector store architecture
-   [`docs/rfp_integration_qa.md`](rfp_integration_qa.md) — Yixiao's
    Week 3 integration QA notes, `assignment_context` contract, and
    smoke test results

# RFP Dashboard Integration Notes — Week 4 Update

## Owner: Freya

## Week 3 Status

The following records the Week 3 Streamlit RFP Assignment Tool page integration. It covers the page structure, the `assignment_context` field mapping, empty/error state handling, prototype labelling, and current limitations.

------------------------------------------------------------------------

## Page Structure

The RFP Assignment Tool is Page 2 in `app/app.py`. It is reached via the sidebar radio button labelled **"RFP Assignment Tool"**.

The page uses a two-column layout:

| Column | Contents |
|------------------------------------|------------------------------------|
| Left (input) | File upload, RFP text area, Territory / Service Domain dropdowns, Analyze RFP button |
| Right (results) | Prototype notice banner, then one section per `assignment_context` key |

The file upload widget accepts TXT, DOCX, and text-based PDF files and loads the extracted text into the RFP text area. Users can still paste or edit RFP text manually. The territory and service domain selectors are UI context only — they are not passed into backend scoring yet.

------------------------------------------------------------------------

## assignment_context Field Mapping

Every field from `generate_assignment_context()` is displayed. The table below lists each field and its UI treatment.

| `assignment_context` key | UI Section Header | Display Treatment |
|------------------------|------------------------|------------------------|
| `rfp_summary` | **RFP Summary** | `st.write()` — plain text |
| `effort.level` | **Estimated Effort** | Colour-coded badge (`effort-high`, `effort-medium`, `effort-low` CSS classes) |
| `effort.estimated_duration` | (under Estimated Effort) | `st.caption()` |
| `effort.reason` | (under Estimated Effort) | `st.write()` — plain text; falls back to `effort.rationale` |
| `retrieved_examples` | **Retrieved Supporting Examples** | One expandable entry per retrieved chunk, first expanded by default; shows proposal ID, chunk ID, match score, and `supporting_text` truncated at 320 chars |
| `recommended_directors` | **Recommended Directors** | One `st.expander()` per director, first expanded by default |
| ↳ `director_name` | Expander title | Text |
| ↳ `capacity_label` | Inside expander | Bold label |
| ↳ `capacity_score` | Inside expander | Rounded numeric, 2 decimal places |
| ↳ `relative_load` | Inside expander | Rounded numeric, 2 decimal places plus `x` |
| ↳ `assignment_score` | Inside expander | Rounded numeric, 2 decimal places |
| ↳ `match_reason` | Inside expander | `st.write()` |
| ↳ `capacity_explanation` | Inside expander | `st.write()` under bold sub-header |
| ↳ `experience_match_explanation` | Inside expander | `st.write()` under bold sub-header |
| ↳ `supporting_chunks` | Inside expander | `st.caption()` — comma-separated chunk IDs |
| `risk_flags` | **Risk Flags** | `st.error()` for High, `st.warning()` for Medium, `st.info()` for Low/Info; shows `level: message` |
| `notes` | **Notes** | `st.caption()` — shown only when non-empty; text varies by enrichment path (see Prototype Labels section) |

The backend key is `effort`, not `estimated_effort`. The dashboard displays it under the heading **"Estimated Effort"** as agreed with Yixiao (see `docs/rfp_assignment_integration_qa.md`, naming decision section).

The `similar_rfps` key is returned by the engine but is not separately displayed. It duplicates `retrieved_examples` in a different shape and was not required by the dashboard spec.

------------------------------------------------------------------------

## Empty / Placeholder State

When no analysis has been run (no `rfp_assignment_context` in session state), each results section shows a dashed placeholder box with a label indicating:

-   what will appear there
-   which `assignment_context` key feeds it (e.g. `generate_assignment_context() → effort`)

This makes it clear to reviewers that the sections are wired and waiting for backend output, not broken.

------------------------------------------------------------------------

## Error / API Failure State

If `generate_assignment_context()` raises an exception (for example, if a dependency import fails or retrieval throws unexpectedly), the error is caught and stored in `st.session_state["rfp_assignment_error"]`. The results column then shows an `st.error()` banner with the exception message and a suggestion to check project dependencies.

The session context is cleared on error so stale results are not shown alongside the error message.

The local fallback path (`rfp_engine.py` → `rfp_preprocessor.py` → `InMemoryVectorStore`) does not require Azure credentials and should not raise under normal conditions. If the error state fires, the likely cause is a missing package or an import failure, not an API timeout.

------------------------------------------------------------------------

## Prototype / Mock / Fallback Labels

Three visible labels distinguish prototype output from real results:

1.  **Top-of-page banner** (always shown on the RFP page, Week 4 update):

    Shows three labelled segments in one banner:

    -   Retrieval: active backend shown after analysis (Azure/Chroma or labelled local fallback)
    -   Capacity data: real director capacity scores when available
    -   Recommendations: prototype guidance only — not final CGI assignment decisions

2.  **Above results** (shown once analysis has run):

    -   If mock capacity data: `st.warning()` — "Prototype output — heuristic recommendations using synthetic mock capacity data."
    -   If real capacity data: `st.info()` — "Prototype output — capacity-aware recommendations using {source label}."
    -   Both variants include the retrieval caveat.

3.  **Risk flags section**: each flag uses severity-appropriate styling (`st.error()` / `st.warning()` / `st.info()`).

These labels satisfy the Week 4 requirement that the dashboard clearly mark which outputs are real API-backed, fallback, heuristic, or mock.

Week 5 usability refinement: the results view now also shows a separate LLM enrichment caption. This explicitly distinguishes retrieval mode from Azure OpenAI chat enrichment, so a local retrieval fallback does not imply that LLM enrichment failed.

------------------------------------------------------------------------

## Required Fields from Backend

The following `assignment_context` fields are load-bearing for the UI. If any are missing or wrongly typed, the section degrades gracefully (shows an info message or falls back to a default string) rather than crashing.

| Field | Required type | Graceful fallback |
|------------------------|------------------------|------------------------|
| `rfp_summary` | `str` | `"No summary returned."` |
| `effort` | `dict` | empty dict; badge shows "Unknown" |
| `effort.level` | `str` — one of Low / Medium / High | badge class defaults to plain `badge` |
| `effort.reason` | `str` | falls back to `effort.rationale`; `None` is silently skipped |
| `effort.estimated_duration` | `str` | `None` is silently skipped |
| `retrieved_examples` | `list[dict]` | `st.info("No retrieved examples returned.")` |
| `recommended_directors` | `list[dict]` | `st.info("No recommended directors returned.")` |
| `risk_flags` | `list[dict \| str]` | `st.info("No risk flags returned.")` |
| `notes` | `str` | section omitted if falsy |

All list fields handle `None`, empty list, and non-list gracefully.

------------------------------------------------------------------------

## Current Limitations

-   **File upload is enabled for text extraction.** TXT and DOCX are parsed directly. Text-based PDFs use `pypdf`; scanned image PDFs may return no readable text and should be pasted manually or OCR-processed outside the app.

-   **Territory and service domain are not passed to the backend.** The dropdowns are UI context only. Jai's assignment logic does not yet accept these as inputs.

-   **Director recommendations use mock/heuristic data when capacity data is unavailable.** When `director_df` is not passed to `generate_assignment_context()`, the engine returns a single mock "Director A" record. Real `capacity_df` is passed via `director_df=capacity_df` in the Streamlit flow.

-   **Similarity score source depends on retrieval mode.** Azure/Chroma results use Azure embedding + Chroma retrieval. Local fallback results use deterministic local embeddings. Scores are relative rankings within the active corpus, not absolute business confidence.

-   **The historical corpus uses local proposal data when available.** When `proposals_responses.json` is available locally, the engine uses the chunked local proposal corpus. If it is unavailable or cannot be parsed, the engine falls back to a small built-in sample RFP text and labels that sample-corpus status.

-   **Full-corpus Azure/Chroma rebuilds are guarded.** Azure/Chroma is wired through the RFP engine, but normal dashboard requests reuse an existing Chroma collection instead of rebuilding on every request. If Azure/Chroma config, optional dependencies, or a reusable store are unavailable, the UI uses labelled local fallback retrieval over the same active corpus. The UI uses client-facing wording such as: "Azure/Chroma retrieval was unavailable for this request. The system used local retrieval instead."

-   **Retrieved chunks do not prove director experience.** Proposal chunks can carry CRM opportunity linkage when CGI's `Json S-Num` / `rfp_alias` crosswalk is available. Linked `opportunity_owner` reflects CRM opportunity ownership/context, not proof that the owner personally wrote the proposal or delivered the work. When retrieved examples lack linkage, the UI reports that they should be interpreted as semantic evidence only.

------------------------------------------------------------------------

## Week 4 Update - Integration Status

| Item | Status |
|----------------------------------------|--------------------------------|
| RFP text input and Analyze button | Done |
| `generate_assignment_context()` wired to button | Done |
| All `assignment_context` fields displayed | Done |
| Empty / placeholder state | Done |
| Error / exception state | Done |
| Prototype / fallback / heuristic labels | Done — Week 4 banner updated |
| Risk flag severity styling (High/Medium/Low) | Done — Week 4 |
| Upload/paste workflow caption | Done — Week 4; refined after upload support |
| Header subtitle updated for final prototype scope | Done |
| `effort` displayed as "Estimated Effort" | Done |
| `similarity_score` formatted to 2 decimal places | Done |
| Real `capacity_df` passed to RFP engine | Done — Week 4 (`director_df=capacity_df`) |
| Capacity source labelled in results view | Done — Week 4 |
| `azure_chat_available()` and `chat_completion()` in `azure_client.py` | Done — Week 4 |
| LLM enrichment path in `rfp_engine.py` (`_chat_fn=_AUTO`) | Done — Week 4 |
| Heuristic fallback when LLM unavailable / fails | Done — Week 4 |
| LLM failure Low risk flag | Done — Week 4 |
| `notes` field reflects LLM vs heuristic path | Done — Week 4 |
| Separate LLM enrichment status caption | Done — Week 5 usability refinement |
| Pasted RFP text used as query; historical/sample corpus chunked | Documented — Week 5 |
| Full local proposal corpus used when available | Done — Week 4 |
| Retrieval corpus/query status shown in UI | Done — Week 4 |
| Missing director/opportunity linkage caveat | Done — Week 4 |
| Azure/Chroma retrieval status shown when active; backend/smoke-test validation documented | Week 5 caveat added |
| File upload text extraction | Done — Week 4 for TXT, DOCX, and text-based PDF |
| Retrieved examples label changed to "Retrieved Supporting Examples" | Done — Week 5 usability refinement |
| Recommendation numeric values rounded for stakeholder display | Done — Week 5 usability refinement |
| LLM director match wording guarded against prior-experience overclaiming | Done — Week 5 usability refinement |
| Territory / service domain passed to backend | Pending — Role 5 (Jai) |

------------------------------------------------------------------------

## Validation

``` bash
python -m py_compile app/app.py
```

Passes with no errors. The RFP fallback pipeline tests also pass:

``` bash
python -m pytest tests/test_rfp_preprocessor.py tests/test_vector_store.py tests/test_rfp_engine.py
```

Current verification: `151 passed, 2 warnings`.

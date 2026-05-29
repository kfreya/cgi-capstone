# Week 4 Report Notes — Freya

**Role:** LLM Enrichment + RFP Output Quality Check + Dashboard Polish

------------------------------------------------------------------------

## 1. What Changed from Week 3

-   Header subtitle updated from "Week 3 Prototype" to "Week 4 Final
    Prototype".
-   RFP page top banner redesigned to show three explicitly labelled
    segments: Retrieval (fallback/heuristic), Capacity data (real when
    available), and Recommendations (prototype guidance only).
-   Real `capacity_df` is now passed into
    `generate_assignment_context()` via `director_df=capacity_df`. This
    was the highest-priority Week 4 integration fix. Director
    recommendations are now capacity-aware when live or pre-built
    capacity data is loaded.
-   The results area info box was consolidated. It now surfaces the
    capacity data source label and the retrieval caveat in a single
    line, reducing visual noise.
-   Risk flags now use severity-appropriate Streamlit components:
    `st.error()` for High, `st.warning()` for Medium, `st.info()` for
    Low/Info. Previously all flags used `st.warning()` regardless of
    severity.
-   A paste-only caption was added immediately below the disabled file
    upload widget to make it unambiguous that RFP text must be pasted,
    not uploaded.
-   `docs/rfp_dashboard_integration.md` updated from Week 3 to Week 4
    status, including corrected integration table and updated label
    documentation.
-   **Azure OpenAI chat enrichment implemented.**
    `generate_assignment_context()` now accepts a `_chat_fn` parameter
    (default `_AUTO`). When Azure chat is configured, the engine calls
    the chat deployment and uses LLM output to replace the heuristic
    `rfp_summary`, `effort` fields, and per-director `match_reason`.
    Heuristic output is used transparently when LLM is unavailable,
    raises, or returns malformed JSON. A Low risk flag is added when
    enrichment was attempted but failed. The `notes` field indicates
    whether LLM enrichment succeeded.
-   `azure_chat_available()` and `chat_completion()` added to
    `src/azure_client.py`. `chat_completion()` uses
    `AZURE_OPENAI_ENDPOINT` (the general endpoint) with
    `AZURE_OPENAI_CHAT_DEPLOYMENT`.
-   Test suite expanded: `test_rfp_engine.py` gains an `autouse`
    LLM-disable fixture (protecting all 12 existing tests) plus 7 new
    LLM path tests. `test_azure_client.py` gains 4 new chat tests. Full
    suite: 120 passed.

------------------------------------------------------------------------

## 2. Final Dashboard Structure

**Page 1 — Director Capacity Dashboard**

-   Loads capacity data in order: live from `cleaned_opportunity_df.csv`
    or `opportunity_df.csv`, then pre-built `director_capacity_df.csv`,
    then mock.
-   Displays KPI row, relative load bar chart, label mix donut chart,
    current vs historical load chart, workload trend chart, and director
    summary table.
-   Sidebar shows the active data source with a colour indicator.
-   Data source banner (green for real/pre-built, amber for mock) is
    shown at the top of the page body.
-   Filters: territory, owner, capacity label, status, sales stage, date
    range, opportunity type, sales model. Row-level filters require live
    opportunity data.

**Page 2 — RFP Assignment Tool**

-   Accepts pasted RFP text (file upload is disabled; paste-only
    workflow).
-   Calls
    `generate_assignment_context(rfp_text, director_df=capacity_df)`.
-   Displays: RFP summary, Estimated Effort (badge + duration + reason),
    Similar Historical RFPs (retrieved examples), Recommended Directors
    (expandable cards), Risk Flags (severity-styled), and Notes.
-   All sections degrade gracefully to info messages when fields are
    missing or empty.
-   Error state shows `st.error()` with the exception message if the
    engine raises.

------------------------------------------------------------------------

## 3. RFP Page Integration Notes

-   `generate_assignment_context()` is called with
    `director_df=capacity_df` where `capacity_df` is the dataframe
    already loaded by `load_data()` at app start.
-   If `capacity_df` is real or pre-built, the engine uses real capacity
    signals to rank and score recommended directors.
-   If `capacity_df` is mock (no real data found), the UI displays a
    `st.warning()` banner and the risk flags section will include a
    "mock director data" flag from the engine.
-   The capacity data source used at analysis time is stored in
    `st.session_state["rfp_capacity_data_source"]` so the label shown in
    the results view reflects the source at the time the button was
    clicked, not the current sidebar state.

------------------------------------------------------------------------

## 4. Capacity_df Integration Notes

| Scenario | Behaviour |
|----------------------------------|--------------------------------------|
| `cleaned_opportunity_df.csv` or `opportunity_df.csv` available | `capacity_df` computed live; passed into RFP engine; results use real capacity signals |
| `director_capacity_df.csv` available but no raw CSV | `capacity_df` loaded from pre-built file; passed into RFP engine |
| Neither available | `capacity_df` is mock (from `app/mock_data.py`); UI warns; risk flag fires |

The engine's `_director_records()` helper converts `capacity_df` (a
pandas DataFrame) to a list of dictionaries. Fields used for scoring:
`capacity_label`, `capacity_score`, `relative_load`. The director name
is read from `opportunity_owner` (the column name used by the capacity
engine).

------------------------------------------------------------------------

## 5. LLM / Heuristic Response Quality Review

The RFP engine now has two output paths: an LLM enrichment path (when
Azure chat is configured) and a deterministic heuristic fallback path.
Both paths produce the same `assignment_context` schema.

### rfp_summary

**Heuristic path** — generated by `_summarize_rfp_text()`:

-   Detects service area keywords and prepends "RFP appears to request
    {labels} support." Takes the first sentence of the cleaned input
    text.
-   **Assessment:** Appropriately hedged with "appears to request."
    Keyword detection is shallow (bag-of-words) but acceptable for a
    heuristic prototype.

**LLM path** — generated by `chat_completion()` with a structured JSON
prompt:

-   Requests a 2–3 sentence summary of what the RFP is asking for.
-   **Assessment:** More descriptive than the heuristic path. Should
    still be reviewed before use in stakeholder-facing contexts; LLM
    summaries are not validated against business requirements.

### effort estimate

**Heuristic path** — generated by `_effort_estimate()`:

-   Based on word count, service area count, complexity keyword hits,
    and best retrieval similarity score. Reason string names all inputs
    explicitly.
-   **Assessment:** Honest. The reason text states "Heuristic estimate
    based on RFP length (N words), service areas (X), complexity terms
    (Y), and retrieved examples (Z matches)." No overclaiming.

**LLM path** — generated by `chat_completion()`:

-   Requests `level` (Low / Medium / High), a 1–2 sentence `reason`, and
    an `estimated_duration` string. The `rationale` key is always set
    equal to `reason` to preserve backward compatibility with existing
    dashboard consumers.
-   **Assessment:** More contextual than the heuristic path but not
    calibrated against stakeholder-approved thresholds. Should be
    labelled as a prototype estimate.

### match_reason

**Heuristic path** — generated by `_match_reason()`:

-   States the capacity label, top similarity score (to 2 d.p.), and
    service keyword overlap score.
-   **Assessment:** Grounded in observable signals. No overclaiming.

**LLM path** — generated by `chat_completion()`:

-   Requests a 1–2 sentence explanation for each candidate director.
    Injected into the recommendation via `_inject_llm_match_reasons()`.
-   **Assessment:** More readable than the heuristic path. Not a
    validated staffing decision; must be labelled as prototype guidance.

### capacity_explanation

-   Not changed by LLM enrichment. Always generated by
    `_capacity_explanation()`.
-   States director name, label, capacity score, relative load, and adds
    "This is a heuristic input to the assignment score, not a final
    staffing decision."
-   **Assessment:** Honest. The caveat is explicit and appropriate.

### experience_match_explanation

-   Not changed by LLM enrichment. Always generated by
    `_experience_explanation()`.
-   States that experience fit is estimated from "retrieved
    historical/sample RFP chunks and simple service-keyword overlap
    ({score})."
-   **Assessment:** Honest. The word "sample" signals corpus type
    correctly.

### notes field

-   **Heuristic path, real corpus:**
    `"Prototype output for dashboard integration."`
-   **Heuristic path, sample corpus:** appends "Built-in sample
    historical corpus used because real historical proposal data was
    unavailable."
-   **LLM path, real corpus:**
    `"Prototype output enriched with Azure OpenAI chat   analysis. Retrieval remains local fallback."`
-   **LLM path, sample corpus:** appends the sample corpus caveat.
-   **Assessment:** All variants are clear and honest about enrichment
    and retrieval source.

------------------------------------------------------------------------

## 6. Unsupported Claim / Risky Wording Review

| Location | Text | Assessment |
|-------------------------|-----------------|-------------------------------|
| `_match_reason` | "retrieved historical examples" | Acceptable when real corpus is used; the risk flag clarifies when the sample corpus is used instead |
| `_summarize_rfp_text` | "RFP appears to request {labels} support" | Appropriately hedged with "appears to" |
| `_capacity_explanation` | "heuristic input to the assignment score, not a final staffing decision" | Correct caveat |
| Top-of-page banner | "Recommendations: prototype guidance only — not final CGI assignment decisions" | Correct |
| Results info box | "capacity-aware recommendations using {source label}" | Accurate when real capacity data is loaded |
| Results info box (mock) | "heuristic recommendations using synthetic mock capacity data" | Correct |
| `_notes` (sample corpus) | "Built-in sample historical corpus used" | Clear |
| `_notes` (LLM path) | "enriched with Azure OpenAI chat analysis. Retrieval remains local fallback." | Correct — explicitly notes retrieval is still heuristic |
| LLM match_reason | LLM-generated director rationale | Not a validated staffing decision; UI already labels output as prototype guidance |

**No unsupported claims were identified in the current engine output.**
All capacity scores, similarity scores, and keyword overlaps are
traceable to observable inputs. LLM-generated text is labelled as
prototype output in the `notes` field. The output does not claim
Azure-backed retrieval, validated historical proposals, exact
utilization, calendar availability, or business-approved ranking
weights.

------------------------------------------------------------------------

## 7. Response Quality Checklist

-   [x] `rfp_summary` uses hedged language in heuristic path ("appears
    to request")
-   [x] Effort estimate reason names its exact inputs (word count,
    service areas, complexity terms, retrieved examples) in heuristic
    path
-   [x] `match_reason` shows numeric signals (similarity score, keyword
    overlap) in heuristic path
-   [x] `capacity_explanation` includes explicit "not a final staffing
    decision" caveat (both paths)
-   [x] `experience_match_explanation` uses "sample" or
    "historical/sample" to signal corpus type (both paths)
-   [x] `notes` field flags when sample corpus is used (both paths)
-   [x] `notes` field indicates LLM enrichment when active
-   [x] Risk flags cover: sample corpus usage, low retrieval count, low
    similarity, missing capacity data, missing capacity fields,
    overextended directors, LLM enrichment failure
-   [x] High-severity risk flags shown with `st.error()`, Medium with
    `st.warning()`, Low/Info with `st.info()`
-   [x] Mock capacity data triggers a `st.warning()` banner in the
    results view
-   [x] RFP page top banner explicitly labels retrieval as
    fallback/heuristic
-   [x] LLM enrichment failure degrades silently to heuristic output
    with a Low risk flag
-   [x] Output does not imply Azure-backed retrieval
-   [x] Output does not imply business-validated or calibrated
    recommendations

------------------------------------------------------------------------

## 8. Empty State and Error State Notes

**Empty state (no analysis run yet):**

Each results section shows a dashed placeholder box labelled with what
will appear there and the `assignment_context` key that feeds it. This
confirms to reviewers that the sections are wired and waiting for
backend output, not missing or broken.

Placeholder sections: Estimated Effort, Similar Historical RFPs,
Recommended Directors, Risk Flags.

**Error state (engine raises an exception):**

The exception is caught and stored in
`st.session_state["rfp_assignment_error"]`. The results column shows an
`st.error()` banner with the exception message and a note that the local
fallback path should not fail under normal conditions.

The session context is cleared on error so stale results are not
displayed alongside the error banner.

**Empty input guard:**

If the Analyze RFP button is clicked with no text, the session context
is cleared and an `st.warning()` is shown: "Please paste RFP text before
running the analysis."

**Field-level graceful degradation:**

All `assignment_context` list fields (`retrieved_examples`,
`recommended_directors`, `risk_flags`) handle `None`, empty list, and
non-list values without raising. Missing string fields fall back to "No
X returned." Missing effort fields degrade to Unknown badge.

------------------------------------------------------------------------

## 9. Dashboard Limitations

-   File upload (PDF / DOCX parsing) is not yet connected. Current
    workflow is paste-only. This is a Role 5 (Jai) dependency.
-   Territory and service domain selectors are UI context only. They are
    not passed to the backend scoring logic.
-   Retrieval uses the local fallback path over a built-in sample corpus
    when `proposals_responses.json` is not available. All similarity
    scores in this case come from one small sample document.
-   Similarity scores are deterministic local scores (TF-IDF / token
    overlap), not Azure OpenAI embedding similarity. They are relative
    rankings within the fallback corpus only.
-   Director recommendations are ranked by a heuristic assignment score
    that combines capacity score, similarity signal, and keyword
    overlap. The weights are not calibrated against stakeholder-approved
    outcomes.
-   Azure OpenAI chat enrichment is now active when all chat environment
    variables are present. LLM-generated `rfp_summary`, `effort`, and
    `match_reason` values are prototype quality and should not be
    presented as validated business analysis.
-   The Azure + Chroma retrieval path has passed smoke testing but is
    not yet integrated into the Streamlit RFP flow. Retrieval remains
    local fallback even when LLM enrichment is active.

------------------------------------------------------------------------

## 10. UI Notes for Final Report

-   The dashboard uses a dark sidebar (#18181B) with CGI-red (#CC0000)
    branding.
-   Both pages share a header banner showing the current page title and
    the "Week 4 Final Prototype" subtitle.
-   The data source indicator in the sidebar uses green (real/pre-built)
    or amber (mock) dot labels.
-   The RFP page uses a two-column layout: input on the left, results on
    the right.
-   Recommended directors are shown as expandable cards; the first is
    open by default.
-   Risk flags use severity-appropriate Streamlit components for visual
    scanning: red box for High, yellow for Medium, blue for Low/Info.
-   The paste-only workflow is labelled with a caption directly below
    the disabled upload widget to prevent user confusion.
-   All prototype/fallback/heuristic labels are visible without
    expanding any accordions — they appear at the top of the results
    column before the first section header.

------------------------------------------------------------------------

## Related Documents

-   [`docs/rfp_dashboard_integration.md`](rfp_dashboard_integration.md)
    — RFP page field mapping, empty/error state, Week 4 integration
    status
-   [`docs/final_integration_qa.md`](final_integration_qa.md) — Yixiao's
    scope freeze, demo checklist, QA results, architecture compliance
-   [`docs/rfp_pipeline.md`](rfp_pipeline.md) — RFP preprocessing and
    vector store architecture
-   [`docs/rfp_assignment_integration_qa.md`](rfp_assignment_integration_qa.md)
    — `assignment_context` contract and smoke test results

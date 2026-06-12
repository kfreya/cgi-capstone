g# Final App QA and Scope Tracking

This document supports Issue #68, Sprint 5 / Week 5 Final App QA and Scope
Tracking. It is a companion to `docs/final_integration_qa.md`. The Week 4
document records final integration evidence, architecture status, smoke tests,
and scope-freeze notes. This Week 5 companion focuses on manual user-style QA,
issue/fix/decision tracking, CGI feedback tracking, teammate follow-up, and
final scope/caveat alignment.

Owner: Yixiao
Week 5 role: Final App QA & Scope Tracking

Week 5 is focused on user-style testing, issue fixes, CGI feedback tracking, and
final refinement. It is not focused on major new feature development. The app
should be described as a stakeholder-facing final prototype, not a production
staffing system.

This file should avoid duplicating long Week 4 evidence already covered in
`docs/final_integration_qa.md`; keep it focused on current testing status and
tracking.

## 1. Goal

Coordinate final prototype QA for Sprint 5 / Week 5 and keep the team aligned
on tested behavior, known issues, decisions, caveats, CGI feedback, and final
scope language.

Yixiao's responsibilities:

- Coordinate the manual test plan.
- Track issues, fixes, and decisions.
- Keep final scope and caveats aligned.
- Collect follow-up notes from teammates when available.

The final QA goal is to make sure the Director Capacity Dashboard and RFP
Assignment Tool are stable enough for stakeholder-facing demonstration, with
clear wording around prototype limits and decision-support use.

## 2. Current Test Environment

| Item | Current Value / Notes |
| --- | --- |
| Repository | `cgi-capstone` |
| Sprint / Week | Sprint 5 / Week 5 |
| Primary app surface | Streamlit stakeholder-facing final prototype |
| Main QA areas | Director Capacity Dashboard, RFP Assignment Tool, Azure / Chroma smoke-test status, final wording and caveats |
| Development focus | Final QA, fixes, feedback tracking, and refinement |
| Out of scope for Week 5 | Major new feature development or production staffing workflow claims |
| Data / recommendation caveat | Recommendations are decision-support outputs requiring stakeholder validation |
| Retrieval caveat | Retrieved examples are semantic evidence, not proof of director involvement |
| Azure caveat | Azure embeddings and Azure + Chroma retrieval are validated at smoke-test/sample level only, unless a later end-to-end Streamlit Azure path is explicitly implemented and tested |

## 3. Automated Test Baseline

Current automated test baseline:

```bash
python -m pytest
```

Result:

```text
151 passed, 2 warnings
```

Interpretation:

- The automated baseline is currently passing.
- The warnings do not fail the test suite.
- Passing tests support final prototype stability, but do not replace manual
  stakeholder-style QA.
- This baseline should be rerun after Week 5 fixes that affect app behavior,
  scoring, retrieval, data loading, or Streamlit display.
- `docs/final_integration_qa.md` may record an older Week 4 test result, while
  this document records the Week 5 baseline observed after the Yixiao branch was
  aligned with main.

## 4. Manual QA Checklist

Manual QA should focus on realistic stakeholder flows, wording, fallback states,
and whether the prototype avoids overclaiming. Mark `Actual Result`, `Status`,
and `Notes / Issue Link` as testing is completed.

### Director Capacity Dashboard QA

| Test ID | Area | Test Case | Steps | Expected Result | Actual Result | Status | Notes / Issue Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DCD-01 | App launch | Open the Streamlit app from the repository root | Start the app and navigate to the Director Capacity Dashboard | App loads without crash and the dashboard page is reachable | Pass - Streamlit app launched successfully; no traceback observed; Director Capacity Dashboard was reachable | Pass | Initial manual Streamlit QA |
| DCD-02 | Data loading | Confirm capacity data loads | Open dashboard and inspect initial data/status messages | Dashboard loads real or prepared capacity data, or clearly labels fallback/mock data if used | Pass - sidebar showed Scope: CGI Atlantic / Media Atlantic, Source: CRM opportunity records, and Computed CRM opportunity data | Pass | Initial manual Streamlit QA |
| DCD-03 | Capacity table | Confirm director-level capacity table renders | View the director capacity section | Director rows display with capacity labels and supporting workload fields | TBD | Not started |  |
| DCD-04 | Filtering | Test available dashboard filters | Change filters such as region, director, status, or visible options where available | Filters update dashboard outputs without errors or confusing empty states | TBD | Not started |  |
| DCD-05 | Empty state | Test filters that may produce no matching rows | Apply a narrow filter combination | App shows a clear empty state rather than crashing or showing stale results | TBD | Not started |  |
| DCD-06 | Wording | Check capacity wording | Review labels, captions, notes, and chart/table headings | Wording describes relative capacity signals, not exact working hours, utilization, or guaranteed availability | Pass - visible data-source wording used "Computed CRM opportunity data"; visible dashboard wording did not imply exact utilization or final assignment authority | Pass | Initial manual Streamlit QA |
| DCD-07 | Prototype scope | Check dashboard scope language | Review page text and report-style notes | App is presented as a stakeholder-facing final prototype, not a production staffing system | Pass - visible dashboard wording did not imply production-ready staffing or final assignment authority | Pass | Initial manual Streamlit QA |
| DCD-08 | Visual usability | Review table and chart readability | Inspect the dashboard on a standard laptop-sized viewport | Key values are readable, labels do not overlap, and layout supports stakeholder review | Pass - visible dashboard charts rendered: Relative Load by Director, Label Mix, and Current Load vs Historical Average; Label Mix showed 24 directors | Pass | Initial manual Streamlit QA; Director Summary table still covered by DCD-03 |
| DCD-09 | Error handling | Trigger or simulate missing/partial capacity fields where feasible | Load the dashboard with current data and inspect warning states | Missing or incomplete data is handled with clear caveats and no uncaught exception | TBD | Not started |  |
| DCD-10 | Cross-page consistency | Compare capacity labels used in dashboard and RFP recommendations | Review dashboard labels, then generate RFP recommendations | Capacity labels and caveats are consistent across dashboard and RFP page | TBD | Not started |  |

### RFP Assignment Tool QA

| Test ID | Area | Test Case | Steps | Expected Result | Actual Result | Status | Notes / Issue Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RFP-01 | Page access | Open RFP Assignment Tool page | Start the app and navigate to the RFP page | Page loads without crash and input controls are visible | Pass - RFP Assignment Tool page loaded without traceback; top banner showed computed CRM opportunity record capacity source and prototype guidance only, not final CGI assignment decisions; upload, paste-text, and result areas rendered | Pass | Initial page-load QA plus later final PDF-upload Analyze RFP smoke test |
| RFP-02 | Empty input | Submit empty or whitespace-only RFP text | Leave input blank and run analysis | App shows a clear warning and does not attempt retrieval or recommendation generation | TBD | Not started |  |
| RFP-03 | Pasted input | Submit representative RFP text | Paste sample RFP text and run analysis | App returns a structured assignment context with summary, effort estimate, semantic evidence, recommendations, and risk/caveat notes | Pass - three browser-tested pasted inputs ran without crash or traceback; summaries, estimated effort, Retrieved Supporting Examples, and Recommended Directors rendered | Pass | Interim assignment logic QA by Yixiao; cloud migration/managed services, cybersecurity/compliance, and vague short technology project samples |
| RFP-04 | Upload input | Test supported upload path if available | Upload supported TXT, DOCX, or text-based PDF file and run analysis | Text is extracted or a clear error is shown; scanned/OCR-only PDFs are not overclaimed as supported | Pass - final browser smoke test uploaded a text-based PDF after `pypdf` was available in the active environment; PDF text loaded successfully, the RFP summary rendered, and no traceback was observed | Pass | Active environment must include `pypdf` from `environment.yml` / `requirements.txt`; scanned/OCR-only PDFs remain out of scope unless separately tested |
| RFP-05 | Capacity-aware recommendations | Confirm capacity data is used when available | Run an RFP analysis while `capacity_df` is available | RFP recommendations are capacity-aware when `capacity_df` is available | Pass - app-facing RFP path passes `director_df=capacity_df` into `generate_assignment_context()` | Pass | See W5-008 |
| RFP-06 | Missing capacity fallback | Confirm behavior when capacity data is unavailable where feasible | Simulate or inspect fallback path if real capacity data cannot load | App labels fallback/mock director data clearly and avoids presenting outputs as final staffing guidance | TBD | Not started |  |
| RFP-07 | Recommendation wording | Review recommendation section | Inspect match reasons, ranking labels, and any explanatory notes | Recommendations are described as decision-support outputs requiring stakeholder validation | Pass - Recommended Directors rendered with capacity, capacity score, relative load, and assignment score; prototype/capacity-aware framing remained visible | Pass | Interim assignment logic QA by Yixiao |
| RFP-08 | Retrieval wording | Review retrieved examples section | Inspect headings and notes around retrieved examples | Retrieved examples are described as semantic evidence, not proof of director involvement or prior experience | Pass with caveat - Retrieved Supporting Examples rendered with match scores; wording stated retrieved chunks are semantic similarity evidence and not proof of prior director experience. Kian confirmed retrieved examples are semantic evidence only, not proof of director involvement or opportunity ownership; vague input evidence was weak/unclear because examples were broad or generic. | Pass with caveat | Interim assignment logic QA by Yixiao; Kian evidence/output review |
| RFP-09 | Azure wording | Review retrieval/Azure status shown in the RFP page | Run standard RFP page flow and inspect status text | The page does not claim the Streamlit RFP page is fully Azure-backed unless that exact path is implemented and tested | Pass with caveat - final local browser smoke test after the retrieval performance/stability fix displayed Azure/Chroma retrieval active, capacity-aware recommendations using Computed from CRM opportunity records, and the semantic-evidence caveat; earlier browser runs also validated local fallback wording | Pass with caveat | Local browser smoke test only; describe carefully and keep fallback/demo caveats |
| RFP-10 | Risk flags | Confirm risk/caveat display | Run an RFP analysis and inspect risk flags | Risk flags render clearly and include relevant caveats for fallback, data limits, missing linkage, or prototype status | Pass with caveat - risk flags and caveat wording appeared for missing director/opportunity linkage and short/vague input; semantic-evidence warning helped. Vague short input still produced confident-looking retrieved examples and recommendation output, so a stronger limited-input / low-detail warning may be useful. | Pass with caveat | See W5-013 and W5-014 |
| RFP-11 | Large input | Submit a long RFP-like text | Paste a longer sample and run analysis | App handles chunking and either completes or shows a clear non-crashing warning/fallback status | TBD | Not started |  |
| RFP-12 | Repeat analysis | Run two different RFP inputs in one session | Analyze sample A, then sample B | Results update for the new input and stale results are not mistaken for current analysis | Pass - three different pasted RFP inputs were run in one browser session and outputs updated without stale results | Pass | Interim assignment logic QA by Yixiao |

### Azure / Chroma Smoke-Test Status

| Test ID | Area | Test Case | Steps | Expected Result | Actual Result | Status | Notes / Issue Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AZ-01 | Environment | Confirm Azure environment variables are present where needed | Run the environment check used by the team, without printing secret values | Required variables are found or missing variables are clearly reported without exposing secrets | Pass - `python src/check_env.py` confirmed required Azure variables are readable locally; no secret or endpoint values recorded | Pass | Lyken Week 5 retrieval/config validation |
| AZ-02 | Azure embeddings | Run or review embedding smoke test | Execute the minimal embedding smoke test if credentials are available | Azure embeddings are validated only at smoke-test/sample level | Pass - minimal Azure embedding smoke test returned `ok=True`, `vectors=1`, `dim=1536` | Pass | Lyken Week 5 retrieval/config validation |
| AZ-03 | Chroma retrieval | Run or review Azure + Chroma smoke test | Execute sample Azure + Chroma smoke test if credentials are available | Sample chunks can be stored and queried; result is documented as smoke-test/sample validation only | Pass - Azure + Chroma sample retrieval returned `backend=azure_chroma`, `retrieval_mode=azure_chroma`, `preferred_path_ready=True`; full-corpus backend smoke test used 1216 proposal chunks and returned `retrieval_mode=azure_chroma`; `scripts/smoke_azure_chroma.py` returned `stored_chunks=3`, `query_result_count=2`, `first_result_mentions_cloud=True` | Pass | Backend smoke-test/sample/full-corpus validation only |
| AZ-04 | Streamlit claim boundary | Check Streamlit RFP page status wording | Run the RFP page and inspect retrieval status text | The app does not claim the Streamlit RFP page is fully Azure-backed unless a later end-to-end Streamlit Azure path is explicitly implemented and tested | Pass with caveat - final local browser smoke test showed Azure/Chroma retrieval active after the performance/stability fix, with computed CRM capacity source wording and no traceback; this verifies the local Streamlit UI path in the tested environment, not every deployment environment | Pass with caveat | Keep wording careful: Azure/Chroma browser path was smoke-tested locally; local fallback remains the safe path when Chroma/Azure dependencies or reusable store are unavailable |
| AZ-05 | Fallback status | Confirm fallback is clearly labelled | Trigger or inspect fallback/local retrieval status | Local fallback is labelled clearly and not presented as Azure + Chroma retrieval | Pass - local fallback path is preserved and retrieval status / notes distinguish fallback from `azure_chroma` | Pass | Lyken Week 5 retrieval/config validation |
| AZ-06 | Secrets safety | Inspect logs, UI, and docs for secret exposure | Run smoke checks and review displayed output | No API keys, endpoints, or secret values are exposed in UI, logs, screenshots, or docs | TBD | Not started |  |

## 5. Issue / Fix / Decision Tracking

Use this table to track Week 5 issues, fixes, decisions, and follow-up items.
Prefer linking GitHub issues, pull requests, commits, or notes when available.

| ID | Area | Issue or Observation | Severity | Owner | Status | Decision or Fix | PR / Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W5-001 | QA coordination | Create Week 5 final app QA and scope tracking companion document for Issue #68 | Medium | Yixiao | Completed | Established manual QA, scope, caveat, feedback, and teammate follow-up tracking structure | Issue #68 |
| W5-002 | Automated tests | Current automated baseline is passing: `151 passed, 2 warnings` | Low | Yixiao | Recorded | Use as the final Week 5 QA baseline after retrieval performance/stability and PDF dependency checks |  |
| W5-003 | Scope wording | Need consistent final prototype language across Week 5 report and app discussion | Medium | Yixiao / Team | Open | Describe app as stakeholder-facing final prototype, not production staffing system |  |
| W5-004 | RFP recommendation caveat | Recommendations must not be framed as authoritative assignment decisions | High | Yixiao / Jai | Open | Use decision-support wording requiring stakeholder validation |  |
| W5-005 | Retrieval caveat | Retrieved examples must not be framed as proof of a director's prior work | High | Yixiao / Lyken / Kian | Open | Describe retrieved examples as semantic evidence only |  |
| W5-006 | Azure claim boundary | Need to avoid claiming full Streamlit Azure-backed RFP flow unless later implemented and tested | High | Yixiao / Lyken | Open | State Azure embeddings and Azure + Chroma retrieval are smoke-test/sample-level validated only |  |
| W5-007 | CGI feedback | Capture final CGI questions, requested wording changes, and caveats | Medium | Yixiao | Open | Add feedback rows as received and track resolution before final report |  |
| W5-008 | RFP capacity integration | Week 5 QA reconfirmed that the Streamlit RFP Assignment Tool passes loaded capacity data into `generate_assignment_context()` | Medium | Yixiao | Pass | App-facing RFP path calls `generate_assignment_context(rfp_text, director_df=capacity_df)` and displays recommendation capacity source |  |
| W5-009 | Capacity source wording cleanup | The UI label "Live CRM capacity data" may imply a live production integration | Medium | Yixiao / Freya | Fixed | Fixed after post-PR #73 audit; replaced final-facing/app-facing "Live CRM" labels with "Computed from CRM opportunity records", "Computed CRM opportunity data", or "processed CRM-derived capacity data" wording |  |
| W5-010 | Pasted RFP chunking wording cleanup | Some app-facing and final-facing wording implied newly pasted RFP text is chunked before retrieval in the current Streamlit fallback path | High | Yixiao | Fixed | Fixed after post-PR #73 audit; updated wording to say pasted RFP text is used as a query against chunked historical/sample corpora; historical/sample corpus chunking is the active retrieval basis |  |
| W5-011 | Azure/Chroma full-integration wording cleanup | Some final-facing wording implied a fully Azure-backed Streamlit RFP flow | High | Yixiao / Lyken | Fixed | Fixed after post-PR #73 audit; softened wording to say Azure/Chroma retrieval status is shown when active and Azure embedding + Chroma retrieval are validated at smoke-test/sample level unless full Streamlit testing is documented |  |
| W5-012 | Retrieval / Config Validation | Lyken provided Week 5 retrieval/config validation notes | Medium | Lyken / Yixiao | Received | Use Lyken's results as backend retrieval/config evidence; keep caveat that full Streamlit UI path still needs browser confirmation if the final report claims end-to-end app verification |  |
| W5-013 | Assignment Logic Review | Jai PR #78 was merged into main with RFP assignment caveat/risk wording updates; Yixiao also completed interim user-style assignment logic QA for three RFP samples | Medium | Yixiao / Jai | Received / Merged | Use Jai's merged owner work as the assignment-logic follow-up. Yixiao's interim QA remains supporting evidence across cloud migration, cybersecurity/compliance, and vague short RFP inputs. Vague and broad-evidence limitations remain documented caveats rather than hidden blockers. | PR #78 |
| W5-014 | Evidence / Output Review | Kian completed RFP evidence review and confirmed semantic-evidence boundaries; one wording concern remained around "Relevant historical experience and available capacity." | Medium | Kian / Yixiao / Jai | Fixed | Use Kian's review as evidence/output validation; keep semantic-evidence caveat. The app-facing fallback phrase was softened to "Semantically similar historical context and available capacity signal." |  |
| W5-015 | RFP retrieval performance / stability | Streamlit RFP analysis was slow because Azure/Chroma could rebuild and re-embed the full corpus during Analyze RFP | High | Yixiao / Lyken | Fixed | Option B-lite fix: default interactive path reuses an existing Chroma collection, rebuild is opt-in via `RFP_REBUILD_CHROMA=1`, and local fallback remains safe when Chroma/Azure dependencies or reusable store are unavailable |  |
| W5-016 | Final RFP UI smoke test | Final local browser smoke test after the performance/stability fix covered PDF upload, text extraction, retrieval mode display, capacity-aware output, and summary rendering | High | Yixiao | Pass | Uploaded PDF text loaded successfully once `pypdf` was available; Azure/Chroma retrieval active was displayed; computed CRM capacity source and semantic-evidence caveat remained visible; no traceback observed and runtime was much faster |  |

### RFP Capacity Integration QA Finding

Status: Pass

Summary:

The Streamlit RFP Assignment Tool passes the loaded capacity dataframe into
`generate_assignment_context()`.

Evidence:

- `app/app.py` line 1280 calls
  `generate_assignment_context(rfp_text, director_df=capacity_df)`.
- `capacity_df` is loaded at module level in `app/app.py` around line 596.
- `load_data()` in `app/app.py` starts around line 533.
- Capacity source precedence:
  1. compute from processed opportunity data using `build_director_capacity_df()`
  2. load prebuilt `data/processed/director_capacity_df.csv`
  3. fall back to synthetic mock data from `make_director_capacity_df()`
- The RFP page maps capacity source labels around `app/app.py` line 1195:
  - `real`: Computed from CRM opportunity records
  - `prebuilt`: Pre-built `director_capacity_df.csv`
  - `mock`: Synthetic mock capacity data
- The RFP page stores the recommendation capacity source in session state around
  `app/app.py` line 1285.
- The RFP page displays the result source around `app/app.py` line 1345.
- Mock/fallback capacity data triggers a clear warning around `app/app.py` line
  1358.
- Non-mock data gets an info message around `app/app.py` line 1364.
- Recommended director output displays `capacity_label`, `capacity_score`, and
  `relative_load` around `app/app.py` line 1461.
- `src/rfp_engine.py` emits those capacity-aware fields around line 422 and uses
  capacity values in scoring around line 382.

Interpretation:

This reconfirms after the Yixiao branch was aligned with main that the
app-facing RFP path is capacity-aware when `capacity_df` is available.

Important caveat:

Capacity-aware means the assignment engine receives available capacity data and
can use capacity signals. It does not mean the recommendations are
business-validated final CGI staffing decisions.

## 6. Scope and Caveat Alignment

Use this table to keep final report, demo script, documentation, and app wording
aligned.

| Claim | Supported Status | Evidence | Safe Wording | Notes |
| --- | --- | --- | --- | --- |
| The app is ready for stakeholder-facing demonstration | Supported as prototype | Passing automated baseline and manual QA tracking | The app is a stakeholder-facing final prototype for review and discussion | Do not describe as production-ready |
| The app is a production staffing system | Not supported | No production validation, governance, integration, or stakeholder approval recorded | The app is not a production staffing system | Avoid production-readiness language |
| Director capacity outputs support workload review | Supported as prototype | Capacity dashboard and capacity scoring outputs | The dashboard provides relative capacity signals for stakeholder review | Avoid exact utilization or guaranteed availability claims |
| RFP recommendations use capacity data | Supported when `capacity_df` is available | Week 5 QA reconfirmed the app-facing RFP path passes `director_df=capacity_df` into `generate_assignment_context()` | RFP recommendations are capacity-aware when `capacity_df` is available | Capacity-aware means capacity signals are available to the assignment engine; recommendations still require stakeholder validation |
| RFP recommendations are final assignment decisions | Not supported | No stakeholder-approved assignment process or calibrated decision policy | Recommendations are decision-support outputs requiring stakeholder validation | Use in final report and demo wording |
| Retrieved examples show relevant prior material | Supported as semantic evidence | Retrieval returns similar chunks/examples; Kian reviewed cloud/managed services, cybersecurity/compliance, and vague/short RFP cases | Retrieved examples provide semantic evidence related to the RFP text | Do not claim proof of director involvement; evidence quality can be weak or broad for vague input |
| Retrieved examples prove a director's prior experience | Not supported | Proposal chunks do not provide reliable director involvement or opportunity ownership linkage; Kian's evidence review supports this boundary | Retrieved examples are semantic evidence, not proof of director prior experience, involvement, or opportunity ownership | Important final caveat |
| Azure embeddings are available for sample validation | Supported if smoke test passes in the configured environment | Azure embedding smoke-test/sample result | Azure embeddings are validated at smoke-test/sample level | Do not extend this to all Streamlit runs |
| Azure + Chroma retrieval is validated | Supported at backend smoke-test/sample/full-corpus level and local browser smoke-test level | Lyken confirmed Azure config readability, embedding smoke test, Azure + Chroma sample retrieval, full-corpus backend retrieval over 1216 proposal chunks, `scripts/smoke_azure_chroma.py`, retrieval mode reporting, and fallback preservation; final Yixiao local browser smoke test showed Azure/Chroma retrieval active after the performance/stability fix | Azure + Chroma retrieval is validated for backend smoke tests and for the local Streamlit UI environment tested in Week 5 | Preserve retrieved-example caveat: semantic evidence, not proof of director involvement; do not generalize to environments without Azure/Chroma config, `chromadb`, or a reusable store |
| Streamlit RFP page is fully Azure-backed | Partially supported only for the tested local smoke-test environment | Final local browser smoke test showed Azure/Chroma retrieval active for a PDF-upload RFP after the performance/stability fix | The Streamlit RFP page reports the retrieval mode used by the current run; the local Week 5 smoke test showed Azure/Chroma active | Do not claim all deployments or all demo environments are fully Azure-backed; local fallback remains supported |
| Local fallback retrieval can support prototype use | Supported as fallback behavior | Automated tests and app status/caveats | Local fallback retrieval supports prototype behavior when Azure/Chroma is unavailable or skipped | Must be labelled clearly |
| Text-based PDF upload is supported | Supported in final local browser smoke test when `pypdf` is installed | Final PDF upload smoke test loaded text successfully and rendered an RFP summary; dependency files include `pypdf` | Text-based PDF upload is supported when the active environment includes `pypdf` | Scanned/OCR-only PDFs may still require manual paste or OCR outside the app |
| Scanned PDF/OCR support is available | Not supported unless separately implemented and tested | Text-based extraction only is the known safe boundary | Scanned PDFs may require manual paste or OCR outside the app | Keep wording conservative |

## 7. CGI Feedback Tracking

Use this table for final CGI feedback, stakeholder questions, and action items.

| Date | Source | Feedback or Question | Area | Action Needed | Owner | Status | Resolution |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TBD | CGI | TBD | General | Record final feedback when received | Yixiao | Open |  |
| TBD | CGI | TBD | Director Capacity Dashboard | Confirm any wording or dashboard interpretation concerns | Yixiao / Freya | Open |  |
| TBD | CGI | TBD | RFP Assignment Tool | Confirm recommendation caveats and decision-support wording | Yixiao / Jai | Open |  |
| TBD | CGI | TBD | Retrieval / evidence | Confirm semantic evidence caveat is acceptable | Yixiao / Kian / Lyken | Open |  |
| TBD | CGI | TBD | Azure / Chroma | Confirm smoke-test/sample-level wording | Yixiao / Lyken | Open |  |

## 8. Teammate Follow-up Tracking

| Teammate | Follow-up Area | Requested Input | Owner | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Kian | Evidence & Output Review | Review retrieved example wording, output evidence language, and final report phrasing so semantic evidence is not overstated | Kian | Received / Integrated | Kian completed evidence/output review for cloud/managed services, cybersecurity/compliance, and vague/short RFP input. Kian confirmed retrieved examples are usable as semantic evidence but not proof of director involvement or opportunity ownership. |
| Lyken | Retrieval & Config Validation | Review retrieval mode wording, Azure/Chroma sample validation notes, and configuration caveats | Lyken | Received / Integrated | Retrieval/config validation checklist received and integrated. Azure config readability, embedding smoke test, Azure + Chroma sample retrieval, full-corpus backend retrieval, retrieval mode reporting, and fallback behavior validated. Final Yixiao browser smoke test later confirmed Azure/Chroma active status in the local Streamlit UI after the performance/stability fix; caveat remains that other environments may use local fallback if config/dependencies/store are unavailable. |
| Freya | Dashboard Usability & Wording | Review Director Capacity Dashboard usability, labels, empty states, and final prototype wording | Freya | Received / Merged | PR #73 was reviewed and merged; post-PR wording cleanup and verification were completed. Dashboard language should continue to avoid exact availability/utilization claims. |
| Jai | Assignment Logic Review | Review recommendation ranking, capacity-aware logic, risk flags, and decision-support caveats | Jai | Received / Merged | Jai PR #78 was merged into main and its RFP assignment caveat/risk wording updates are included after latest-main alignment. Yixiao's interim browser QA across cloud migration, cybersecurity/compliance, and vague short RFP inputs remains supporting evidence, not a replacement for Jai's owner work. Confirm recommendations require stakeholder validation. |

## 9. Week 5 QA Summary

Current summary:

- Automated baseline recorded: `python -m pytest` -> `151 passed, 2 warnings`.
- This Week 5 baseline may differ from the older Week 4 result recorded in
  `docs/final_integration_qa.md`; this file records the result observed after
  the Yixiao branch was aligned with main.
- Week 5 QA reconfirmed the Week 4 `capacity_df` integration after the Yixiao
  branch was aligned with main: the Streamlit RFP path passes
  `director_df=capacity_df` into `generate_assignment_context()`.
- Week 5 wording audit identified and cleaned up overclaiming risks around
  pasted RFP query handling, Azure/Chroma integration status, and capacity data
  source wording.
- Initial manual Streamlit QA passed for Dashboard page load, visible dashboard
  charts, safe computed-data wording, and initial RFP page load. The full
  pasted-input RFP analysis path was browser-tested with three sample inputs.
  Final UI smoke testing after the retrieval performance/stability fix also
  passed for PDF upload, text extraction, retrieval mode display, capacity-aware
  output, and RFP summary rendering.
- Lyken's retrieval/config validation notes were received: Azure config
  readability, embedding smoke test, Azure + Chroma sample/full-corpus backend
  retrieval, retrieval mode reporting, and fallback behavior passed. A final
  Yixiao local browser smoke test later showed Azure/Chroma retrieval active in
  the Streamlit RFP page after the performance/stability fix, with no traceback.
- After PR #73 merge and main alignment, a post-merge wording audit found some
  previous wording risks reappeared. These were cleaned up again on the latest
  main-aligned branch.
- Interim assignment logic QA passed for three browser-tested RFP inputs: cloud
  migration / managed services, cybersecurity / compliance, and a vague short
  technology request. Local fallback retrieval was shown in the browser for
  these runs, and no unsafe director-experience proof wording was observed.
  Caveat: vague input may benefit from a stronger low-detail warning.
- Kian's evidence/output review was received and integrated. Kian reviewed cloud
  / managed services, cybersecurity / compliance, and vague / short RFP cases
  and confirmed retrieved examples are useful as semantic evidence but cannot
  prove director/opportunity linkage. The app-facing fallback phrase Kian
  flagged was softened to "Semantically similar historical context and available
  capacity signal."
- Jai's assignment logic review was received through PR #78 and merged into
  main. Its RFP assignment caveat/risk wording updates are included after
  latest-main alignment; Yixiao's three-input interim browser QA remains
  supporting evidence.
- Teammate follow-up is being tracked but is not blocking Yixiao's Week 5 QA
  scope tracking. Lyken's retrieval/config notes, Freya's wording PR, and
  Kian's evidence/output review have been integrated, and Jai's assignment logic
  review is merged through PR #78.
- Final UI smoke test confirmed that `pypdf` must be installed in the active
  environment for PDF upload; with `pypdf` available, uploaded PDF text loaded,
  the RFP summary rendered, and the semantic-evidence caveat remained visible.
- Manual QA checklist is prepared for Director Capacity Dashboard, RFP
  Assignment Tool, and Azure / Chroma smoke-test status.
- Key claim boundaries are documented:
  - The app is a stakeholder-facing final prototype, not a production staffing
    system.
  - RFP recommendations are capacity-aware when `capacity_df` is available.
  - Azure embeddings and Azure + Chroma retrieval are validated at
    smoke-test/sample level and in the final local Streamlit browser smoke test;
    other environments may still use local fallback when config/dependencies or
    a reusable store are unavailable.
  - The Streamlit RFP page should report the retrieval mode used by the current
    run rather than be described as universally Azure-backed.
  - Retrieved examples are semantic evidence, not proof of director
    involvement.
  - Recommendations are decision-support outputs requiring stakeholder
    validation.

Final Week 5 QA summary is updated through the final local RFP UI smoke test
with PDF upload and Azure/Chroma active retrieval mode.

## 10. Week 5 Report Notes

Suggested safe report wording:

- During Week 5, the team focused on final app QA, issue fixes, CGI feedback
  tracking, and scope refinement rather than major new feature development.
- The app should be presented as a stakeholder-facing final prototype that
  supports review of director capacity signals and RFP assignment
  decision-support outputs.
- The current automated baseline is passing with `151 passed, 2 warnings` from
  `python -m pytest`.
- Manual QA should confirm that the Director Capacity Dashboard is usable,
  understandable, and appropriately caveated.
- Manual QA should confirm that the RFP Assignment Tool provides
  capacity-aware recommendations when `capacity_df` is available.
- RFP recommendations should be treated as decision-support outputs requiring
  stakeholder validation.
- Retrieved examples should be described as semantic evidence related to the
  RFP text, not proof of director involvement or prior experience.
- Azure embeddings and Azure + Chroma retrieval should be described as
  backend smoke-test validated and locally browser smoke-tested for the final
  Week 5 RFP UI run.
- The final report should not claim that every Streamlit RFP deployment is fully
  Azure-backed; the page reports the retrieval mode used by the current run and
  falls back locally when Azure/Chroma config, dependencies, or a reusable store
  are unavailable.

## 11. Week 6 Client Data Replacement QA

The Week 6 client-data replacement update keeps the opportunity preprocessing
workflow local and explicit. The opportunity cleaner now supports spreadsheet
input arguments for `--opps1-path`, `--opps2-path`, `--sheet-name`, and
`--output-dir`, while the no-argument command remains backward-compatible with
the existing demo filenames under `data/csv_files/` and outputs under
`data/processed/`.

CGI can pass local spreadsheet filenames directly in the preprocessing command
instead of renaming files or setting environment variables. The updated opps1
`Json S-Num` column is preserved as preprocessing-output fields `rfp_alias` and
`has_rfp_alias`; local validation found 19 non-empty `rfp_alias` rows. This is a
machine-readable linkage field for downstream review, not proof of director
ownership, prior experience, or assignment suitability.

This update does not change capacity scoring, dashboard metrics, RFP retrieval,
recommendation ranking, UI linkage display, or ownership/experience claims.
Excel orange highlighting is treated as visual-only context and is not used as
pipeline logic.

Validation results:

```text
python -m pytest tests/test_opportunity_cleaner.py -> 14 passed
python -m pytest -> 152 passed, 2 warnings
```

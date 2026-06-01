# RFP Week 4 Status

## Owner

Jai - Role 5

## Scope

Week 4 focused on validating the RFP Assignment Tool inside the Streamlit app and confirming that the final prototype can show Azure/Chroma retrieval, Azure OpenAI chat enrichment, live capacity data, director recommendations, risk flags, and prototype limitations clearly.

## Current Status

- The Streamlit RFP Assignment Tool page runs locally.
- The page accepts pasted RFP text and calls `generate_assignment_context()`.
- Azure/Chroma retrieval is integrated into the RFP analysis flow when the Azure configuration is available.
- Local fallback behavior is still preserved if Azure/Chroma is unavailable.
- Azure OpenAI chat enrichment is active for summary, effort estimate, and director match explanations when chat configuration is available.
- Live CRM capacity data is being used for director capacity signals when available.
- The output is dashboard-ready and includes summary, effort, similar historical RFPs, recommended directors, risk flags, notes, and retrieval status.

## Week 4 Checklist Confirmation

- Full `assignment_context` display is working as expected in the Streamlit RFP page.
- The page displays `rfp_summary`, `effort`, retrieved/similar historical RFP examples, recommended directors, risk flags, notes, and retrieval mode/status information.
- Azure/Chroma mode is visible after analysis. The page clearly shows when Azure/Chroma retrieval is active.
- The page is designed to show local fallback retrieval when Azure/Chroma is unavailable.
- Three main sample categories were tested: cloud migration / managed services, health/data roadmap, and vague or short RFP input.
- The tested inputs returned summary, effort estimate, similar historical RFPs, recommended directors, risk flags, and notes.
- LLM enrichment is fallback-safe. When Azure OpenAI chat succeeds, the summary, effort, and match reasons are enriched. When chat fails, the page still shows heuristic output and does not crash.
- Screenshots were captured during testing showing Azure/Chroma retrieval mode, live CRM capacity data, recommended directors, and risk flags.

## Week 4 RFP Safeguard Updates

- Added a low-confidence risk flag for very short RFP input.
- Added a limited-scope risk flag for short/vague RFP text that lacks service-domain detail.
- Added `service_solution` to the director capacity output as an owner-level service profile, allowing RFP recommendations to use a basic service-fit signal.
- Added a capacity-led ranking risk flag when RFP service keywords are present but service-domain overlap is unavailable or weak in the current director capacity records.
- Updated LLM-generated director match reasons so they are softened when director-domain fit is not validated by current data.
- Added logging for Azure OpenAI chat enrichment failures so the terminal/debug logs can show the actual exception while the Streamlit page still falls back safely.
- Focused tests passed after these changes: `52 passed` across `tests/test_capacity_engine.py` and `tests/test_rfp_engine.py`.

## Capacity Data Verification

- Confirmed in `app/app.py`: the app loads `capacity_df` once through `load_data()`.
- The Director Capacity Dashboard uses this `capacity_df` for its charts, tables, and capacity labels.
- The RFP Assignment Tool passes the same `capacity_df` into `generate_assignment_context(rfp_text, director_df=capacity_df)`.
- The RFP page labels the source as Live CRM capacity data when `_data_source` is `real`.
- Recommended directors display capacity label, capacity score, and relative load from the passed capacity table.
- The assignment score is capacity-aware because `src/rfp_engine.py` uses `capacity_score`, capacity label, retrieval similarity, and `service_solution` overlap when available.
- This confirms the RFP recommendations are using the same capacity data source as the dashboard, while still remaining prototype guidance.

## Director-to-RFP Linkage Check

The director rankings currently repeat across many RFP tests because the recommendation logic is mostly capacity-aware. This is not a coding bug; it reflects a data-linkage limitation.

Raw data checked:

- `data/raw_data/data/proposals_responses.json`
- `data/raw_data/data/csv_files/anonymized_opps_1.xlsx`
- `data/raw_data/data/csv_files/anonymized_opps_2.xlsx`

Findings:

- `proposals_responses.json` contains 19 historical proposal/RFP records.
- The CRM opportunity files contain 17,130 opportunity rows, 8,746 unique opportunity IDs, and 24 opportunity owners.
- Exact proposal-title matches to CRM opportunity names: 0.
- Fuzzy proposal-title matches to CRM opportunity names: 0.
- RFP/procurement code matches into CRM opportunity text: 0.
- Opportunity owner or manager names found in proposal text: 0.
- Existing chunk validation also shows 1,216 chunks with null `opportunity_owner` and null `opportunity_id`.

Conclusion:

- The current data does not provide a reliable link between retrieved proposal/RFP chunks and the director or CRM opportunity that worked on them.
- The tool can say that an input RFP is similar to historical proposal chunks.
- The tool can say that a recommended director has a current capacity signal from the CRM capacity table.
- The tool cannot honestly claim that a recommended director worked on the retrieved historical RFP unless CGI provides trusted linkage metadata.

Possible future improvement:

- The CRM opportunity files do contain `Service / solution` history by owner.
- A future heuristic could build an owner service-domain profile from CRM opportunity history and match RFP keywords to that profile.
- This would make rankings less repetitive, but it would still be a heuristic and would not prove that a director worked on a specific historical proposal.
- CGI should confirm whether `Opportunity owner` is the right field to treat as director experience before using this for stronger recommendations.

Suggested CGI wording:

> We confirmed that the current proposal/RFP corpus does not include reliable director or CRM opportunity linkage. The proposal chunks have proposal/document IDs, but not `opportunity_owner` or `opportunity_id`. We also could not match proposal titles or RFP numbers back to the anonymized CRM opportunity records.
>
> Because of that, the RFP Assignment Tool can retrieve similar historical proposal examples and combine them with current capacity signals, but it cannot yet prove that a recommended director worked on a similar past RFP.
>
> To improve recommendation quality, we would need a trusted crosswalk or metadata fields linking historical proposals to CRM opportunities and/or directors. Useful fields would include proposal/RFP ID, CRM opportunity ID, opportunity owner/director, contributing proposal leads or SMEs, service domain, client/sector, outcome, and date.
>
> Without that linkage, director recommendations should remain labelled as prototype guidance based on capacity and heuristic service fit, not validated historical experience.

## Latest Demo Test

Test input: cloud modernization / managed services sample RFP.

Result:

- Streamlit RFP page rendered successfully.
- Retrieval mode displayed as Azure/Chroma retrieval active.
- Capacity data displayed as Live CRM capacity data with 24 owners.
- Azure OpenAI chat enrichment produced the RFP summary, effort estimate, and director match reasons.
- Similar historical RFP chunks were returned from the default sample historical corpus.
- Recommended directors were shown with capacity score, relative load, assignment score, explanations, and supporting chunks.
- Risk flags correctly warned that retrieval evidence is still prototype/sample-corpus based until the full approved proposal corpus is indexed.
- Page did not crash during the test.

## Observed Output

- RFP summary described the request as a multi-year technology modernization program with Microsoft cloud advisory, Azure migration planning, data analytics, and managed services.
- Estimated effort was labelled High with an estimated duration of 12-18 months.
- Similar historical RFP chunks were returned from the `historical_sample` corpus.
- Recommended directors included Indira Foxworth, Cameron Foxworth, and Jordan Jameson.
- Notes confirmed that the output was enriched with Azure OpenAI chat analysis and that retrieval used Azure/Chroma.

## Additional Test Observation

Data analytics / reporting modernization RFP test:

- Azure/Chroma retrieval ran and returned similar historical chunks from the `historical_sample` corpus.
- The same top directors appeared again because the current recommendation logic is still mostly capacity-aware.
- Azure OpenAI chat enrichment was attempted but failed for this run, so the app showed the heuristic summary, effort estimate, and director match reasons instead.
- This is expected fallback behavior: the page did not crash, and the output remained usable.
- The exact chat failure reason is not visible in the Streamlit output because `generate_assignment_context()` catches chat errors and safely falls back to heuristic output.
- Likely causes include a temporary Azure chat API issue, deployment/endpoint mismatch, response parsing failure, or the chat model returning output that did not match the expected JSON format.

Health data roadmap RFP test:

- Azure/Chroma retrieval was active.
- Azure OpenAI chat enrichment succeeded and produced a clean RFP summary, High effort estimate, 4-6 month estimated duration, and director match reasons.
- Similar historical chunks were retrieved from the default `historical_sample` corpus.
- The same top directors appeared again because the ranking is still mostly capacity-aware.
- Director explanations were more polished because chat enrichment succeeded, but service-domain overlap was unavailable with the current capacity records.
- This shows that the prototype can generate useful explanation text, but true director-to-domain experience mapping is still limited.
- Risk flags correctly warned about sample-corpus retrieval, missing/default capacity fields, and overextended candidates.

Agile delivery / digital transformation resources RFP test:

- Azure/Chroma retrieval was active and returned three similar chunks from the default `historical_sample` corpus.
- Azure OpenAI chat enrichment was attempted but failed, so the app used the heuristic RFP summary, effort estimate, and match reasons.
- Estimated effort was labelled Medium with an estimated duration of 3-5 weeks.
- The same top directors appeared again because the current recommendation logic is still mostly capacity-aware.
- Service-domain overlap was unavailable with the current capacity records, so the experience match explanation stayed generic.
- Risk flags correctly showed sample-corpus retrieval, missing/default capacity fields, overextended candidate warning, and chat-enrichment fallback.

Microsoft Centre of Excellence / cloud advisory RFP test:

- Azure/Chroma retrieval was active and returned three similar chunks from the default `historical_sample` corpus.
- Azure OpenAI chat enrichment was attempted but failed, so the app used the heuristic RFP summary, effort estimate, and match reasons.
- Estimated effort was labelled Medium with an estimated duration of 3-5 weeks.
- Retrieved chunks included technical architecture, Microsoft tool/access, and scope-of-work related evidence.
- The same top directors appeared again because the current recommendation logic is still mostly capacity-aware.
- Service-domain overlap was unavailable with the current capacity records, so the director experience explanations remained generic.
- Risk flags correctly showed sample-corpus retrieval, missing/default capacity fields, overextended candidate warning, and chat-enrichment fallback.

Empty input failure-state test:

- Clicking Analyze RFP with no pasted RFP text did not crash the page.
- The app did not call the assignment pipeline or produce fake recommendations.
- Placeholder panels remained visible for effort, similar historical RFPs, recommended directors, and risk flags.
- The page displayed a clear warning: "Please paste RFP text before running the analysis."
- This confirms the empty-input guard is working correctly.

Short input failure-state test:

- Test input was only: "Need IT help."
- The page did not crash and still returned a structured assignment context.
- Azure/Chroma retrieval remained active, but similarity scores were lower than the fuller RFP tests.
- The summary correctly identified that the request lacked specific details or scope.
- Estimated effort was labelled Low with an estimated duration of 1-2 weeks.
- This confirms the app can handle very short input, but the output should be treated as low-confidence because the RFP text does not provide enough detail.

Vague RFP failure-state test:

- Test input described a general need for a technology services vendor but did not include a detailed scope.
- Azure/Chroma retrieval remained active and returned similar chunks from the default `historical_sample` corpus.
- Azure OpenAI chat enrichment succeeded and produced a readable summary, effort estimate, and director match reasons.
- Estimated effort was labelled Medium with an estimated duration of 3-5 weeks.
- The summary correctly noted that additional details would be shared later.
- The same top directors appeared again because the current ranking is still mostly capacity-aware.
- Service-domain overlap was unavailable with the current capacity records, so the experience match evidence stayed weak even though the LLM-generated wording sounded polished.
- This confirms the app can handle vague input, but the recommendations should be treated cautiously because the source text does not contain enough detail for strong matching.

Missing-scope / administrative RFP failure-state test:

- Test input included general proposal instructions such as company background, team qualifications, pricing, and references, but did not include a clear technical scope of work.
- Azure/Chroma retrieval remained active and returned similar chunks from the default `historical_sample` corpus.
- Retrieved evidence leaned toward administrative/proposal-response sections, including cover letter, contact, pricing, and fee schedule language.
- Azure OpenAI chat enrichment succeeded and produced a readable summary, Medium effort estimate, 2-4 week estimated duration, and director match reasons.
- The same top directors appeared again because the current ranking is still mostly capacity-aware.
- Service-domain overlap was unavailable with the current capacity records.
- This confirms the app can handle incomplete procurement-style text, but the resulting recommendations should be treated as low-confidence.

Administrative-only RFP failure-state test:

- Test input included submission deadline, electronic submission instructions, question deadline, pricing validity, and cancellation language, but no technical service scope.
- Azure/Chroma retrieval remained active and returned similar chunks from the default `historical_sample` corpus.
- Retrieved evidence focused on administrative/procurement sections, including closing deadline, fee schedule, pricing, and confidentiality language.
- Azure OpenAI chat enrichment succeeded and produced a readable summary, Medium effort estimate, 3-5 week estimated duration, and director match reasons.
- The same top directors appeared again because the current ranking is still mostly capacity-aware.
- Service-domain overlap was unavailable with the current capacity records.
- This confirms the app can process administrative-only RFP text, but the recommendations should not be treated as strong assignment guidance.

Contradictory / unrealistic scope failure-state test:

- Test input combined cybersecurity operations, court case management replacement, Salesforce implementation, health data governance, and Microsoft cloud migration into one request.
- The input also required completion in two weeks with no access to current systems or stakeholders.
- Azure/Chroma retrieval remained active and returned similar chunks from the default `historical_sample` corpus.
- Azure OpenAI chat enrichment succeeded and produced a clear summary that captured the broad, conflicting scope.
- Estimated effort was labelled High, and the duration reflected the two-week timeline stated in the RFP.
- The explanation correctly noted that the scope is extensive and the timeline is extremely tight.
- The same top directors appeared again because the current ranking is still mostly capacity-aware.
- Service-domain overlap was unavailable with the current capacity records, so director-domain matching is still weak even though the LLM-generated explanations mention specific domains.
- This confirms the app can handle contradictory or unrealistic input without crashing, but the output should be treated as a stress-test result rather than a realistic assignment recommendation.

Non-RFP text failure-state test:

- Test input was a short internal-style message asking someone to review dashboard numbers and update chart colors before a meeting.
- Azure/Chroma retrieval remained active and returned similar chunks from the default `historical_sample` corpus.
- Similarity scores were lower than the fuller RFP tests, which is expected because the input was not a real RFP.
- Azure OpenAI chat enrichment succeeded and produced a concise summary and Low effort estimate.
- Estimated duration was 1-2 days, matching the small task-like nature of the input.
- The same top directors appeared again because the current ranking is still mostly capacity-aware.
- Service-domain overlap was unavailable with the current capacity records, so the director match evidence stayed weak.
- This confirms the app does not crash on non-RFP text, but it can still produce recommendations even when the input is outside the intended workflow.

Random symbols / keyword-only failure-state test:

- Test input contained random symbols, numbers, and a small set of keywords such as Azure, cloud, dashboard, privacy, and security.
- Azure/Chroma retrieval remained active and returned similar chunks from the default `historical_sample` corpus.
- Similarity scores were lower than fuller RFP tests, which is expected because the input lacked real RFP structure and context.
- Azure OpenAI chat enrichment succeeded and inferred a plausible cloud dashboard/privacy/security scope from the limited keywords.
- Estimated effort was labelled Medium with an estimated duration of 4-6 weeks.
- The same top directors appeared again because the current ranking is still mostly capacity-aware.
- Service-domain overlap was unavailable with the current capacity records, so the director match evidence stayed weak.
- This confirms the app does not crash on noisy input, but keyword-only text can still lead to over-interpreted summaries and recommendations.

Very short keyword-heavy failure-state test:

- Test input contained only high-level service keywords such as cloud, cybersecurity, data analytics, managed services, privacy, and architecture.
- Azure/Chroma retrieval remained active and returned similar chunks from the default `historical_sample` corpus.
- Similarity scores were lower than fuller RFP tests, which is expected because the input had keywords but no actual RFP scope.
- Azure OpenAI chat enrichment succeeded and inferred a broad enterprise technology scope from the keywords.
- Estimated effort was labelled High with an estimated duration of 8-12 weeks because the keywords covered multiple complex domains.
- The same top directors appeared again because the current ranking is still mostly capacity-aware.
- Service-domain overlap was unavailable with the current capacity records, so the director match evidence stayed weak.
- This confirms the app can process very short keyword-heavy input, but keywords alone can make the output look more confident than the source text supports.

## Risk Flags Shown

- Azure/Chroma retrieval searched the default sample historical corpus, so retrieval evidence should be treated as a prototype signal until the full approved proposal corpus is indexed.
- Some directors may have no historical baseline, so capacity_score and relative_load
  use heuristic defaults in RFP ranking.
- At least one candidate director is overextended based on capacity signals and should be reviewed before assignment.
- Azure OpenAI chat enrichment may fail independently of Azure/Chroma retrieval. When this happens, the app falls back to heuristic summary, effort, and match reasons.

## Known Limitations

- File upload is enabled for TXT, DOCX, and text-based PDF extraction; scanned PDFs may still need manual paste/OCR.
- Territory and service domain dropdowns are UI context only and are not used by backend scoring yet.
- The retrieved historical examples currently come from the default sample corpus unless the full approved proposal corpus is indexed.
- Director-to-RFP history linkage is still limited, so recommendations remain prototype guidance rather than final staffing decisions.
- Some capacity fields may use defaults when the expected structured values are missing.
- The sidebar navigation between Director Capacity Dashboard and RFP Assignment Tool is occasionally finicky during RFP analysis. In some runs, clicking Analyze RFP causes the page to briefly reload or visually flash back toward the dashboard option, even though the RFP results still render. This appears to be a Streamlit UI/state refresh issue rather than an RFP backend failure.
- The pasted RFP text box can occasionally clear or appear empty after clicking Analyze RFP, even though the analysis results still render. This should be addressed so users can review or edit the submitted text after analysis.

## Week 4 Next Steps

- Test additional RFP inputs, including cybersecurity/privacy and short or vague RFP examples.
- Confirm stable fallback behavior when Azure/Chroma or chat enrichment is unavailable.
- Capture final screenshots for the report and presentation.
- Document that Azure/Chroma retrieval is active, but currently searching the default sample historical corpus.
- Keep prototype labels and risk flags visible so users do not over-trust the recommendations.
- Stabilize the Streamlit sidebar/page-selection state so Analyze RFP does not visually flash or appear to switch pages during reruns.
- Preserve pasted RFP text in the input box after analysis so the user can review or revise the submitted text.

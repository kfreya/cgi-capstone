# RFP Week 5 Status

## Current Focus

Week 5 is focused on final QA, user-style testing, and refinement of the RFP Assignment Tool rather than major new feature development.

Jai's focus area is assignment logic review:

- Test recommendation behavior with varied RFP inputs.
- Review risk flags and explanation quality.
- Check that retrieval mode, supporting examples, recommended directors, and notes are clear in the Streamlit page.
- Document remaining caveats before final CGI feedback.

## Current Retrieval Behavior

- Azure/Chroma retrieval is active when local Azure configuration is available.
- The RFP engine now loads the local `proposals_responses.json` corpus when available instead of only the small sample corpus.
- In the current local data, the proposal corpus preprocesses into roughly 1,216 chunks.

## Week 5 Caveat: Real-Corpus Indexing Performance

- Azure/Chroma real-corpus retrieval works, but first-run indexing can be slow because the app may rebuild the full proposal corpus inside the Streamlit request.
- When the user clicks **Analyze RFP**, the app can load the proposal JSON, preprocess chunks, generate Azure embeddings, rebuild/reset the Chroma collection, query Chroma, and optionally run Azure chat enrichment.
- This is much heavier than the earlier sample-corpus path and can make the Streamlit page appear stuck while the backend is still running.
- Recommended follow-up: cache or prebuild the Chroma index so the app reuses an existing proposal index instead of rebuilding it during every analysis click.

Test 1:
cloud/data modernization RFP: Passed. Azure/Chroma retrieval used the local proposals_responses.json corpus with 1,216 chunks, and Azure OpenAI chat enrichment produced the summary, effort estimate, and match wording. Output was coherent and caveated correctly. Retrieved examples were moderately relevant, though match scores were around 0.54-0.55. After PR #78, the overextended risk flag is framed as a broader-capacity-pool caveat rather than a claim that a displayed top-3 director is overextended.

Test 2:
cybersecurity RFP: Passed. Azure/Chroma retrieval used the local proposals_responses.json corpus and returned highly relevant cybersecurity/MDR examples, with stronger match scores around 0.58-0.61. Azure OpenAI chat enrichment produced a reasonable summary and high effort estimate. Director recommendations remained capacity-led, with the correct caveat that retrieved evidence does not prove prior director experience. After PR #78, the overextended risk flag is documented as a broader-capacity-pool caveat and should not be read as proof that a visible top-3 recommendation is overextended.

Test 3:
vague IT consulting input: Mostly passed. Azure/Chroma retrieval used the local proposal corpus and returned reasonable general IT consulting examples. LLM summary correctly recognized that details are limited. However, the output may overstate confidence: service keyword overlap showed 1.00 despite the input being vague, and the risk flags did not clearly call out missing scope/detail. Recommended follow-up: add or strengthen a vague-input risk flag and avoid treating broad terms like “IT consulting” as strong service-domain evidence.


Test 4, procurement/deadline-only input:
Passed. The tool correctly summarized the input as proposal submission instructions rather than a technical scope. Azure/Chroma retrieval returned procurement/timeline/pricing-related examples, and service-domain overlap was not calculated because no service keywords were detected. The limited-scope risk flag appeared as expected. Minor caveat: effort may be somewhat high for procurement-only text, and LLM director wording can still sound more specific than the available evidence supports.

Test 5, large multi-domain transformation RFP: 
Mostly passed. Azure/Chroma retrieval used the local proposal corpus and LLM enrichment produced a reasonable high-effort summary. Retrieved evidence was relevant, but all top 3 chunks came from the same Salesforce proposal even though the RFP covered multiple domains such as cloud, cybersecurity, data governance, managed services, and Salesforce. Recommended follow-up: add retrieval diversification so broad RFPs surface examples across multiple proposals or service areas instead of several chunks from one document.

Test 6: Nothing is passed to RFP box
Prompted to input text or upload a file.

Test 7, TXT upload workflow: 
The uploaded TXT file parsed correctly and populated the RFP text box. Azure/Chroma retrieval used the local proposals_responses.json corpus, and Azure OpenAI chat enrichment generated the summary, effort estimate, and director wording. Retrieved examples were generally relevant to managed services, operational support, service requests, and incident management. Minor caveat: effort may skew high for short managed-services inputs, depending on whether the tool interprets the work as ongoing support.

Fallback test: 
After temporarily disabling data/.env, the app switched to Local fallback retrieval active and still returned summary, effort, retrieved examples, recommended directors, risk flags, and notes without crashing. Azure OpenAI chat enrichment was disabled and heuristic output was shown instead. Processed CRM-derived capacity data still worked. Caveat: fallback similarity scores are not directly comparable to Azure/Chroma scores, and the risk flags could more explicitly mention that fallback mode was used.

## Proposal-to-CRM Crosswalk Check

To test whether retrieved proposal/RFP examples can be tied back to CRM owners, a local candidate crosswalk was generated at:

`data/processed/rfp_crm_crosswalk_candidates.csv`

Method used:

- Start with the proposal/RFP titles from `data/raw_data/data/proposals_responses.json`.
- Compare each title against CRM opportunity fields from `data/processed/cleaned_opportunity_df.csv`.
- Search for exact or near-exact identifiers such as RFP numbers, document numbers, and project codes.
- Compare remaining title/client/service words against CRM fields such as `opportunity_name`, `end_client_name`, and `service_solution`.
- Mark results as candidate-only because title/theme matching can be wrong without CGI confirmation.

Current finding:

- The proposal JSON has 19 top-level proposal/RFP entries.
- No strong automatic CRM match was found for most proposal/RFP entries.
- Some weak theme-based candidates appear, but they are not reliable enough to use as confirmed director-to-RFP evidence.
- This supports the current app caveat: retrieved chunks are semantic similarity evidence, not proof that a displayed director personally worked on the retrieved historical proposal.

Possible follow-up:

- Ask CGI whether they can provide or confirm a crosswalk with fields like `proposal_json_title`, `crm_opportunity_id`, `opportunity_name`, `opportunity_owner`, and `opportunity_manager`.
- Until then, any inferred proposal-to-CRM mapping should remain labelled as heuristic/candidate-only.

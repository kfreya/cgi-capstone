# RFP Evidence Output Review

Historical note: this document records an earlier validation stage. For the
current Week 6 handoff workflow, see docs/rfp_week6_status.md and
docs/README.md.

This note records the Week 5 evidence and output review for final app QA
consolidation. The focus is whether retrieved examples support displayed RFP
outputs, and whether wording stays within the current metadata limits.

## Review Setup

- Branch state: `Kian` merged with latest `origin/main` before review.
- Review command: `generate_assignment_context(..., _chat_fn=None)` for three
  sample RFP inputs.
- Retrieval mode observed: `local_fallback`; this depends on the local
  Azure/Chroma configuration and availability at review time.
- Corpus observed: local `proposals_responses.json` proposal corpus.
- Claim boundary: retrieved chunks are semantic evidence only. Current chunk
  metadata does not prove director experience or CRM opportunity ownership.

## Inputs Reviewed

- Cloud migration / managed services: "The client is seeking support for Azure
  cloud migration, application modernization, managed services transition,
  platform operations, and post-migration support for critical public-sector
  systems."
- Cybersecurity / compliance: "The client requires cybersecurity assessment,
  privacy compliance review, identity and access controls, risk remediation
  planning, and audit-ready security documentation."
- Vague or short RFP text: "Need implementation help for a technology project."

## Evidence Review Table

| Input | Retrieved examples | Evidence quality | Effort-estimate support | Weak/unclear cases | Suggested wording or risk flag |
|---|---|---|---|---|---|
| Cloud migration / managed services | `18_105668_sy_rfp_for_cybersecurity_operations_and_services__response__proposal_response_1__chunk_0063` (0.8438); `10_sr_18_fy26_microsoft_centre_of_excellence_partner__response__proposal_response_1__chunk_0007` (0.8277); `1_halifax_harbour_bridges_r2023_g_information_technology_consulting_services__response__proposal_response_1__chunk_0049` (0.8267) | Mixed. The summary correctly identifies cloud, managed services, and application support. Retrieved examples have high similarity scores, but the top example is from a cybersecurity proposal ID, so it should be manually reviewed before using as narrative evidence. | Medium effort (`3-5 weeks`) comes from detected service areas (`cloud`, `managed services`, `applications`) and complexity terms (`managed`, `migration`). The retrieved similarity scores are well above the low-similarity threshold, so retrieval did not increase the effort score; describe this estimate as heuristic rather than retrieval-proven. | Earlier output exposed the mock-director phrase "Relevant historical experience and available capacity"; this was misleading because metadata cannot prove a director personally worked on the retrieved RFP. The active wording has since been softened to "Semantically similar historical context and available capacity signal." The app also shows a risk flag saying retrieved chunks are semantic evidence, not proof of prior director experience. | Use: "retrieved semantically similar historical chunks." Keep risk flag: "Retrieved chunks cannot currently be tied reliably to a specific director or opportunity." Preserve the softened mock match-reason wording and semantic-evidence caveat for final demo/report language. |
| Cybersecurity / compliance | `5_salesforce_cxm_partner__proposal__chunk_0029` (0.9975); `6_managed_detection_and_response_rfp_8026125_26__proposal__chunk_0019` (0.9028); `4_courts_case_management_system__proposal__chunk_0056` (0.9028) | Mostly relevant. The summary identifies security support, and retrieved examples include security/compliance style proposal chunks with strong similarity scores. | Medium effort (`3-5 weeks`) comes from detected complexity terms (`privacy`, `security`), not from retrieved-example similarity. Because the input is only 19 words, the estimate should remain low-confidence and should not be treated as a validated delivery forecast. | Input is short, so the app correctly adds a low-confidence risk flag. Director match is still heuristic because no director/opportunity linkage exists in retrieved chunk metadata. | Keep short-input risk flag: "Input RFP text is very short, so summary, retrieval, and director recommendations should be treated as low confidence." Phrase evidence as semantic support only. |
| Vague or short RFP text | `8_rfsq_opot_it_resources__response__proposal_response_1__chunk_0002` (1.0000); `8_rfsq_opot_it_resources__response__proposal_response_1__chunk_0001` (1.0000); `8_rfsq_opot_it_resources__proposal__chunk_0008` (1.0000) | Weak/unclear. The output gives a generic summary and retrieves IT resource examples, but the input has too little scope detail to validate a strong match reason. | Low effort (`1-2 weeks`) is consistent with the very short 7-word input and no detected service/complexity terms. Retrieved examples do not strongly support a specific effort estimate because the input is underspecified and all top examples are from one proposal family. | All top examples came from the same proposal family (`8_rfsq_opot_it_resources`), so evidence diversity is weak. Top scores are high, but this likely reflects broad/generic wording rather than a specific RFP theme. The app correctly flags the input as very short and warns that recommendations are low confidence. | Add/keep risk flag: "Input RFP text is very short; confirm full scope before relying on recommendations." Suggested wording: "retrieval found broad IT implementation examples, but evidence is not specific enough for a strong recommendation." |

## Final Notes For Consolidation

- Retrieved examples are useful for semantic similarity checks, not for proving
  prior director experience.
- Match reasons should not say or imply that a named director personally worked
  on a retrieved RFP unless future metadata links chunks to validated
  director/opportunity records.
- Risk flags are present for missing director/opportunity linkage and for short
  or vague input text.
- Effort estimates are heuristic. Retrieved examples factor into effort only as
  a low-similarity novelty signal: they raise effort only when best similarity
  is below `0.20`. For these three inputs, retrieval did not increase the
  effort score, so retrieved examples do not validate delivery duration.
- LLM-enabled output should keep the same safety boundary: if match reasons are
  enriched, they still need to avoid implying personal director ownership unless
  the retrieved chunks have validated director/opportunity linkage.
- The previous mock-director wording concern has been addressed: the earlier
  phrase "Relevant historical experience and available capacity" has been
  softened to "Semantically similar historical context and available capacity
  signal." Keep the semantic-evidence boundary in final demo/report wording.
- For demo/report wording, use "retrieved semantically similar historical
  proposal/response chunks" rather than "proven director experience."

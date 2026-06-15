# Final UI Usability Review

Historical note: this document records an earlier validation stage. For the
current Week 6 handoff workflow, see docs/rfp_week6_status.md and
docs/README.md.

Date: June 2, 2026

This document records the first Week 5 stakeholder-style usability review of
the Director Capacity Dashboard and RFP Assignment Tool. The review used the
latest dashboard screenshots and focused on whether a CGI stakeholder could
understand the output without overinterpreting prototype, fallback, LLM, or
retrieval states.

## Review Scope

- Tested the RFP upload/paste workflow from a user perspective.
- Reviewed the final dashboard and RFP page screenshots for stakeholder
  clarity.
- Checked prototype, fallback, heuristic, LLM, and Azure/Chroma status wording.
- Reviewed risk flag wording and display.
- Checked whether recommendations overclaimed business validation,
  Azure-backed retrieval, or director experience.
- Identified wording and display refinements before final screenshot updates.

## Findings from Screenshot Review

### Capacity Dashboard

The Director Capacity Dashboard is understandable and reasonable for a
stakeholder demo. The page clearly shows that processed/computed CRM-derived
data is loaded, presents capacity labels and relative load prominently, and
includes an explanatory expander for relative load. The KPI cards,
relative-load chart, label mix, current-vs-historical comparison, trend chart,
and director summary table are appropriate for final prototype review.

No major wording changes were required on the capacity dashboard screenshot.

### RFP Assignment Tool

The RFP upload/paste workflow is understandable. The page clearly shows that a
PDF was uploaded, extracted text was loaded, and the user can still edit or
paste text manually.

The results page was broadly clear, but seven refinements were needed before
final screenshots:

1.  LLM-generated director match reasons could overclaim experience. Example
    wording such as "has extensive experience" was inconsistent with the
    linkage caveat because retrieved chunks do not prove that a recommended
    director worked on a historical proposal.
2.  The section label "Similar Historical RFPs" made retrieved chunks sound
    like full distinct RFPs. The output is more accurately described as
    retrieved supporting examples.
3.  The Azure/Chroma fallback caption was technically accurate but too
    implementation-heavy for stakeholders.
4.  The retrieval corpus caption said "pasted-RFP query chunks" even when the
    input came from an uploaded file.
5.  The linkage caveat used backend field names first
    (`opportunity_owner` / `opportunity_id`) rather than client-facing wording.
6.  Recommended director metrics showed too many decimals.
7.  Retrieval mode and LLM enrichment status could be confused. Local retrieval
    fallback does not mean Azure OpenAI chat enrichment failed.

## Changes Implemented

### Dashboard Wording

- Changed the results section header from **Similar Historical RFPs** to
  **Retrieved Supporting Examples**.
- Changed retrieved result labels from **similarity score** to **match score**.
- Changed "pasted-RFP query chunks" to "submitted RFP query text; historical/sample corpus chunks".
- Reworded the Azure/Chroma fallback caption:
  "Azure/Chroma retrieval was not used for this request. The system used local
  retrieval over the proposal corpus instead."
- Reworded the director/opportunity linkage caveat:
  "Retrieved chunks cannot currently be tied reliably to a specific director or
  opportunity. Treat them as semantic similarity evidence, not proof of prior
  director experience."

### LLM and Retrieval Status

- Added a separate LLM enrichment caption above the RFP results.
- When Azure OpenAI chat enrichment succeeds, the UI states that chat was used
  for the summary, effort estimate, and director match wording.
- When chat enrichment is not used, the UI states that heuristic summary,
  effort, and match wording are shown.
- This separates LLM enrichment status from retrieval mode, so local retrieval
  fallback is not mistaken for LLM fallback.

### Recommendation Display

- Rounded `capacity_score` to two decimals.
- Displayed `relative_load` with two decimals plus `x`.
- Rounded `assignment_score` to two decimals.
- Kept recommended directors in expandable cards, with the first card expanded
  by default.

### Recommendation Wording

- Updated LLM match-reason handling so director rationale is framed as
  prototype fit based on capacity, service-fit signals, and retrieved semantic
  evidence.
- Added a guard phrase stating that the recommendation does not prove prior
  director experience.
- Updated the LLM prompt to avoid claiming proven prior experience unless the
  provided data explicitly supports it.

## Remaining Prototype Caveats

- Retrieved chunks still cannot prove director experience because proposal
  chunks do not include reliable director/opportunity linkage.
- Azure/Chroma retrieval may fall back locally for large full-corpus requests
  until the retrieval indexing path is refined.
- `service_solution` is a lightweight service-fit signal, not a full expertise
  model.
- Capacity labels and recommendation weights still require CGI validation.
- Scanned PDFs may require manual paste or OCR.

## Screenshot Update Notes

After rerunning the app, final RFP screenshots should verify that:

- The retrieved examples section is titled **Retrieved Supporting Examples**.
- Retrieved examples show **match score** rather than **similarity score**.
- Retrieval captions use client-facing wording.
- The corpus caption says **submitted RFP query text; historical/sample corpus chunks**.
- The LLM enrichment caption appears separately from retrieval mode.
- Director cards show rounded metrics.
- LLM match reasons include the prototype-fit caveat and do not claim proven
  prior director experience.

## Handoff Notes

If future testing finds that recommendation fields need to change structurally,
share those issues with the team. Current changes are wording, display, and overclaim
prevention refinements rather than ranking-model changes.

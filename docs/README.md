# Documentation Map

This folder contains final handoff documentation, implementation notes, QA
evidence, and historical weekly records for the CGI Capacity Analyzer
prototype.

## Start here

- [Project README](../README.md) - repository overview, setup, common commands,
  data safety, and final prototype scope.
- [Architecture](architecture.md) - system architecture, data flow, scoring
  approach, RFP assignment flow, and prototype boundaries.
- [Final integration QA](final_integration_qa.md) - final prototype scope,
  supported claims, demo path, QA checklist, and caveats.

## Architecture and setup

- [Architecture](architecture.md) - canonical architecture and design notes.
- [Project README](../README.md) - setup, data folders, Streamlit entry point,
  preprocessing commands, tests, and data security.

## Client data replacement and handoff

- [Week 6 RFP status and handoff](rfp_week6_status.md) - client data
  replacement workflow, troubleshooting, data safety, RFP alias interpretation,
  and Chroma rebuild guidance.
- [Opportunity merge](opportunity_merge.md) - merge strategy for the two local
  opportunity spreadsheets.
- [Opportunity cleaning](opportunity_cleaning.md) - cleaned opportunity layer,
  prepared outputs, and local artifact boundaries.
- [Cleaned opportunity column dictionary](cleaned_opportunity_column_dictionary.md)
  - cleaned opportunity schema, including Week 6 alias fields.

## RFP Assignment Tool and linkage

- [RFP opportunity linkage implementation](rfp_opportunity_linkage_implementation.md)
  - Week 6 `Json S-Num` / `rfp_alias` linkage implementation and caveats.
- [RFP dashboard integration](rfp_dashboard_integration.md) - Streamlit RFP page
  contract, display behavior, fallback labels, and UI limitations.
- [RFP retrieval backend validation](rfp_retrieval_backend_validation.md) -
  Azure/Chroma validation, reuse-by-default behavior, explicit rebuild behavior,
  and local fallback.

## Capacity dashboard and scoring

- [Capacity scoring](capacity_scoring.md) - scoring workflow, formulas,
  assumptions, and non-claims.
- [Capacity engine integration](capacity_engine_integration.md) - integration
  contract and output artifacts for the capacity engine.

## QA / validation

- [Final integration QA](final_integration_qa.md) - final prototype QA and scope
  freeze.
- [Final app QA and scope tracking](final_app_qa_scope_tracking.md) - Week 5/6
  QA tracking, caveat alignment, and client-data replacement validation notes.

## Weekly reports and historical notes

- [Week 6 team report](time_management/week6_2026-06-14_team_report.pdf) -
  final Week 6 team report PDF.
- [Time management reports](time_management/) - weekly team reports and related
  project process artifacts.

## Historical / traceability notes

Historical weekly status notes and implementation notes remain in this folder
for traceability. When a historical note conflicts with current Week 6 handoff
behavior, prefer [Week 6 RFP status and handoff](rfp_week6_status.md),
[RFP opportunity linkage implementation](rfp_opportunity_linkage_implementation.md),
and this documentation map.

Older sprint or issue-specific notes are retained so reviewers can trace how
the prototype evolved. The canonical final handoff path starts with the root
[Project README](../README.md), this documentation map,
[Architecture](architecture.md), [Final integration QA](final_integration_qa.md),
and [Week 6 RFP status and handoff](rfp_week6_status.md).

# CGI Capacity Analyzer

UBC MDS Capstone 2025/2026 project in partnership with CGI Atlantic / Media Atlantic.

## Project Overview

CGI Capacity Analyzer is a stakeholder-facing capstone prototype for
understanding director capacity and supporting new RFP assignment discussions.
It surfaces useful workload, pipeline, retrieval, and recommendation signals for
leadership and delivery teams; it does not replace business judgment or CGI's
internal decision processes.

The prototype emphasizes transparency, reproducibility, and stakeholder review rather than fully automated decision-making.

The project has two core deliverables:

1. **Director Capacity Dashboard**
   Uses processed CRM-derived opportunity data to summarize director workload,
   historical baseline, relative load, capacity score, and capacity labels.

2. **RFP Assignment Tool**
   Accepts pasted RFP text or uploaded TXT, DOCX, and text-based PDF files.
   It supports effort estimation, semantic retrieval, capacity-aware
   director recommendations, optional Azure OpenAI chat enrichment, and
   fallback-safe prototype output.

## Repository Structure

```text
cgi-capstone/
├── app/
│   ├── README.md               # Streamlit app directory guide
│   ├── app.py                  # Streamlit integrated prototype dashboard
│   └── mock_data.py            # synthetic data for dashboard prototyping
├── src/
│   ├── README.md               # source module directory guide
│   ├── azure_client.py         # Azure/OpenAI chat and environment helpers
│   ├── azure_embedding_client.py # Azure embedding compatibility helpers
│   ├── azure_rag_client.py     # Azure/Chroma retrieval with local fallback
│   ├── check_env.py            # local environment variable check script
│   ├── data_loader.py          # local data loading helpers
│   ├── opportunity_cleaner.py  # opportunity Excel merge/cleaning pipeline
│   ├── data_validator.py       # validation summaries and owner aggregates
│   ├── capacity_engine.py      # capacity scoring and director output contract
│   ├── rfp_data_validator.py   # proposal/RFP data validation helpers
│   ├── rfp_engine.py           # dashboard-facing RFP assignment context
│   ├── rfp_evidence_validator.py # retrieved-evidence validation helpers
│   ├── rfp_preprocessor.py     # RFP/proposal text extraction and chunking
│   └── vector_store.py         # in-memory and Chroma vector retrieval helpers
├── tests/                      # unit tests for data, scoring, dashboard contracts, and RFP modules
├── config/
│   ├── README.md               # config directory guide
│   └── fallback_assumptions.yaml # shared fallback rules for validation/scoring
├── docs/
│   ├── architecture.md         # system architecture and modeling approach
│   ├── opportunity_merge.md    # opportunity Excel merge strategy and outputs
│   ├── opportunity_cleaning.md # cleaned opportunity layer and prepared artifacts
│   ├── cleaned_opportunity_column_dictionary.md # cleaned opportunity schema
│   ├── data_validation.md      # field validation findings and fallback notes
│   ├── scoring_input_reliability.md # scoring input reliability contract
│   ├── scoring_input_reliability_findings.md # detailed scoring input findings
│   ├── capacity_scoring.md     # capacity scoring workflow and assumptions
│   ├── capacity_engine_integration.md # capacity engine integration contract
│   ├── director_capacity_dashboard_column_dictionary.md # dashboard output schema
│   ├── dashboard_requirements.md # dashboard data and UI contracts
│   ├── rfp_pipeline.md         # RFP preprocessing and retrieval pipeline
│   ├── rfp_assignment_integration_qa.md # RFP assignment integration QA notes
│   ├── rfp_dashboard_integration.md # final RFP dashboard integration notes
│   ├── rfp_data_validation.md  # proposal/RFP data validation notes
│   ├── rfp_final_evidence_validation.md # final retrieval evidence validation
│   ├── final_integration_qa.md # final prototype QA and demo scope
│   ├── final_prototype_change_validation.md # final local changes and validation
│   ├── final_app_qa_scope_tracking.md # Week 5 final QA and scope tracking
│   ├── rfp_assignment_final_status.md # final RFP Assignment Tool status
│   ├── rfp_azure_chroma_retrieval_notes.md # Azure/Chroma retrieval notes
│   ├── rfp_retrieval_backend_validation.md # RFP retrieval backend validation
│   ├── team_charter.md         # team working agreement
│   └── time_management/        # weekly team report PDFs and time-management artifacts
├── scripts/                    # utility scripts for Chroma, validation, and evidence export
├── notebooks/                  # exploratory/historical EDA and validation notebooks
├── outputs/                    # tracked redacted validation/evidence artifacts
├── data/                       # local-only CGI data and generated outputs, ignored by Git
├── .streamlit/
│   └── config.toml             # Streamlit configuration
├── .env.example                # environment variable template, no secrets
├── environment.yml             # recommended conda environment
└── requirements.txt            # optional pip fallback
```

The `data/` directory is for local CGI-provided files and generated artifacts only. It is ignored by Git and must not be committed. The tracked `outputs/` directory contains intentionally committed redacted validation/evidence artifacts for handoff review.

## Documentation

Start with the [documentation map](docs/README.md) for the final handoff
reading order and historical note guidance.

Core technical documentation:

- [Architecture](docs/architecture.md)
- [Documentation map](docs/README.md)
- [Opportunity merge](docs/opportunity_merge.md)
- [Opportunity cleaning](docs/opportunity_cleaning.md)
- [Cleaned opportunity column dictionary](docs/cleaned_opportunity_column_dictionary.md)
- [Data validation](docs/data_validation.md)
- [Scoring input reliability](docs/scoring_input_reliability.md)
- [Scoring input reliability findings](docs/scoring_input_reliability_findings.md)
- [Capacity scoring](docs/capacity_scoring.md)
- [Capacity engine integration](docs/capacity_engine_integration.md)
- [Director capacity dashboard column dictionary](docs/director_capacity_dashboard_column_dictionary.md)
- [Dashboard requirements](docs/dashboard_requirements.md)
- [RFP pipeline](docs/rfp_pipeline.md)
- [RFP assignment integration QA](docs/rfp_assignment_integration_qa.md)
- [RFP dashboard integration](docs/rfp_dashboard_integration.md)
- [RFP data validation](docs/rfp_data_validation.md)
- [RFP final evidence validation](docs/rfp_final_evidence_validation.md)
- [RFP evidence output review](docs/rfp_evidence_output_review.md)
- [Week 6 RFP handoff/status](docs/rfp_week6_status.md)
- [RFP opportunity linkage implementation](docs/rfp_opportunity_linkage_implementation.md)
- [Azure/Chroma retrieval notes](docs/rfp_azure_chroma_retrieval_notes.md)
- [RFP retrieval backend validation](docs/rfp_retrieval_backend_validation.md)
- [Final integration QA](docs/final_integration_qa.md)
- [Final app QA and scope tracking](docs/final_app_qa_scope_tracking.md)
- [Final prototype change validation](docs/final_prototype_change_validation.md)
- [RFP Assignment Tool final status](docs/rfp_assignment_final_status.md)

Project process documentation:

- [Team charter](docs/team_charter.md)
- [Weekly reports and time management artifacts](docs/time_management/) (Week
  1 through Week 6, including the [Week 6 team report](docs/time_management/week6_2026-06-14_team_report.pdf))
- [Final report](docs/time_management/final_report_2026-06-24.pdf)

## Setup

Conda is the recommended setup path:

```bash
conda env create -f environment.yml
conda activate cgi-capstone
```

To update an existing environment after dependency changes:

```bash
conda env update -f environment.yml --prune
```

If conda is not available, use the optional pip fallback:

```bash
pip install -r requirements.txt
```

Dependency notes:

- `pypdf` is required for text-based PDF upload in the RFP Assignment Tool.
- `chromadb` is optional. It is needed for Azure/Chroma backend retrieval and
  smoke tests, but it is not required for the basic Streamlit demo because
  local fallback retrieval remains supported.

## Data Setup

Create the expected local data folders:

```bash
mkdir -p data/csv_files data/processed data/vector_store
```

Expected local files:

```text
data/.env
data/csv_files/anonymized_opps_1.xlsx
data/csv_files/anonymized_opps_2.xlsx
data/proposals_responses.json
```

The default no-argument preprocessing workflow reads the listed Excel filenames.
For CGI handoff, spreadsheet paths can also be supplied explicitly without
renaming local files.

Default preprocessing:

```bash
python -m src.opportunity_cleaner
```

Custom local spreadsheet preprocessing:

```bash
python -m src.opportunity_cleaner \
  --opps1-path data/csv_files/<opps1_file>.xlsx \
  --opps2-path data/csv_files/<opps2_file>.xlsx \
  --sheet-name Data \
  --output-dir data/processed
```

CGI spreadsheets, proposal JSON, credentials, and generated outputs must remain
local and should not be committed.

Generated local output folders:

```text
data/processed/
data/vector_store/
```

These files and folders are not committed. If you do not yet have a local `data/.env`, create a placeholder from the template and fill it in locally:

```bash
cp .env.example data/.env
```

## Common Commands

Check local environment variables:

```bash
python src/check_env.py
```

Build the merged opportunity dataset:

```bash
python -m src.opportunity_cleaner
```

Build the persistent RFP Chroma index when Azure configuration and optional
Chroma dependencies are available:

```bash
python scripts/build_rfp_chroma_index.py
```

Run the Streamlit app:

```bash
streamlit run app/app.py
```

Run all tests:

```bash
python -m pytest
```

Latest local validation:

```text
168 passed, 2 warnings
```

The warnings are existing pandas FutureWarning messages in capacity-engine
tests and do not affect the documentation-only packaging update.

Run selected validation suites:

```bash
python -m pytest tests/test_opportunity_cleaner.py
python -m pytest tests/test_capacity_engine.py
python -m pytest tests/test_rfp_engine.py tests/test_vector_store.py
```

## Demo-Safe Behavior

The Streamlit app is intended to run safely for stakeholder demonstration:

- Capacity views use processed/computed CRM-derived opportunity data when
  available.
- If processed data is unavailable, the app can fall back to prebuilt capacity
  output or synthetic mock data, clearly labelled in the UI.
- RFP retrieval uses Azure/Chroma only when Azure config, optional dependencies,
  and a reusable Chroma store are available.
- Local fallback retrieval remains supported when Azure/Chroma is unavailable.
- Set `RFP_REBUILD_CHROMA=1` only when an explicit Chroma rebuild is needed for
  backend validation or maintenance; normal interactive analysis does not
  rebuild Chroma on every request.
- To rebuild the reusable index outside the app, run
  `python scripts/build_rfp_chroma_index.py`. To force an explicit
  maintenance/debug rebuild through the Streamlit path, run
  `RFP_REBUILD_CHROMA=1 streamlit run app/app.py`.

## Final Prototype Status

This repository is a final stakeholder-facing capstone prototype. It is not a
production staffing system or a business-validated assignment system.

Week 1 established the project foundations:

- Opportunity merge pipeline for the two anonymized opportunity Excel workbooks.
- Validation notes and reusable helpers for field quality checks and owner-level aggregates.
- Initial capacity scoring, dashboard, RFP preprocessing, and vector retrieval module skeletons.

Week 2 moved the project toward an integrated capacity prototype:

- Opportunity cleaning now produces `cleaned_opportunity_df.csv` and
  `owner_base_summary.csv` as local prepared artifacts.
- Capacity scoring uses the shared opportunity outcome taxonomy and gates
  current load to open sales pipeline plus active won delivery commitments.
- The dashboard uses cleaned opportunity data when available, or raw
  `opportunity_df.csv` plus cleaning as a fallback.
- The initial RFP prototype provides preprocessing, chunking, sample historical
  retrieval, and a dashboard-compatible `generate_assignment_context()` output.

Week 3 moved the RFP Assignment Tool and documentation closer to an integrated demo:

- RFP data validation documented proposal/response structure, text quality,
  chunk metadata, representative sample chunk exports, and proposal-to-director
  linkage limitations.
- Local fallback retrieval remained available for demos and tests.
- `generate_assignment_context()` became more stable for Streamlit integration,
  with improved assignment logic, risk flags, and schema-oriented tests.

Final prototype capabilities:

- The RFP page accepts pasted input or uploaded TXT, DOCX, and text-based PDF
  files. Scanned PDFs may still require manual paste or OCR.
- The RFP engine loads the local `data/proposals_responses.json` corpus when
  available and uses the sample corpus only as fallback.
- Submitted RFP text is used as a query against a chunked historical/sample corpus.
- Azure OpenAI embeddings with Chroma are the preferred retrieval path when
  configured and a reusable store is available; local retrieval remains
  available as a fallback over the same corpus.
- Azure OpenAI chat enrichment can improve the RFP summary, effort estimate,
  and director match reasons when configured; heuristic output is used when
  chat enrichment is unavailable or fails.
- RFP recommendations are capacity-aware when `capacity_df` is available.
- Owner-level `service_solution` profiles from open/won opportunities provide
  a lightweight service-fit signal.
- When CGI's `Json S-Num` field is present in the local opps1 spreadsheet, the
  preprocessing pipeline preserves it as `json_s_num`, `rfp_alias`, and
  `has_rfp_alias`. This supports RFP-to-CRM traceability review.
- The dashboard labels retrieval mode, capacity source, prototype status, and
  risk flags.
- Retrieved proposal chunks are treated as supporting semantic/contextual
  evidence. Alias linkage can provide CRM opportunity traceability when
  available, but it does not prove director authorship, ownership, prior
  experience, or delivery responsibility.

Latest local validation:

```text
168 passed, 2 warnings
```

The warnings are existing pandas FutureWarning messages in capacity-engine
tests and do not affect the documentation-only packaging update.

## Limitations and Non-Claims

- The app is a stakeholder-facing final prototype, not a production staffing
  system.
- RFP recommendations are decision-support outputs and require stakeholder
  validation before use.
- Retrieved chunks are supporting evidence only; even when `rfp_alias` links a
  proposal to CRM opportunity context, the link does not establish historical
  director participation, authorship, ownership, prior experience, or delivery
  responsibility.
- Azure/Chroma retrieval is optional and backend-validated. The app reports the
  retrieval mode used by each run, reuses a Chroma collection when available,
  and can fall back locally when Azure config, optional Chroma dependencies, or
  a reusable collection are unavailable.
- Capacity results use processed CRM-derived data, not a live production CRM
  integration.

## Data Security

Never commit:

- `data/.env`
- CGI Excel files in `data/csv_files/`
- `data/proposals_responses.json`
- `data/processed/`
- `data/vector_store/`
- `chroma_db/`

Do not print or expose API keys, endpoints, secrets, or row-level CGI data. Generated data should be reproducible locally from code.

To check that no local data files are tracked, run:

```bash
git ls-files data
```

This should return no output.

## Acknowledgements and AI Use

The core project ideas, problem framing, system design, feature priorities, and final implementation decisions were developed through team discussion, weekly planning, mentor feedback, and partner feedback. The team maintained weekly work plans, progress notes, documentation, and validation records throughout the project to support transparent collaboration and decision-making.

ChatGPT was used as an auxiliary development and writing-support tool. Its use included code maintenance support, debugging assistance, documentation polishing, wording review, and clarification of implementation notes. The project concept, core functionality, system architecture, validation decisions, and final claims were created, reviewed, and approved by the human authors. All AI-assisted outputs were checked through human review, repository tests, manual QA, and the project documentation available under `docs/`.

We sincerely thank every team member for their effort throughout this project. As a team that experienced personnel changes, we worked through many coordination, technical, and communication challenges to bring the project to completion. We are also grateful to the UBC teaching team, especially our mentor Garrett, for guidance and for helping support communication between CGI and the student team. Finally, we thank CGI for providing continuous feedback, sharing a valuable real-world project opportunity, and allowing us to learn through practical problem solving. This project helped us better understand the technical, collaborative, and professional skills needed in applied data science work.

## Team

Freya Kan, Qian Yang, Junxian Lin, Yixiao Jing, Jai
UBC MDS Capstone 2025/2026

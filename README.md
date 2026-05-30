# CGI Capacity Analyzer

UBC MDS Capstone 2025/2026 project in partnership with CGI Atlantic / Media Atlantic.

## Project Overview

CGI Capacity Analyzer is a decision-support tool for understanding director capacity and supporting new RFP assignment decisions. It is intended to surface useful workload, pipeline, and retrieval signals for leadership and delivery teams; it does not replace business judgment or CGI's internal decision processes.

The prototype emphasizes transparency, reproducibility, and stakeholder review rather than fully automated decision-making.

The project has two core deliverables:

1. **Director Capacity Dashboard**  
   Uses CRM opportunity data to summarize director workload, historical baseline, relative load, capacity score, and capacity labels.

2. **RFP Assignment Tool**  
   Uses proposal/RFP text and structured opportunity data to support RFP effort estimation, similar RFP retrieval, and director recommendations.

## Repository Structure

```text
cgi-capstone/
├── app/
│   ├── app.py                  # Streamlit integrated prototype dashboard
│   └── mock_data.py            # synthetic data for dashboard prototyping
├── src/
│   ├── azure_client.py         # Azure/OpenAI environment validation helper
│   ├── check_env.py            # local environment variable check script
│   ├── data_loader.py          # local data loading helpers
│   ├── opportunity_cleaner.py  # opportunity Excel merge/cleaning pipeline
│   ├── data_validator.py       # validation summaries and owner aggregates
│   ├── capacity_engine.py      # capacity scoring and director output contract
│   ├── rfp_engine.py           # dashboard-facing RFP assignment context
│   ├── rfp_preprocessor.py     # RFP/proposal text extraction and chunking
│   └── vector_store.py         # in-memory and Chroma vector retrieval helpers
├── tests/                      # unit tests for data, scoring, dashboard contracts, and RFP modules
├── config/
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
│   ├── azure_embedding_vector_store_notes.md # Azure embedding/vector-store notes
│   ├── team_charter.md         # team working agreement
│   └── time_management/        # weekly team report PDFs and time-management artifacts
├── notebooks/                  # EDA and validation notebooks
├── data/                       # local-only CGI data and generated outputs, ignored by Git
├── .streamlit/
│   └── config.toml             # Streamlit configuration
├── .env.example                # environment variable template, no secrets
├── environment.yml             # recommended conda environment
└── requirements.txt            # optional pip fallback
```

The `data/` directory is for local CGI-provided files and generated artifacts only. It is ignored by Git and must not be committed.

## Documentation

Core technical documentation:

- [Architecture](docs/architecture.md)
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
- [Azure embedding and vector store notes](docs/azure_embedding_vector_store_notes.md)

Project process documentation:

- [Team charter](docs/team_charter.md)
- [Weekly reports and time management artifacts](docs/time_management/)

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

The Excel filenames should match the listed names exactly because the opportunity merge/cleaning pipeline reads from those expected paths.

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

Run the Streamlit app:

```bash
streamlit run app/app.py
```

Run all tests:

```bash
python -m pytest
```

Run selected validation suites:

```bash
python -m pytest tests/test_opportunity_cleaner.py
python -m pytest tests/test_capacity_engine.py
python -m pytest tests/test_rfp_engine.py tests/test_vector_store.py
```

## Week 3 Prototype Status

This repository is a Week 3 integrated capstone prototype. It is not a
production system.

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

- RFP data validation now documents proposal/response structure, text quality,
  chunk metadata, representative sample chunk exports, and proposal-to-director
  linkage limitations.
- Azure embedding and vector-store helper work is in place while local fallback
  retrieval remains available for demos and tests.
- `generate_assignment_context()` is more stable for Streamlit integration, with
  improved assignment logic, risk flags, and schema-oriented tests.
- RFP dashboard integration notes and QA documentation capture fallback,
  heuristic, mock, and real component boundaries.
- Documentation filenames and README links have been cleaned up around canonical,
  content-based documentation sources.

Full Azure-backed Chroma retrieval, production retrieval quality,
stakeholder-calibrated recommendation weights, and final demo polish remain
ongoing work.

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

## Team

Freya Kan, Qian Yang, Junxian Lin, Yixiao Jing, Jai  
UBC MDS Capstone 2025/2026

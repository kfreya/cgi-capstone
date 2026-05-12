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
│   ├── app.py                  # Week 1 Streamlit dashboard skeleton
│   └── mock_data.py            # synthetic data for dashboard prototyping
├── src/
│   ├── azure_client.py         # Azure/OpenAI environment validation helper
│   ├── check_env.py            # local environment variable check script
│   ├── data_loader.py          # local data loading helpers
│   ├── opportunity_cleaner.py  # opportunity Excel merge/cleaning pipeline
│   ├── data_validator.py       # validation summaries and owner aggregates
│   ├── capacity_engine.py      # first-pass capacity scoring functions
│   ├── rfp_preprocessor.py     # RFP/proposal text extraction and chunking
│   └── vector_store.py         # in-memory and Chroma vector retrieval helpers
├── tests/                      # unit tests for Week 1 src modules
├── config/
│   └── fallback_assumptions.yaml # shared fallback rules for validation/scoring
├── docs/
│   ├── architecture.md         # system architecture and modeling approach
│   ├── opportunity_merge.md    # opportunity Excel merge strategy and outputs
│   ├── data_validation.md      # field validation findings and fallback notes
│   ├── capacity_scoring.md     # capacity scoring workflow and assumptions
│   ├── dashboard_requirements.md # dashboard data and UI contracts
│   ├── rfp_pipeline.md         # RFP preprocessing and retrieval pipeline
│   ├── team_charter.md         # team working agreement
│   └── time_management/        # weekly time-stamped report PDFs
├── notebooks/                  # EDA and validation notebooks
├── data/                       # local-only CGI data and generated outputs, ignored by Git
├── .streamlit/
│   └── config.toml             # Streamlit configuration
├── .env.example                # environment variable template, no secrets
├── environment.yml             # recommended conda environment
└── requirements.txt            # optional pip fallback
```

The `data/` directory is for local CGI-provided files and generated artifacts only. It is ignored by Git and must not be committed.

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

The Excel filenames should match the listed names exactly because the Week 1 data pipeline reads from those expected paths.

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
python src/opportunity_cleaner.py
```

Run the Streamlit app:

```bash
streamlit run app/app.py
```

Run all tests:

```bash
python -m pytest tests
```

Run a selected test file:

```bash
python -m pytest tests/test_opportunity_cleaner.py
```

## Week 1 Status

Week 1 established the project foundations:

- Opportunity merge pipeline for the two anonymized opportunity Excel workbooks.
- Data validation notes and reusable validation helpers for field quality checks and owner-level aggregates.
- Capacity scoring engine skeleton as a first-pass foundation for sales load, delivery load, historical baseline, relative load, scores, and labels.
- Streamlit dashboard skeleton with mock data for the Director Capacity Dashboard and RFP Assignment Tool views.
- RFP preprocessing and vector store skeletons as first-pass foundations for proposal/response extraction, chunking, and retrieval experiments.
- Architecture, dashboard input, validation, capacity engine, RFP pipeline, team charter, and time management documentation.

These are Week 1 foundations and skeletons. Final model behavior, production integration, and validated business rules are still in progress.

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

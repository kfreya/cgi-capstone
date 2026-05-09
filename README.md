# CGI Capacity Analyzer Dashboard

UBC Capstone project in partnership with CGI.

## What This Project Does

CGI has many directors and senior managers across Canada who are responsible for both running existing projects and winning new business. The problem is that there is no clear, real-time view of who is overloaded and who has room for more work. This is currently tracked manually and inconsistently.

This project builds a two-part tool:

1. **Capacity Dashboard** - shows each director's current workload compared to their own historical average, so leadership can quickly see who is at capacity and who is available.

2. **RFP Assignment Tool** - when a new project proposal (RFP) comes in, the tool estimates how much effort it requires and recommends the best available director to take it on.

The tool uses sales opportunity data from CGI's CRM and past RFP/proposal documents. It integrates with Azure OpenAI for document analysis and reasoning.

## Repo Structure

```text
cgi-capstone/
├── app/                        # Streamlit web app
│   ├── app.py                  # dashboard entrypoint
│   └── mock_data.py            # synthetic dashboard data for Week 1 UI
├── src/                        # reusable data, Azure, and analysis modules
├── notebooks/                  # exploratory analysis
├── docs/
│   ├── architecture.md         # system architecture and dashboard design notes
│   └── team_charter.md         # team contract and collaboration guidelines
├── tests/                      # unit tests for src modules
├── data/                       # local folder for CGI-provided project data
│   ├── .env                    # local API keys and Azure endpoints, ignored by Git
│   ├── csv_files/              # local opportunity Excel files, ignored by Git
│   ├── proposals_responses.json # local proposal/RFP data, ignored by Git
│   ├── processed/              # local processed data outputs, ignored by Git
│   └── vector_store/           # local vector database artifacts, ignored by Git
├── .streamlit/
│   └── config.toml             # Streamlit theme configuration
├── .env.example                # template for required environment variables
├── environment.yml             # recommended conda environment
└── requirements.txt            # optional pip alternative
```

## Setup

Create and activate the recommended conda environment:

```bash
conda env create -f environment.yml
conda activate cgi-capstone
```

### Data setup

The `data/` directory is the local folder for CGI-provided project data. CGI-provided data files are intentionally not tracked in Git. Team members should place their local copies of the CGI files there.

Expected local files include:

- `data/.env`
- `data/csv_files/`
- `data/proposals_responses.json`

These files are ignored by Git and should not be committed.

Create the local data folders if they are missing:

```bash
mkdir -p data/csv_files
```

Copy the CGI-provided `.env` into `data/.env`.

Put the opportunity Excel files into `data/csv_files/`.

Put `proposals_responses.json` into `data/proposals_responses.json`.

If you do not have a CGI-provided `.env` yet, create a local placeholder from the template:

```bash
cp .env.example data/.env
```

Fill in `data/.env` locally with the required Azure OpenAI and OpenAI values. Real API keys, endpoints, secrets, and data files must never be committed.

Verify that the environment variables are configured:

```bash
python src/check_env.py
```

The Streamlit app entrypoint will be `app/app.py` later in the project.

### Optional pip setup

Conda is the recommended setup path for this project. If you cannot use conda, `requirements.txt` is kept as an optional pip alternative:

```bash
pip install -r requirements.txt
```

## Team

Freya, Kian, Lyken, Yixiao - UBC MDS Capstone 2025/2026

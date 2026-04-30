# CGI Capacity Management Tool

This repository contains the initial scaffold for the CGI Capacity Management / Capacity Analyzer Dashboard UBC capstone project. The project will load proposal and opportunity data, support capacity analysis workflows, and provide the foundation for a dashboard and future Azure OpenAI integration.

## Setup

Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate cgi-capstone
```

Check that required environment variables are present:

```bash
python src/check_env.py
```

## Security

Never commit `data/.env` or any file containing real API keys, endpoints, or secrets. Use `.env.example` as the template for required variable names, and keep actual values only in local ignored environment files.

## Initial Repo Structure

```text
.
├── app/
├── data/
│   ├── csv_files/
│   ├── processed/
│   ├── vector_store/
│   └── proposals_responses.json
├── notebooks/
├── src/
│   ├── azure_client.py
│   ├── check_env.py
│   └── data_loader.py
├── .env.example
├── .gitignore
├── environment.yml
└── README.md
```

# Scripts

This directory contains utility scripts for setup, validation, and evidence
generation workflows.

Current scripts include:

- `build_rfp_chroma_index.py` for building the reusable local RFP Chroma index.
- `smoke_azure_chroma.py` for Azure/Chroma smoke validation.
- `validate_rfp_data_and_export_samples.py` for proposal/RFP validation and
  sample export generation.
- `generate_rfp_retrieval_evidence.py` for retrieval evidence artifacts.

Run scripts from the repository root so relative paths resolve as documented.
Generated local CGI-derived artifacts should remain under ignored `data/`
folders unless they are intentionally redacted handoff artifacts.

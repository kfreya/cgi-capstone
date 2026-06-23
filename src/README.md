# Source Modules

This directory contains reusable Python source modules for the prototype.

Main module groups:

- Data loading and cleaning: `data_loader.py`, `opportunity_cleaner.py`.
- Validation: `data_validator.py`, `rfp_data_validator.py`,
  `rfp_evidence_validator.py`.
- Capacity scoring: `capacity_engine.py`.
- RFP processing and retrieval: `rfp_preprocessor.py`, `rfp_engine.py`,
  `vector_store.py`.
- Azure and fallback helpers: `azure_client.py`,
  `azure_embedding_client.py`, `azure_rag_client.py`, `check_env.py`.

These files define application behavior and shared logic. Local CGI data,
credentials, generated outputs, and notebooks should stay outside `src/`.

# Fallback Demo and Vector Store Notes

## Responsibility Summary

This week my main role was to keep the RFP retrieval backend stable and demo-ready while the Azure preferred path remained blocked.

The goal was not to add a new feature for its own sake. The goal was to make sure the final prototype still had one reliable retrieval path that could support the Streamlit RFP page, the dashboard-facing `assignment_context`, and the report notes.

## Current Blocker

The Azure embedding path is still blocked because CGI has not confirmed these two required values:

- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

Because of that, the fallback retrieval path remains the official safe path for now.

## Code Updates

The retrieval backend is updated to make the fallback and preferred paths more explicit and easier to test.

### `src/azure_client.py`

- Added fallback-safe Azure configuration checks
- Added lazy Azure SDK import behavior
- Added helpers for environment status and smoke-test readiness

### `src/vector_store.py`

- Improved chunk parsing so the vector store accepts multiple chunk shapes
- Added local vector store status helpers
- Added retrieval helpers that return dashboard-style retrieved examples
- Kept the Chroma helper path available without making it the default demo path

### New compatibility layers

- `src/azure_embedding_client.py`
- `src/azure_rag_client.py`

These files make the Azure-related path easier to reason about without forcing the rest of the project to depend on a live Azure setup.

`src/azure_embedding_client.py` acts as a small wrapper around the Azure embedding helpers. It gives the project a clearer place to ask questions like:

- Is the Azure embedding configuration ready?
- Can the smoke test run right now?
- Can we get a callable embedding function, or should we stay on fallback?

That makes it easier to keep the Azure setup checks separate from the retrieval logic itself.

`src/azure_rag_client.py` does the same thing for retrieval. It gives the project a clearer entry point for:

- building a fallback retrieval report from local chunks
- building a preferred retrieval report when Azure embeddings are available
- returning dashboard-style retrieved examples in the same shape the RFP page expects

In other words, these two files separate the Azure readiness checks from the actual retrieval flow. That makes the code easier to test, and it also keeps the fallback path clean when Azure is still blocked.

## How To Run Tests

Run the focused retrieval and Azure helper tests from the repository root:

```bash
conda run -n cgi-capstone python -m pytest tests/test_azure_client.py tests/test_vector_store.py tests/test_azure_embedding_client.py tests/test_azure_rag_client.py
```

## Test Result

Focused retrieval and Azure helper tests passed:

- `29 passed`

## Notes

The fallback retrieval path is the one that should be used for demo readiness until CGI provides the missing Azure configuration values.

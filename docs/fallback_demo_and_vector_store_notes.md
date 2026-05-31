# Fallback Demo and Vector Store Notes

## Responsibility Summary

This week my role was to keep the RFP retrieval backend honest, stable, and easy to hand off. The work started from a fallback-first setup, but the scope now also includes the Azure/Chroma path because CGI finally provided the missing environment values.

The main goal is still the same: make sure the final prototype has one reliable retrieval flow that can support the Streamlit RFP page, the dashboard-facing `assignment_context`, and the report notes.

## Retrieval Mode and Status

The retrieval backend now needs to support two clear modes:

- `azure_chroma` when Azure embeddings and Chroma are available
- `local_fallback` when Azure, Chroma, or vector-store setup fails

That mode should be obvious in the backend behavior and in the final UI/report notes, so nobody has to guess which path produced a result.

The practical rule for this week is:

- prefer Azure/Chroma when the environment is ready
- fall back cleanly when any step fails
- keep the output schema stable either way

## Current Blocker

The main Azure blocker from Week 3 is gone because CGI provided the missing config values. That means the preferred Azure/Chroma path is now in scope instead of being purely theoretical.

The remaining risk is integration stability, not environment availability. If the preferred path breaks at any step, the fallback retrieval path still needs to work and still needs to return dashboard-style examples.

The Streamlit RFP page also needs to stay in sync with the backend now, so the retrieval mode shown to users matches the actual path that produced the result.

## Code Updates

The retrieval backend was updated to make the fallback and preferred paths more explicit and easier to test.

### `src/azure_client.py`

- Added fallback-safe Azure configuration checks
- Added lazy Azure SDK import behavior
- Added helpers for environment status and smoke-test readiness
- Aligned the embedding setup with the CGI-provided Azure configuration style

This file gives the project a safe way to check whether Azure is ready without forcing the rest of the code to import the SDK too early.

### `src/vector_store.py`

- Improved chunk parsing so the vector store accepts multiple chunk shapes
- Added local vector store status helpers
- Added retrieval helpers that return dashboard-style retrieved examples
- Kept the Chroma helper path available without making it the only path

This file now handles both the local fallback path and the preferred Chroma path in a way that is still compatible with the chunk shapes used by the project.

### New compatibility layers

- `src/azure_embedding_client.py`
- `src/azure_rag_client.py`

These files make the Azure-related path easier to reason about without forcing the rest of the project to depend on a live Azure setup.

`src/azure_embedding_client.py` is a small wrapper around the Azure embedding helpers. It gives the project a clear place to ask questions like:

- Is the Azure embedding configuration ready?
- Can the smoke test run right now?
- Can we get a callable embedding function, or should we stay on fallback?

`src/azure_rag_client.py` does the same thing for retrieval. It gives the project a clearer entry point for:

- building a fallback retrieval report from local chunks
- building a preferred retrieval report when Azure embeddings are available
- returning dashboard-style retrieved examples in the same shape the RFP page expects

In other words, these two files separate Azure readiness checks from the actual retrieval flow. That makes the code easier to test, and it also keeps the fallback path clean when Azure is unavailable.

### `src/rfp_engine.py`

- Wired the preferred Azure/Chroma retrieval path into `generate_assignment_context()`
- Added `retrieval_mode` and `retrieval_status` to the dashboard payload
- Kept the fallback path available when Azure or Chroma fails
- Updated the note text so it no longer describes Azure/Chroma results as local fallback

This is the file that connects the retrieval backend to the dashboard-facing assignment output.

### `app/app.py`

- Updated the RFP Assignment Tool banner and result area so the retrieval mode is shown explicitly
- Displayed `Azure/Chroma retrieval active` when the preferred path succeeds
- Displayed `Local fallback retrieval active` when the fallback path is used

This keeps the UI message aligned with the backend result instead of hard-coding the old fallback-only message.

## Test Coverage

The test updates were added to match the files above one by one.

### `tests/test_azure_client.py`

- Covers fallback-safe Azure config checks
- Covers the lazy Azure client factory
- Covers Azure embedding helper behavior when config is missing or present
- Covers the environment status and smoke-test readiness helpers

### `tests/test_vector_store.py`

- Covers the vector store status helper
- Covers retrieval from chunk dictionaries
- Covers the flat chunk contract used by the RFP pipeline
- Covers the Chroma helper path when it is available

### `tests/test_azure_embedding_client.py`

- Covers the Azure embedding compatibility wrapper
- Checks the blocked smoke-test state when Azure config is missing
- Checks the successful smoke-test shape when embeddings are available

### `tests/test_azure_rag_client.py`

- Covers the fallback retrieval wrapper
- Covers the preferred retrieval wrapper
- Confirms the fallback path still returns dashboard-style output
- Confirms the preferred path falls back cleanly when Azure is unavailable

### `tests/test_rfp_engine.py`

- Covers the dashboard-facing `assignment_context`
- Confirms the preferred Azure/Chroma path flows into `generate_assignment_context()`
- Confirms `retrieval_mode` and `retrieval_status` are returned in the output
- Confirms the notes text stays consistent with the backend path that was actually used

## How To Run Tests

Run the focused retrieval and Azure helper tests from the repository root:

```bash
conda run -n cgi-capstone python -m pytest tests/test_azure_client.py tests/test_vector_store.py tests/test_azure_embedding_client.py tests/test_azure_rag_client.py
```

## Test Result

Focused retrieval and Azure helper tests passed:

- `29 passed`

Preferred-path regression tests also passed:

- `39 passed`

## Latest Smoke Test

The Azure embedding smoke test also passed after the environment values were filled in:

```bash
conda run -n cgi-capstone python -c "from src.azure_embedding_client import smoke_test_embedding; print(smoke_test_embedding())"
```

Result:

- `status: ok`
- `missing: []`
- `vector_count: 1`
- `dimension: 1536`

This confirms that the Azure embedding path is working and producing a valid vector for the current configuration.

## End-to-End Retrieval Smoke Test

The full Azure/Chroma retrieval path also passed.

### Retrieval backend report

```bash
conda run -n cgi-capstone python -c "from src.azure_rag_client import preferred_retrieval_report; report = preferred_retrieval_report('Need cloud migration and dashboard support.'); print({'backend': report.get('backend'), 'retrieval_mode': report.get('retrieval_mode'), 'retrieved_count': len(report.get('retrieved_examples', [])), 'first_chunk_id': report.get('retrieved_examples', [{}])[0].get('chunk_id') if report.get('retrieved_examples') else None})"
```

Result:

- `backend: azure_chroma`
- `retrieval_mode: azure_chroma`
- `retrieved_count: 3`
- `first_chunk_id: historical_sample_chunk_013`

### Assignment context report

```bash
conda run -n cgi-capstone python -c "from src.rfp_engine import generate_assignment_context; output = generate_assignment_context('Need cloud migration and dashboard support.'); print({'retrieval_mode': output.get('retrieval_mode'), 'retrieved_count': len(output.get('retrieved_examples', [])), 'keys': sorted(output.keys())})"
```

Result:

- `retrieval_mode: azure_chroma`
- `retrieved_count: 3`
- `keys` included:
  - `effort`
  - `notes`
  - `recommended_directors`
  - `retrieval_mode`
  - `retrieval_status`
  - `retrieved_examples`
  - `rfp_summary`
  - `risk_flags`
  - `similar_rfps`

This confirms that the preferred Azure/Chroma path is not just available by itself, but also wired into `generate_assignment_context()` in a Streamlit-ready way.

## Notes

The fallback retrieval path is still important, but it is no longer the only story. The current job is to make the Azure/Chroma path real, keep the fallback path safe, and make the retrieval mode obvious wherever the result is shown.

Recent small fixes:

- The preferred Azure/Chroma path now resets the Chroma collection before rebuilding, so old test results do not leak into new runs.
- Ordinary unit tests are kept on the local fallback path by default, so local Azure settings do not change the normal test behavior.
- Preferred-path tests still exist separately and can be run when we want to check the Azure/Chroma flow directly.

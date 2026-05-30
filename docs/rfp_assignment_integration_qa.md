# Week 3 Yixiao RFP Integration Notes

## Azure Embedding Status and Blocker

- The local environment is now ready for Azure/OpenAI checks.
- `python-dotenv`, `openai`, and `chromadb` are installed.
- `python src/check_env.py` runs successfully and reads `data/.env`.
- Existing `data/.env` has API key and endpoint variables, but is currently missing:
  - `AZURE_OPENAI_API_VERSION`
  - `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
  - `AZURE_OPENAI_CHAT_DEPLOYMENT`
- For embedding smoke tests, the immediate blockers are:
  - `AZURE_OPENAI_API_VERSION`
  - `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- `AZURE_OPENAI_CHAT_DEPLOYMENT` is not required for the current embedding-only smoke test.
- A minimal Azure embedding client layer has been implemented and unit-tested with mocked calls.
- Real Azure embedding smoke testing is blocked until CGI confirms API version and embedding deployment name.
- Do not overclaim that Azure embeddings are working end-to-end yet.
- Local fallback retrieval remains available and should continue to support RFP Assignment Tool integration while Azure details are pending.

## Impact on Week 3 Progress

This blocker affects only the preferred Azure embedding + Chroma retrieval path. It does not block RFP preprocessing, chunking, local fallback retrieval, `generate_assignment_context()`, Streamlit RFP page integration, recommendation heuristic work, or QA documentation.

Freya can continue UI integration using fallback `assignment_context`. Jai can continue assignment logic and `risk_flags` using fallback `retrieved_examples`. Kian can continue RFP text validation and chunk metadata work. Yixiao should document the blocker, preserve fallback behavior, and maintain the smoke test checklist.

## Current RFP Fallback Path

Current working fallback path:

```text
RFP text
-> text normalization / preprocessing
-> chunking
-> local deterministic fallback embeddings
-> in-memory retrieval
-> generate_assignment_context()
-> Streamlit RFP page display
```

This path does not require Azure credentials. It should remain available even after Azure embedding is added, because it supports Week 3 UI and assignment logic development while Azure deployment details are pending.

Outputs from this path should be labelled as fallback / heuristic / prototype in UI and report notes.

## assignment_context Contract

Current `generate_assignment_context()` signature:

```python
generate_assignment_context(
    rfp_text: str,
    director_df: Any = None,
    historical_chunks: list[dict[str, Any]] | None = None,
)
```

Current top-level keys:

- `rfp_summary`
- `effort`
- `similar_rfps`
- `retrieved_examples`
- `recommended_directors`
- `risk_flags`
- `notes`

Nested fields:

`effort`:

- `level`
- `reason`
- `estimated_duration`
- `rationale` (backward-compatible alias for `reason`)

`retrieved_examples`:

- `proposal_id`
- `chunk_id`
- `similarity_score`
- `supporting_text`

`recommended_directors`:

- `director_name`
- `capacity_label`
- `capacity_score`
- `relative_load`
- `assignment_score`
- `match_reason`
- `capacity_explanation`
- `experience_match_explanation`
- `risk_flags`
- `supporting_chunks`

Naming decision:

- Backend keeps the key `effort`.
- Streamlit should display this as "Estimated Effort".
- `effort.reason` should be used as the displayed reason/explanation, with
  `effort.rationale` as a backward-compatible fallback.
- Do not rename `effort` to `estimated_effort` before UI integration unless tests and dashboard are updated together.

## Integration QA Checklist

- [ ] Run RFP fallback tests:

  ```bash
  python -m pytest tests/test_rfp_preprocessor.py tests/test_vector_store.py tests/test_rfp_engine.py
  ```

- [ ] Run Azure client tests:

  ```bash
  python -m pytest tests/test_azure_client.py
  ```

- [ ] Run environment check:

  ```bash
  python src/check_env.py
  ```

- [ ] Confirm `generate_assignment_context()` returns all required top-level keys.
- [ ] Confirm `effort` includes `level` and `reason`.
- [ ] Confirm `retrieved_examples` is a list, even when empty.
- [ ] Confirm `recommended_directors` is a list, even when using mock/fallback director data.
- [ ] Confirm `risk_flags` is a list.
- [ ] Confirm local fallback retrieval still works if Azure variables are missing.
- [ ] Confirm the Streamlit RFP page blocks or warns on empty RFP input.
- [ ] Confirm Streamlit displays `effort` as "Estimated Effort".
- [ ] Confirm fallback, heuristic, and mock outputs are clearly labelled in UI/report notes.
- [ ] Confirm no API keys, endpoints, or secret values are printed.

## Fallback assignment_context Smoke Test Result

- The smoke test was run without Azure calls.
- The local fallback path successfully generated a dashboard-facing `assignment_context`.
- Required top-level keys were all present:
  - `rfp_summary`
  - `effort`
  - `similar_rfps`
  - `retrieved_examples`
  - `recommended_directors`
  - `risk_flags`
  - `notes`
- Smoke test summary:
  - `missing_required_keys`: `[]`
  - `effort_keys`: `['estimated_duration', 'level', 'rationale', 'reason']`
  - `effort_level`: `Low`
  - `retrieved_examples_count`: `3`
  - `recommended_directors_count`: `1`
  - `risk_flags_count`: `1`
  - `first_director_name_present`: `True`
  - `first_director_capacity_label`: `Available`
- Tests run:
  - `python -m pytest tests/test_rfp_preprocessor.py tests/test_vector_store.py tests/test_rfp_engine.py` -> `18 passed`
  - `python -m pytest tests/test_azure_client.py` -> `6 passed`
- Interpretation:
  - This confirms the local fallback path can support Streamlit RFP page integration while Azure embedding deployment details are pending.
  - Outputs should still be labelled as fallback / heuristic / prototype until Azure-backed retrieval and final assignment logic are connected.

## Streamlit RFP Fallback Integration Status

- `app/app.py` now imports `generate_assignment_context` from `src.rfp_engine`.
- The RFP Assignment Tool page can now call `generate_assignment_context(rfp_text)` for non-empty pasted RFP text.
- Empty or whitespace-only input is handled with a Streamlit warning before any backend call.
- The Analyze RFP button is enabled.
- The territory and service domain selectors remain UI context only for now and are not yet passed into backend scoring.
- The page renders:
  - `rfp_summary`
  - `effort` as "Estimated Effort", including level, estimated duration, and reason
  - `retrieved_examples`
  - `recommended_directors`
  - `risk_flags`
  - `notes`
- The page includes a visible fallback/prototype notice near the generated results.
- Azure is not called by this Streamlit integration.
- Local fallback retrieval remains the active path while Azure embedding deployment details are pending.
- `data/.env` was not modified.

Validation summary:

- `python -m py_compile app/app.py` -> passed
- `python -m pytest tests/test_rfp_preprocessor.py tests/test_vector_store.py tests/test_rfp_engine.py` -> `18 passed`
- `python -m pytest tests/test_azure_client.py` -> `6 passed`

Interpretation:

- This confirms that the RFP Assignment Tool page can now support Week 3 fallback demo flow.
- The result should still be labelled as fallback / heuristic / prototype until Azure-backed retrieval and final assignment logic are connected.

## Real vs Fallback vs Heuristic vs Mock Components

| Component | Current Status | Notes |
| --- | --- | --- |
| Text extraction / preprocessing | Real local code | Uses `rfp_preprocessor.py` |
| Chunking | Real local code | Produces traceable chunk metadata |
| Local retrieval | Real fallback | Uses deterministic local embeddings and in-memory retrieval |
| Azure embeddings | Implemented helper, blocked for real smoke test | Missing API version and embedding deployment in local `data/.env` |
| Chroma retrieval | Structure exists / not final end-to-end | Chroma expects precomputed embeddings |
| Effort estimate | Heuristic prototype | Should be labelled as estimate |
| Recommended directors | Heuristic / mock-like when `director_df` is missing | Not final business recommendation |
| Risk flags | Heuristic prototype | Useful for surfacing limitations |
| Sample historical corpus | Fallback | Used when `historical_chunks` is omitted |
| Mock Director A | Mock fallback | Used when `director_df` is missing |

## Prepared Smoke Test Once CGI Provides Values

Run the environment check first:

```bash
python src/check_env.py
```

Then run the embedding smoke test:

```bash
python - <<'PY'
from src.azure_client import embed_texts

vectors = embed_texts(["This is a minimal Azure embedding smoke test."])
print("embedding_count:", len(vectors))
print("embedding_dimension:", len(vectors[0]) if vectors else 0)
print("first_vector_is_numeric:", all(isinstance(x, (int, float)) for x in vectors[0][:5]))
PY
```

Expected output:

- `embedding_count` should be `1`
- `embedding_dimension` should be greater than `0`
- `first_vector_is_numeric` should be `True`

## Week 3 (Role 3 — Lyken) Status: Blocked By CGI Azure Env Vars

### What is blocked
As of Friday night (Week 3), CGI has not provided the two Azure embedding configuration values required to perform a real Azure embedding call:

- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

Without these, we cannot run the preferred path end-to-end:

`RFP text → chunking → Azure embeddings → Chroma persist/query → retrieved_examples → assignment_context`

### What is already completed (code + interface)
The repository is ready to integrate Azure retrieval as soon as the missing env vars arrive:

- `src/azure_client.py`
  - Azure config validation helper(s) (no secrets logged)
  - Azure OpenAI SDK client factory (no API call in factory)
  - `embed_texts(texts)` embedding function (real Azure call when configured)
  - Fallback-safe helper(s) to detect whether Azure embedding is currently usable
- `src/vector_store.py`
  - Local fallback retrieval remains available (deterministic local embedding + in-memory vector store)
  - Chroma helper path is wired to accept an injected embedding function so tests and fallback do not require Azure

### Fallback behavior (team unblocked)
Even if Azure/Chroma is unavailable, the Week 3 workflow can continue:

- `generate_assignment_context()` remains runnable using local fallback retrieval
- `assignment_context` schema remains stable for dashboard + assignment logic development
- Risk/notes can clearly label that fallback retrieval is being used

### Tests (current status)
Local RFP fallback pipeline tests are passing (no Azure credentials required):

```bash
python -m pytest tests/test_vector_store.py tests/test_rfp_engine.py tests/test_rfp_preprocessor.py
```

### Smoke test (run immediately once CGI provides the missing vars)
1) Put the values into the local, untracked env file:

- `data/.env` (do not commit)

2) Confirm the environment is visible:

```bash
python src/check_env.py
```

3) Minimal Azure embedding smoke test (prints only vector count + dimension; no secrets):

```bash
python - << 'PY'
from src.azure_client import embed_texts

vectors = embed_texts(["This is a minimal Azure embedding smoke test."])
print("n_vectors:", len(vectors))
print("dim:", len(vectors[0]) if vectors else None)
PY
```

Expected:

- `n_vectors: 1`
- `dim: <positive integer>`

### Next step when env vars arrive
Once `AZURE_OPENAI_API_VERSION` and `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` are provided and the smoke test passes:

- enable the preferred retrieval path in the integration layer (vector-store + RFP engine wiring)
- keep fallback retrieval as a non-blocking path for dashboard demos and development

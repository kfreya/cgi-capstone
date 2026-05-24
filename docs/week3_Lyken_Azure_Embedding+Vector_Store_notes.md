# Azure Embedding + Vector Store (Week 3)

## Responsibility Summary
This week's focus is moving the RFP retrieval pipeline from a purely local prototype toward an Azure-backed retrieval path **without breaking the existing fallback**.

What was already working:
- `proposals_responses.json` → text extraction → chunking
- local deterministic embedding → in-memory retrieval
- `generate_assignment_context()` → dashboard-facing `assignment_context` schema
- RFP-related unit tests passing

My Week 3 responsibility:
- Add Azure OpenAI embedding capability behind a clean interface
- Add an Azure embeddings → Chroma persist/query path in the vector store layer
- Keep local fallback retrieval available and stable
- Keep tests passing / non-blocking for the team

## Code Deliverables (What I Added)
### A. `src/azure_client.py`
Added helper functions to:
- Validate Azure env configuration (strict validation + fallback-safe inspection)
- Create Azure OpenAI SDK client (factory only; no API call on creation)
- Embed texts via Azure OpenAI embeddings deployment (`embed_texts`)
- Provide availability + safe selection helpers so callers can decide Azure vs fallback without crashing

Intent:
- Make Azure embedding a **drop-in embedding function**: `embedding_function(texts) -> embeddings`
- Make it possible to test logic and keep the dashboard working even when Azure env vars are missing.

### B. `src/vector_store.py`
Added helper functions to support:
- Building/persisting a Chroma vector store from dashboard-style chunks:
  - `chunks (dict list) → RFPChunk objects → embeddings → Chroma persist`
- Querying Chroma using an embedding of `query_text`
- Returning results in the **existing dashboard-facing retrieved_examples shape**:
  - `{proposal_id, chunk_id, similarity_score, supporting_text}`

Intent:
- Enable an Azure+Chroma retrieval path while preserving the local in-memory retrieval path.

## How to Call / Use 
### Azure embedding function
- Primary entrypoint is the embedding function that takes `Sequence[str]` and returns `list[list[float]]`.
- This is designed to plug into vector store build/query helpers.

### Chroma build/query
- Build/persist once (or rebuild as needed) from chunk dicts.
- Query using `query_text` embedding, returning dashboard-friendly retrieved examples.

Important:
- The existing local fallback retrieval remains the default "safe path".
- Azure+Chroma is an optional "preferred path" that can be selected when env vars are present.

## Tests Status
Ran:
```bash
python -m pytest tests/test_vector_store.py tests/test_rfp_engine.py tests/test_rfp_preprocessor.py
```

Result:
- `18 passed` (local prototype + new helper additions did not break existing behavior)

Notes:
- Azure/Chroma end-to-end is not executed by these tests because we do not yet have:
  - `AZURE_OPENAI_API_VERSION`
  - `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

## Smoke Test: Run Immediately Once Env Vars Arrive
### Required env vars (stored locally in `data/.env`, not committed)
Minimum for embeddings:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

### Step 1 — confirm env is visible
From repo root:
```bash
python src/check_env.py
```
Expected:
- Required variables show `FOUND`

### Step 2 — run minimal embedding smoke test 
Run from repo root (prints only counts/dimensions):
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

### Step 3 — (optional) Chroma smoke test 
```bash
python - << 'PY'
from src.rfp_preprocessor import prepare_rfp_chunks
from src.vector_store import build_chroma_from_chunks, query_chroma

chunks = prepare_rfp_chunks("Cloud migration and data analytics with managed services support.")
build_chroma_from_chunks(chunks, persist_directory="data/vector_store", collection_name="rfp_chunks")

results = query_chroma("cloud migration analytics", persist_directory="data/vector_store", collection_name="rfp_chunks", top_k=3)
print("n_results:", len(results))
print("keys:", list(results[0].keys()) if results else None)
PY
```

Expected:
- `n_results: 1..3`
- result keys include: `proposal_id`, `chunk_id`, `similarity_score`, `supporting_text`

Note:
- This is a **mechanical Chroma smoke test** (can embed → write → query).
- It does **not** validate the full preferred retrieval workflow (persist historical proposal chunks once, then retrieve them for a new RFP query).

## Current Blockers / Dependencies
- Azure embeddings cannot be validated end-to-end until CGI provides:
  - `AZURE_OPENAI_API_VERSION`
  - `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- Until then:
  - Local fallback retrieval remains verified and usable (tests pass)
  - Assignment context schema remains stable for dashboard + assignment logic development

## Next Steps (Once CGI Unblocks)
- Run Step 2 (Azure embedding smoke test) and record vector dimension only (no secrets).
- If Step 2 passes, run Step 3 (Chroma smoke test) to validate persist/query locally.
- Keep fallback path enabled so dashboard + assignment logic remain non-blocking.

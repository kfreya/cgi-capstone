# RFP Pipeline

## Purpose

This document describes the Week 2 version of the RFP retrieval pipeline. The
goal is to take proposal/RFP text, break it into searchable chunks, attach
traceable metadata, and return a stable dashboard ready prototype output.

This supports the larger CGI Capacity Analyzer project by giving the future RFP
assignment tool relevant historical examples when a new RFP comes in. Those
retrieved examples can later help explain effort estimates, risk flags, and
director recommendations. For Week 2, the priority is the interface and basic
retrieval prototype, not a final recommendation model yet.

## Data Assumptions

The real proposal data is expected at:

```text
data/proposals_responses.json
```

That file contains sensitive company data and is intentionally not committed to
Git. The tests still use small synthetic examples so the repo can run without
private data. The preprocessing code has also been checked against a local copy
of the proposal JSON, but the file itself should stay outside Git.

## Files in This Work

Project files should be run from the repository root so imports work
consistently. For example:

```bash
python src/rfp_preprocessor.py
python src/vector_store.py
python -m pytest tests/test_rfp_preprocessor.py tests/test_vector_store.py tests/test_rfp_engine.py
```

### `src/rfp_preprocessor.py`

This file prepares historical RFP text for retrieval.

It does the following:

- reads proposal and proposal-response records from the expected JSON shape
- converts raw content fields into clean plain text
- handles strings, lists of paragraphs, nested lists, and simple dictionaries
- splits long RFP text into overlapping chunks so it can be searched safely
- stores source metadata on every chunk, including title, section, response
  name, chunk index, ownership fields when available, and approximate
  token/character span

To run a quick readable demo from the terminal:

```bash
python src/rfp_preprocessor.py
```

The main functions in this file are:

```python
chunk_text(rfp_text, chunk_size=500, overlap=50)
load_sample_rfp_text("data/proposals_responses.json")
preprocess_proposals(proposals)
prepare_rfp_chunks(rfp_text)
```

`preprocess_proposals()` returns `RFPChunk` objects for the historical proposal
JSON. `prepare_rfp_chunks()` returns chunk dictionaries for a new pasted/uploaded
RFP so the dashboard can call the pipeline with one text input.
`load_sample_rfp_text()` tries to read one proposal from the local JSON file and
falls back to synthetic RFP text if the private data is not available.
Running `python src/rfp_preprocessor.py` prints a short readable preview of the
first generated chunk instead of dumping the full raw dictionary.

The main dashboard-facing functions now match the Week 2 work plan:

```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]
def prepare_rfp_chunks(rfp_text: str) -> list[dict]
def build_vector_store(chunks: list[dict])
def retrieve_relevant_chunks(query: str, top_k: int = 5)
def generate_assignment_context(rfp_text: str, director_df=None)
```

For the dashboard wrapper, each chunk uses this flat metadata shape:

```python
{
    "proposal_id": "proposal_001",
    "chunk_id": "proposal_001_chunk_001",
    "source_type": "proposal",
    "text": "chunk text here",
    "chunk_index": 0,
    "opportunity_owner": None,
    "opportunity_id": None,
}
```

This dashboard wrapper shape is intentionally minimal and does **not** include
`document_id`. It is designed for a single pasted RFP input path.

### Chunk Metadata Contract (Sprint 3)

Issue #38 formalizes the required metadata dictionary for historical-chunk
validation and retrieval handoff. The canonical required fields are:

```python
[
    "proposal_id",
    "chunk_id",
    "document_id",
    "source_type",
    "chunk_index",
    "text",
    "opportunity_owner",
    "opportunity_id",
]
```

Field-level rules:

- `proposal_id` (string): stable proposal-level grouping key.
- `chunk_id` (string): unique chunk identifier.
- `document_id` (string): source document ID (`...__proposal` or
  `...__response__...`).
- `source_type` (string): expected values are `proposal` or
  `proposal_response`.
- `chunk_index` (int): zero-based index within one source document.
- `text` (string): chunk payload used for embedding/retrieval.
- `opportunity_owner` (nullable string): currently null in historical chunks.
- `opportunity_id` (nullable string): currently null in historical chunks.

Current limitation (validated in Sprint 3):

- `opportunity_owner` / `opportunity_id` are null for all current chunks, so
  proposal-to-director linkage cannot be inferred from chunk metadata alone.

Validation and sample export references:

- `src/rfp_data_validator.py`
- `scripts/validate_rfp_data_and_export_samples.py`
- `docs/rfp_data_validation.md`
- `outputs/rfp_validation/rfp_validation_summary.json`
- `outputs/rfp_validation/rfp_sample_chunks.json`

### `src/vector_store.py`

This file handles retrieval over embedded RFP chunks.

It does the following:

- defines a small `SearchResult` object for ranked retrieval results
- computes cosine similarity between embedding vectors
- provides `InMemoryVectorStore` for local testing without real data or Azure
- provides `ChromaVectorStore` as the wrapper for the future persistent vector
  store
- formats retrieved chunks into a text context block for the later explanation
  step
- builds a stable dashboard/API-style payload with retrieved examples,
  recommended directors, risk flags, and notes

The local store is used so we can test the retrieval
logic with fake embeddings before connecting to Azure OpenAI and Chroma.

The dashboard-facing wrapper functions are:

```python
build_vector_store(chunks)
retrieve_relevant_chunks(query, top_k=5)
```

`retrieve_relevant_chunks()` returns dictionaries shaped like this:

```python
{
    "proposal_id": "proposal_001",
    "chunk_id": "proposal_001_chunk_001",
    "similarity_score": 0.82,
    "supporting_text": "Relevant historical RFP or proposal chunk",
}
```

### `src/rfp_engine.py`

This file connects the preprocessing and vector store wrappers into the mock
assignment output expected by the Streamlit RFP page.

The dashboard-facing function is:

```python
generate_assignment_context(rfp_text, director_df=None)
```

It returns:

```python
{
    "rfp_summary": "Short summary of the input RFP",
    "retrieved_examples": [
        {
            "proposal_id": "proposal_001",
            "chunk_id": "proposal_001_chunk_001",
            "similarity_score": 0.82,
            "supporting_text": "Relevant historical RFP or proposal chunk",
        }
    ],
    "recommended_directors": [
        {
            "director_name": "Director A",
            "capacity_label": "Available",
            "capacity_score": 0.72,
            "relative_load": 0.65,
            "match_reason": "Relevant historical experience and available capacity",
            "supporting_chunks": ["proposal_001_chunk_001"],
        }
    ],
    "risk_flags": [
        {
            "level": "Medium",
            "message": "Limited historical examples found for this RFP type.",
        }
    ],
    "notes": "Prototype output for dashboard integration.",
}
```

If real director capacity data is not available, the function uses a small mock
director record so the dashboard can still be connected and tested.

### `tests/test_rfp_preprocessor.py`

This file tests the preprocessing behavior using synthetic RFP records.

It checks that:

- raw text content is normalized correctly
- proposal and response sections are extracted
- chunking uses overlap
- invalid chunk settings raise clear errors
- final chunks contain traceable metadata
- `prepare_rfp_chunks()` returns the flat Week 2 dashboard chunk shape

### `tests/test_vector_store.py`

This file tests the vector retrieval behavior using a small fake embedding function.

It checks that:

- cosine similarity behaves correctly
- invalid vector dimensions are rejected
- the in-memory store ranks relevant chunks first
- retrieved chunks can be formatted for RFP context
- the dashboard payload has the Week 2 output shape

### `tests/test_rfp_engine.py`

This file tests the dashboard-facing assignment wrapper.

It checks that:

- `generate_assignment_context()` returns the expected dashboard keys
- recommended directors include `director_name`, `match_reason`,
  `capacity_label`, `capacity_score`, `relative_load`, and `supporting_chunks`
- `notes` is returned as a dashboard-friendly string
- the wrapper still works if real director data is not passed in

## Current Limitations

- The preprocessing code has been checked against the real local
  `proposals_responses.json` structure, but retrieval quality still needs to be
  evaluated with CGI-approved examples.
- The chunker uses an approximate whitespace based token count. This is fine for
  local development, but it should be checked against the actual Azure embedding
  model tokenizer before production use.
- The Azure OpenAI embedding function is not implemented yet.
- The Chroma wrapper is ready for precomputed embeddings, but the full
  end-to-end persistence flow still needs to be connected. This is not required
  for Week 2.
- `generate_assignment_context()` is still a mock/basic integration wrapper, not
  the final director recommendation model.

## Mock vs Real Parts

Real/basic parts in this prototype:

- text normalization
- whitespace-based chunking with overlap
- flat chunk metadata
- local deterministic retrieval baseline
- output schema used by the dashboard

Mock or temporary parts:

- Azure OpenAI embeddings are not connected yet
- Chroma persistence is not connected end to end yet
- director ranking is placeholder logic until capacity scoring output is ready
- risk flags are simple prototype flags, not final business logic

## Next Steps

1. Confirm chunk sizes against the Azure OpenAI embedding model limit.
2. Add the Azure embedding function and connect it to the preprocessing output.
3. Persist chunk embeddings into `data/vector_store` using Chroma.
4. Test retrieval quality with known RFP examples and adjust chunk size/overlap
   if needed.
5. Connect the RFP wrappers to the Streamlit page once the dashboard is ready.
6. Replace the mock assignment context with real effort estimation and director
   ranking logic when the capacity scoring output is finalized.

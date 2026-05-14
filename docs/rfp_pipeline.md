# RFP Pipeline

## Purpose

This document describes the first version of the RFP retrieval pipeline. The
goal is to take historical proposal and response text, break it
into searchable chunks, and prepare those chunks for embedding-based retrieval.

This supports the larger CGI Capacity Analyzer project by giving the future RFP
assignment tool relevant historical examples when a new RFP comes in. Those
retrieved examples can later help explain effort estimates, risk flags, and
director recommendations.

## Data Assumptions

The real proposal data is expected at:

```text
data/proposals_responses.json
```

That file contains sensitive company data and is intentionally not committed to
Git. Since I don't have access to the real file yet, this implementation uses
small synthetic examples in the tests. The code follows the JSON structure
described in the README and EDA notebook, but it still needs to be validated on
the real data once it's made available to me.

## Files in This Work

Project files should be run from the repository root so imports work
consistently. For example:

```bash
python src/vector_store.py
python -m pytest tests/test_rfp_preprocessor.py tests/test_vector_store.py
```

### `src/rfp_preprocessor.py`

This file prepares historical RFP text for retrieval.

It does the following:

- reads proposal and proposal-response records from the expected JSON shape
- converts raw content fields into clean plain text
- handles strings, lists of paragraphs, nested lists, and simple dictionaries
- splits long RFP text into overlapping chunks so it can be embedded safely
- stores source metadata on every chunk, including title, section, response
  name, chunk index, and approximate token/character span

The file can be run as:

```python
preprocess_proposals(proposals)
prepare_rfp_chunks(rfp_text)
```

`preprocess_proposals()` returns `RFPChunk` objects for the historical proposal
JSON. `prepare_rfp_chunks()` returns chunk dictionaries for a new pasted/uploaded
RFP so the dashboard can call the pipeline with one text input.

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
- builds a stable dashboard/API-style payload with the recommended directors and
  supporting chunks

The local store is useful for development because I can test the retrieval
logic with fake embeddings before connecting to Azure OpenAI and Chroma.

The dashboard-facing wrapper functions are:

```python
build_vector_store(chunks)
retrieve_relevant_chunks(query, top_k=5)
```

### `src/rfp_engine.py`

This file connects the preprocessing and vector-store wrappers into the mock
assignment output expected by the Streamlit RFP page.

The dashboard-facing function is:

```python
generate_assignment_context(rfp_text, director_df)
```

It returns:

```python
{
    "rfp_summary": "Short summary of the RFP",
    "recommended_directors": [
        {
            "director_name": "Director A",
            "match_reason": "Relevant experience and available capacity",
            "capacity_label": "Available",
            "supporting_chunks": ["chunk 1", "chunk 2"],
        }
    ],
    "notes": "This is a mock output for dashboard integration.",
}
```

### `tests/test_rfp_preprocessor.py`

This file tests the preprocessing behavior using synthetic RFP records.

It checks that:

- raw text content is normalized correctly
- proposal and response sections are extracted
- chunking uses overlap
- invalid chunk settings raise clear errors
- final chunks contain traceable metadata

### `tests/test_vector_store.py`

This file tests the vector retrieval behavior using a small fake embedding function.

It checks that:

- cosine similarity behaves correctly
- invalid vector dimensions are rejected
- the in-memory store ranks relevant chunks first
- retrieved chunks can be formatted for RFP context
- the dashboard payload has a stable output shape

### `tests/test_rfp_engine.py`

This file tests the dashboard-facing assignment wrapper.

It checks that:

- `generate_assignment_context()` returns the expected dashboard keys
- recommended directors include `director_name`, `match_reason`,
  `capacity_label`, and `supporting_chunks`
- `notes` is returned as a dashboard-friendly string

## Current Limitations

- The preprocessing code has been checked against the real local
  `proposals_responses.json` structure, but retrieval quality still needs to be
  evaluated with CGI-approved examples.
- The chunker uses an approximate whitespace-based token count. This is fine for
  local development, but it should be checked against the actual Azure embedding
  model tokenizer before production use.
- The Azure OpenAI embedding function is not implemented in this PR.
- The Chroma wrapper is ready for precomputed embeddings, but the full
  end-to-end persistence flow still needs to be connected.
- `generate_assignment_context()` is still a mock/basic integration wrapper, not
  the final director recommendation model.

## Next Steps

1. Confirm chunk sizes against the Azure OpenAI embedding model limit.
2. Add the Azure embedding function and connect it to the preprocessing output.
3. Persist chunk embeddings into `data/vector_store` using Chroma.
4. Test retrieval quality with known RFP examples and adjust chunk size/overlap
   if needed.
5. Replace the mock assignment context with real effort estimation and director
   ranking logic.
6. Connect the RFP wrappers to the Streamlit page once the dashboard is ready.

## PR Summary

This PR adds the first company-safe version of the RFP preprocessing and
retrieval foundation. It is very bare bones and just a skeleton for now. It
doesn't require sensitive data to run, but it gives the project a clear path
from historical RFP JSON to retrieval-ready chunks, local vector search tests,
and the dashboard-facing wrapper functions Freya requested.

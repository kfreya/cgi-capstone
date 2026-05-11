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

That file contains sensitive company data and is intentionally not committed to Git. Since I don't have access to the real file yet, this implementation uses small synthetic examples in the tests. The code follows the JSON structure described in the README and EDA notebook, but it still needs to be validated on the real data once it's made available to me.

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
```

That function returns a list of `RFPChunk` objects that are ready to be passed
to an embedding function.

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
- builds a stable dashboard/API-style payload with the query, retrieved chunks,
  optional summary, optional director recommendations, and notes

The local store is useful for development because I can test the retrieval
logic with fake embeddings before connecting to Azure OpenAI and Chroma.

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

## Current Limitations

- The code has not been tested on the real `proposals_responses.json` file yet.
- The chunker uses an approximate whitespace-based token count. This is fine for
  local development, but it should be checked against the actual Azure embedding
  model tokenizer before production use.
- The Azure OpenAI embedding function is not implemented in this PR.
- The Chroma wrapper is ready for precomputed embeddings, but the full
  end-to-end persistence flow still needs to be connected.
- Retrieval quality cannot be fully evaluated until we have approved access to
  real or representative proposal-response examples.

## Next Steps

1. Validate the extractor against the real proposal JSON once access is approved.
2. Confirm chunk sizes against the Azure OpenAI embedding model limit.
3. Add the Azure embedding function and connect it to the preprocessing output.
4. Persist chunk embeddings into `data/vector_store` using Chroma.
5. Test retrieval quality with known RFP examples and adjust chunk size/overlap
   if needed.
6. Connect retrieved chunks to the future RFP assignment and dashboard workflow.

## PR Summary

This PR adds the first company-safe version of the RFP preprocessing and
retrieval foundation. It is very bare bones and just a skeleton for now. It doesn't require sensitive data to run, but it gives the project a clear path from historical RFP JSON to retrieval-ready chunks and local vector search tests.

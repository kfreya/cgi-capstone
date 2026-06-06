# Week 5 Retrieval Backend Work

This week I focused on the retrieval backend and its user-facing behavior. The main goal was to make the Azure/Chroma path actually work on the full proposal corpus, while keeping the fallback path available and keeping the app output honest.

## What I changed

- Removed the hard cutoff that forced large corpora to fall back to local retrieval.
- Updated the Chroma rebuild path so large corpora are embedded in smaller batches instead of one huge request.
- Aligned the Azure client with CGI's endpoint style, including support for full Azure-style deployment paths.
- Kept the local fallback path in place so the app still works when Azure or Chroma is unavailable.
- Made the retrieval mode and retrieval status flow through the dashboard payload so the backend can explain which path was used.
- Kept the Streamlit RFP page aligned with the backend retrieval mode.

## What I verified

- Azure embedding smoke test passed.
- Preferred Azure/Chroma retrieval passed on the sample corpus.
- Preferred Azure/Chroma retrieval also passed on the full proposal corpus.
- `generate_assignment_context()` returned `retrieval_mode = "azure_chroma"` on the full corpus.
- The normal retrieval-related test suite passed.

## Validation results

- Azure embedding minimal test: `{'ok': True, 'vectors': 1, 'dim': 1536}`
- Preferred retrieval on sample corpus: `backend = azure_chroma`, `retrieval_mode = azure_chroma`
- Preferred retrieval on full corpus: `backend = azure_chroma`, `retrieval_mode = azure_chroma`, `chunks = 1216`
- `generate_assignment_context()` on full corpus: `retrieval_mode = azure_chroma`
- Targeted retrieval/backend tests: `66 passed`

## What this means

The retrieval backend is now actually usable on the full proposal corpus, not just on a tiny test sample. The code no longer pretends Azure/Chroma is available while silently using fallback for large inputs. Instead, it now tries the preferred path, rebuilds Chroma in batches, and falls back only when something really fails.

## Remaining note

The proposal corpus still does not provide reliable `opportunity_owner` or `opportunity_id` linkage for historical RFP evidence, so retrieved chunks should be treated as semantic similarity evidence rather than proof of a director's prior work.


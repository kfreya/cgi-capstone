# RFP Retrieval Backend Validation

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

## Current final behavior

After the Week 5 performance/stability fix, the interactive Streamlit path
does not rebuild Chroma on every **Analyze RFP** click. It reuses an existing
Chroma collection when Azure config, optional `chromadb`, and a reusable store
are available. Set `RFP_REBUILD_CHROMA=1` only for explicit backend validation
or maintenance rebuilds.

Local fallback retrieval remains the safe path when Azure/Chroma config,
dependencies, or store reuse are unavailable.

## What this means

The retrieval backend is usable on the full proposal corpus, not just on a tiny
test sample. The code no longer pretends Azure/Chroma is available while
silently using fallback for large inputs. Instead, it reports the retrieval mode
used by the request, reuses Chroma by default when a store is available, keeps
the batched rebuild path available for explicit rebuilds, and falls back locally
when the preferred path cannot run.

## Remaining note

Week 6 alias linkage can provide CRM traceability when CGI's `Json S-Num` /
`rfp_alias` metadata is present in the cleaned opportunity output and the
Chroma index has been rebuilt with that metadata. This linkage remains
supporting context for stakeholder review. It does not prove director
authorship, opportunity ownership, prior experience, or delivery responsibility,
and retrieved examples should still be treated as semantic/contextual evidence
rather than final assignment proof.

# Final RFP Evidence Validation

Historical note: this document records an earlier validation stage. For the
current Week 6 handoff workflow, see docs/rfp_week6_status.md and
docs/README.md.

This note records Kian's Sprint 4 issue #53 validation of the RFP retrieval
path. The purpose is to keep final demo/report claims evidence-backed and clear
about what the current metadata can and cannot prove.

## Validation Inputs

- Source data: `data/proposals_responses.json` loaded locally only.
- Preprocessing path: `preprocess_proposals()` from `src/rfp_preprocessor.py`.
- Evidence script: `scripts/generate_rfp_retrieval_evidence.py`.
- Generated artifacts:
  - `outputs/rfp_evidence/rfp_final_validation_summary.json`
  - `outputs/rfp_evidence/rfp_retrieval_evidence_examples.json`
  - `outputs/rfp_evidence/rfp_retrieval_path_comparison.json`
- Azure configuration used for this evidence run:
  - `AZURE_OPENAI_API_VERSION=2025-01-01-preview`
  - `AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large`
  - `AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o`

No API keys, endpoint values, raw proposal titles, or raw proposal text are
stored in the generated evidence artifacts.

## Final Data Validation Summary

The historical RFP corpus produced 1,216 retrieval chunks from 19 proposal
records and 46 extracted proposal/response documents.

| Check | Result |
| --- | ---: |
| Total chunks evaluated | 1,216 |
| Chunks with text | 1,216 |
| Chunks with proposal IDs | 1,216 |
| Chunks with document IDs | 1,216 |
| Proposal chunks | 449 |
| Proposal response chunks | 767 |
| Chunks with `opportunity_owner` | 0 |
| Chunks with `opportunity_id` | 0 |

The current chunk metadata supports traceability back to anonymized proposal
and document IDs. It does not support traceability to CRM opportunities or
director ownership.

## Retrieval Evidence Examples

The evidence script evaluates eight representative query themes:

1. cloud migration
2. managed services
3. data analytics dashboard
4. cybersecurity compliance
5. application modernization
6. service desk support
7. change management training
8. short vague request

For each theme, the artifact records the input query, top retrieved chunk IDs,
whether the result looks relevant based on expected theme terms, whether the
chunk supports the displayed summary or match reason, and any weak/misleading
retrieval notes.

The Azure/Chroma path was available in this run over a representative 64-chunk
subset. The subset is intentional: full-corpus Azure embedding generation hit
the Azure S0 embedding rate limit, while the subset still validates the
architecture path from Azure embeddings to Chroma query output.

Observed examples:

| Query theme | Azure/Chroma top chunks | Evidence note |
| --- | --- | --- |
| cloud migration | `proposal_004__document_015__chunk_003`, `proposal_004__document_015__chunk_002`, `proposal_017__document_041__chunk_002` | Top result was weak because no expected theme term matched; second and third results had partial support. |
| managed services | `proposal_017__document_041__chunk_001`, `proposal_016__document_039__chunk_001`, `proposal_004__document_015__chunk_003` | Relevant; returned chunks matched services/support or managed/services terms. |
| data analytics dashboard | `proposal_009__document_025__chunk_002`, `proposal_009__document_025__chunk_001`, `proposal_013__document_033__chunk_001` | Relevant; returned chunks matched analytics/data/reporting terms. |
| cybersecurity compliance | `proposal_005__document_017__chunk_002`, `proposal_007__document_021__chunk_004`, `proposal_016__document_039__chunk_001` | Relevant; returned chunks matched cybersecurity/security/compliance/privacy/risk terms. |

The evidence rows intentionally use redacted previews such as
`[redacted: 3570 chars, 3 matched expected terms]` instead of raw supporting
text. This keeps the artifacts safe to share while preserving enough information
to audit relevance labels.

## Azure/Chroma vs Local Fallback Comparison

The script compares Azure/Chroma against local fallback retrieval for three
sample themes: cloud migration, managed services, and data analytics dashboard.

For this run, both paths returned results, but the top results did not overlap
for the three comparison queries. This is expected because the Azure/Chroma run
used a 64-chunk representative subset while local fallback searched the full
1,216-chunk corpus. The correct interpretation is:

- Azure/Chroma mechanics are working for embedding, Chroma indexing, and query.
- The current comparison is not a full-corpus quality benchmark.
- Divergent top results must be manually reviewed before using them as final
  narrative evidence.
- Local fallback remains the safer full-corpus evidence source when Azure
  quota/rate limits prevent full historical indexing.

## Claim Support Assessment

Supported:

- The tool can say a new RFP is semantically similar to retrieved historical
  proposal/response chunks.
- The tool can show anonymized proposal IDs, document IDs, source type, chunk
  IDs, similarity scores, matched theme terms, and weak-result notes.

Not supported:

- The tool cannot say a recommended director has proven experience from a
  retrieved proposal chunk, because all chunks have null/missing
  `opportunity_owner` metadata.
- The tool cannot say a retrieved chunk is linked to a CRM opportunity, because
  all chunks have null/missing `opportunity_id` metadata.
- The tool cannot present Azure/Chroma retrieval as fully quality-benchmarked
  over the entire historical corpus until rate limits or persisted indexing are
  resolved for all 1,216 chunks.

## Final Report Wording

Use:

> The RFP Assignment Tool retrieves semantically similar historical
> proposal/response chunks and combines those examples with capacity signals to
> support assignment discussion.

Avoid:

> The RFP Assignment Tool proves that a recommended director worked on the
> retrieved historical opportunity.

Use:

> Director match reasons are heuristic and should be read as capacity plus
> service-domain fit, not validated prior ownership of the retrieved proposals.

Avoid:

> Retrieved RFP evidence confirms director experience or CRM opportunity
> ownership.

## Final Caveats

- Semantic retrieval: relevance is based on embeddings or keyword-style local
  fallback similarity, not stakeholder-approved ground truth labels.
- Incomplete metadata: proposal and document IDs are present, but director and
  CRM opportunity linkage fields are not populated in `proposals_responses.json`.
- Unsupported director-experience claims: do not describe retrieved chunks as
  proof of director experience unless future data links chunks to validated
  director/opportunity records.
- Historical proposal coverage: the corpus has 19 historical proposal records,
  so retrieval can support demo/report examples but should not be framed as
  comprehensive CGI coverage.
- Azure quota: Azure/Chroma smoke and representative-subset evidence passed,
  but full-corpus Azure embedding generation may require batching, retries, or a
  persisted prebuilt index to avoid rate limits.

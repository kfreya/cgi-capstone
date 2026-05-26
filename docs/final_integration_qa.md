# Final Integration QA and Scope Freeze

## 1. Final Prototype Scope Statement

CGI Capacity Analyzer is a final capstone prototype for stakeholder-facing
review, handoff, and demonstration. The prototype focuses on two core
deliverables:

1. Director Capacity Dashboard
2. RFP Assignment Tool

The Director Capacity Dashboard uses cleaned opportunity data, capacity scoring,
`director_capacity_df`, and Streamlit display components to help stakeholders
inspect relative director workload and capacity signals.

The RFP Assignment Tool uses pasted RFP text, chunking, retrieved examples,
`assignment_context`, `recommended_directors`, `risk_flags`, and Streamlit
display components to show how future RFP assignment support could work. The
current Streamlit RFP demo path remains a fallback / heuristic prototype unless
Azure-backed Chroma retrieval is fully tested and integrated.

The project is scoped as a transparent final prototype, not a production system
or final business decision engine.

## 2. What the Prototype Can Honestly Claim

- Provides a working Streamlit prototype for the Director Capacity Dashboard.
- Uses cleaned opportunity data and documented capacity scoring logic.
- Produces a director-level capacity table through `director_capacity_df`.
- Shows capacity labels, relative load, and supporting workload indicators.
- Provides a working Streamlit RFP Assignment Tool page for pasted RFP text.
- Supports the official fallback RFP demo path using local chunking, fallback
  retrieval, assignment context generation, and dashboard display.
- Preserves a stable dashboard-facing `assignment_context` structure with
  `retrieved_examples`, `recommended_directors`, and `risk_flags`.
- Documents where the prototype uses real data processing, heuristics,
  fallbacks, mocks, Azure embedding smoke-test success, and unvalidated
  Azure-backed retrieval components.
- Is suitable for final capstone demonstration and stakeholder discussion.

## 3. What the Prototype Should Not Claim

- It should not claim production readiness.
- It should not claim final CGI business validation or adoption.
- It should not claim the Streamlit RFP page is fully Azure-backed until the
  Azure + Chroma path is integrated into the RFP engine and Streamlit flow.
- It should not claim calibrated or stakeholder-approved ranking weights.
- It should not claim final CGI assignment guidance.
- It should not claim that director recommendations are authoritative staffing
  decisions.
- It should not claim that the capacity score represents exact working hours,
  calendar availability, utilization, or billable capacity.
- It should not claim Canada-wide coverage unless broader validated data is
  provided.

## 4. Official Demo Path

Official Week 4 fallback demo path:

```text
sample RFP text
-> chunking
-> local fallback retrieval
-> assignment_context with real capacity_df / director capacity output when available
-> Streamlit RFP page display
```

Preferred path once Azure-backed Chroma retrieval is integrated:

```text
sample RFP text
-> chunking
-> Azure OpenAI embeddings
-> Chroma retrieval
-> assignment_context with real capacity_df / director capacity output
-> Streamlit RFP page display
```

The fallback path remains the official Week 4 Streamlit demo path unless Azure
+ Chroma retrieval is integrated into the RFP engine and Streamlit flow. Azure
embedding access and a sample Azure + Chroma retrieval smoke test have passed,
but the Streamlit RFP page should not yet be described as fully Azure-backed. In
both paths, the RFP Assignment Tool should pass real capacity data into
`generate_assignment_context()` when available so
`recommended_directors` is capacity-aware. Fallback or mock director data should
only be used when real capacity data cannot be loaded, and the UI/report should
clearly label which data source is being used.

## 5. Integration QA Checklist

- [ ] Confirm the app runs from the repository root.
- [ ] Confirm the Director Capacity Dashboard loads cleaned opportunity data.
- [ ] Confirm capacity scoring produces `director_capacity_df`.
- [ ] Confirm the Streamlit dashboard renders director capacity results.
- [ ] Confirm dashboard labels and explanations do not imply exact utilization.
- [ ] Confirm the RFP page accepts pasted sample RFP text.
- [ ] Confirm empty or whitespace-only RFP input is handled with a warning.
- [ ] Confirm RFP text is chunked before retrieval.
- [ ] Confirm local fallback retrieval returns dashboard-facing examples.
- [ ] Confirm the RFP Assignment Tool passes real `capacity_df` /
  `director_capacity_df` output into `generate_assignment_context()` when
  available.
- [ ] Confirm fallback or mock director data is used only when real capacity
  data cannot be loaded.
- [ ] Confirm `recommended_directors` reflects available capacity data in the
  final demo path.
- [ ] Confirm `assignment_context` includes expected top-level keys.
- [ ] Confirm `recommended_directors` is present as a list.
- [ ] Confirm `risk_flags` is present as a list.
- [ ] Confirm the UI/report labels whether recommendations are based on real
  capacity data or fallback/mock director data.
- [ ] Confirm fallback / heuristic labels are visible in report notes or UI.
- [ ] Confirm Azure keys, endpoints, and secret values are not printed.
- [ ] Confirm Azure + Chroma smoke-test success is not presented as a fully
  Azure-backed Streamlit RFP flow.

### Recorded Local QA Results

Recorded local QA commands and results:

| Area | Command | Result |
| --- | --- | --- |
| App syntax check | `python -m py_compile app/app.py` | Passed |
| RFP-related tests | `python -m pytest tests/test_rfp_preprocessor.py tests/test_vector_store.py tests/test_rfp_engine.py` | 32 passed in 2.67s |
| Azure client mocked tests | `python -m pytest tests/test_azure_client.py` | 9 passed |
| Full test suite | `python -m pytest` | 108 passed, 2 warnings in 2.00s |
| Azure + Chroma smoke test | `python scripts/smoke_azure_chroma.py` | `stored_chunks: 3`; `query_result_count: 2`; top result `smoke-cloud-modernization`; `first_result_mentions_cloud: True` |

Azure environment check:

```bash
python src/check_env.py
```

Result:

```text
AZURE_OPENAI_API_KEY: FOUND
AZURE_OPENAI_EMBEDDINGS_ENDPOINT: FOUND
AZURE_OPENAI_ENDPOINT: FOUND
AZURE_OPENAI_REASONING_ENDPOINT: FOUND
AZURE_OPENAI_API_VERSION: FOUND
AZURE_OPENAI_EMBEDDING_DEPLOYMENT: FOUND
AZURE_OPENAI_CHAT_DEPLOYMENT: FOUND
```

CGI provided the missing Azure configuration values during Week 4. The local
`data/.env` was updated only in the local environment; no API keys, endpoints,
or secret values are included in this document.

`conda run -n cgi-capstone python -m pytest` was attempted, but that
environment did not currently have `pytest` installed. The recorded full-suite
result therefore uses the active local Python environment.

The two warnings came from `src/capacity_engine.py` around a `FutureWarning` in
`combine_first` behavior. They did not fail the tests.

Azure is no longer blocked at the environment/configuration level. Minimal real
Azure embedding smoke testing passed with `embedding_count: 1`,
`embedding_dimension: 1536`, and `first_vector_is_numeric: True`. A sample
Azure + Chroma smoke test also passed with precomputed Azure embeddings,
confirming Chroma add/query behavior at smoke-test level.

Azure + Chroma smoke test result:

```text
stored_chunks: 3
query_result_count: 2
top_ids: ['smoke-cloud-modernization', 'smoke-cybersecurity-assessment']
top_distances: [0.37519320845603943, 1.1962010860443115]
top_document_preview: Cloud migration support for application modernization, managed services transition, and platform operations.
first_result_mentions_cloud: True
```

The top retrieval result matched the cloud migration / managed services query
direction. This does not mean the Streamlit RFP page is fully Azure-backed.

The successful test results confirm that the fallback RFP path,
`assignment_context` tests, vector store tests, Azure client mocked tests,
capacity engine tests, data validator tests, and opportunity cleaner tests are
currently passing.

Azure embedding endpoint implementation result:

- `src/azure_client.py` keeps the general Azure client on
  `AZURE_OPENAI_ENDPOINT`.
- A separate embedding client uses `AZURE_OPENAI_EMBEDDINGS_ENDPOINT` for
  embedding calls.
- `embed_texts()` now uses the embedding endpoint client.
- `tests/test_azure_client.py` uses mocked tests to verify general endpoint vs
  embedding endpoint behavior without calling Azure.

Validation after the Azure embedding endpoint update:

| Area | Command | Result |
| --- | --- | --- |
| Azure client mocked tests | `python -m pytest tests/test_azure_client.py` | 9 passed |
| Azure client syntax check | `python -m py_compile src/azure_client.py tests/test_azure_client.py` | Passed |
| Minimal real Azure embedding smoke test | Embedding-only smoke test | `embedding_count: 1`; `embedding_dimension: 1536`; `first_vector_is_numeric: True` |
| Azure + Chroma smoke test | `python scripts/smoke_azure_chroma.py` | `stored_chunks: 3`; `query_result_count: 2`; top result matched cloud query direction |

Week 4 capacity-aware RFP integration result:

- `app/app.py` now passes the loaded `capacity_df` into
  `generate_assignment_context()` using `director_df=capacity_df`.
- The RFP page stores the recommendation capacity data source in
  `st.session_state["rfp_capacity_data_source"]`.
- The RFP results area labels whether director recommendations use Live CRM
  capacity data, Pre-built `director_capacity_df.csv`, or Synthetic
  mock/fallback capacity data.
- If mock capacity data is used, the UI warns that recommendations should not
  be treated as final CGI assignment guidance.
- This closes the Week 4 integration gap where the RFP page previously called
  `generate_assignment_context(rfp_text)` without passing director capacity
  data.

Validation after the capacity-aware RFP page update:

| Area | Command | Result |
| --- | --- | --- |
| App syntax check | `python -m py_compile app/app.py` | Passed |
| RFP-related tests | `python -m pytest tests/test_rfp_preprocessor.py tests/test_vector_store.py tests/test_rfp_engine.py` | 32 passed in 2.10s |
| Full test suite | `python -m pytest` | 108 passed, 2 warnings in 1.86s |

### Manual Streamlit Demo Check

Manual demo result:

- The Streamlit app launched successfully.
- Director Capacity Dashboard loaded with Live CRM data and 24 owners.
- RFP Assignment Tool loaded with Live CRM data.
- A sample public-sector digital transformation RFP was pasted and analyzed
  successfully without traceback.
- The RFP result showed:
  - RFP summary
  - Estimated Effort: Medium
  - Estimated duration: 3-5 weeks
  - Similar historical RFPs / retrieved examples
  - 3 recommended directors
  - 3 risk flags
- The Recommended Directors section displayed capacity label, capacity score,
  relative load, assignment score, match reason, capacity explanation,
  experience match explanation, and supporting chunks.
- The UI labelled that director recommendations were using Live CRM capacity
  data.
- The risk flags clearly warned that the built-in sample historical corpus was
  used because real historical proposal data was unavailable in this demo run.
- Retrieval remains local fallback / heuristic while Azure-backed retrieval is
  pending.

This manual demo confirms the capacity-aware Streamlit flow, but it does not
claim Azure-backed retrieval or validated real historical proposal retrieval.
The demo combines live capacity data with fallback/sample retrieval evidence.

## 6. Demo Checklist

- [ ] Start Streamlit from the repository root.
- [ ] Open the Director Capacity Dashboard.
- [ ] Show director-level capacity status and supporting workload indicators.
- [ ] Explain that capacity is an interpreted workload signal, not exact
  utilization.
- [ ] Open the RFP Assignment Tool.
- [ ] Paste the approved sample RFP text.
- [ ] Run the RFP analysis.
- [ ] Show retrieved examples, estimated effort, recommended directors, and risk
  flags.
- [ ] State that the RFP retrieval path is currently fallback / heuristic unless
  Azure-backed Chroma retrieval is fully tested and integrated.
- [ ] Close by framing the tool as a stakeholder-facing final prototype.

## 7. Architecture Compliance Notes

- The prototype aligns with the documented two-deliverable architecture:
  Director Capacity Dashboard and RFP Assignment Tool.
- Numeric capacity scoring is based on structured opportunity data, not LLM
  reasoning.
- The RFP workflow keeps retrieval and assignment context generation separate
  from Streamlit display.
- The RFP page consumes a stable `assignment_context` object rather than
  hard-coding display-only values.
- Azure OpenAI is treated as the preferred embedding path, but local fallback
  retrieval remains available to keep the final demo reproducible.
- The prototype preserves transparent labels for assumptions, heuristics, and
  unvalidated integrations.

## 8. Real vs Heuristic vs Fallback vs Mock vs Unvalidated Components

| Component | Status | Notes |
| --- | --- | --- |
| Opportunity cleaning | Real local processing | Uses available opportunity files and documented cleaning logic. |
| Capacity scoring | Heuristic model over real structured data | Produces interpretable workload signals, not exact utilization. |
| `director_capacity_df` | Real prototype output | Used by the Streamlit capacity dashboard. |
| Streamlit capacity display | Real prototype UI | Stakeholder-facing dashboard view. |
| RFP text input | Real prototype UI | Uses pasted RFP text in Streamlit. |
| RFP chunking | Real local code | Splits input text into retrievable chunks. |
| Local RFP retrieval | Fallback | Official Week 4 fallback demo retrieval path. |
| `assignment_context` | Real prototype contract | Contains summary, effort, examples, recommendations, risks, and notes. |
| Recommended directors | Heuristic / fallback-sensitive | Should not be presented as final CGI assignment guidance. |
| Risk flags | Heuristic prototype | Helps surface uncertainty and limitations. |
| Azure OpenAI embeddings | Smoke-test validated | Environment/configuration is available; minimal embedding test returned one numeric 1536-dimension vector. |
| Azure + Chroma sample retrieval | Smoke-test validated | `scripts/smoke_azure_chroma.py` added/query-tested three chunks with precomputed Azure embeddings; top result matched the cloud query direction. |
| Streamlit Azure-backed RFP retrieval | Not yet integrated | The RFP page remains fallback/local unless the Azure + Chroma path is connected through the RFP engine and Streamlit flow. |
| Azure chat deployment | Config available / not part of embedding smoke test | Chat deployment is configured but not required for embedding-only smoke testing. |
| Sample or placeholder director data | Mock / fallback when used | Only applies when real `capacity_df` is unavailable. |

## 9. Final Limitations and Caveats

- The capacity model is an interpretable heuristic based on available
  opportunity data.
- The prototype does not include calendar data, timesheets, confirmed staffing
  plans, or validated utilization targets.
- Director assignment recommendations are not final CGI staffing guidance.
- RFP ranking and effort logic are not calibrated against stakeholder-approved
  outcomes.
- Azure embedding access and sample Azure + Chroma add/query retrieval have
  passed smoke testing.
- The Streamlit RFP page is not yet fully Azure-backed; the Azure + Chroma path
  still needs integration into the RFP engine and Streamlit flow.
- Local fallback retrieval supports demonstration but should be clearly labelled
  as fallback behavior.
- Smoke-test success should not be presented as production readiness or
  business-validated retrieval.
- Business decisions should not be made directly from prototype output without
  stakeholder review, validation, and production hardening.

## 10. Reproducibility Notes

- Run commands from the repository root.
- Keep private data files and `data/.env` local and out of Git.
- Required Azure embedding smoke-test variables are now present locally:
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_EMBEDDINGS_ENDPOINT`
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_REASONING_ENDPOINT`
  - `AZURE_OPENAI_API_VERSION`
  - `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
  - `AZURE_OPENAI_CHAT_DEPLOYMENT`
- The minimal Azure embedding smoke test has passed.
- Run the sample Azure + Chroma smoke test with:
  `python scripts/smoke_azure_chroma.py`
- The Azure + Chroma smoke test stores three sample chunks, queries top two
  results, and confirms the first result mentions cloud.
- Keep the official Streamlit demo on fallback/local retrieval unless Azure +
  Chroma retrieval is integrated into the RFP engine and Streamlit flow.
- Record smoke-test results without printing secrets, endpoints, or raw private
  data.

## 11. Week 4 Integration Report Notes

- The final integration position is scope freeze, not feature expansion.
- The team should prioritize a stable demo path, clear limitations, and
  reproducible handoff notes.
- The Director Capacity Dashboard is the primary structured-data deliverable.
- The RFP Assignment Tool is a transparent assignment-support prototype with a
  fallback-first final demo path.
- Passing real `capacity_df` / director capacity output into
  `generate_assignment_context()` is a Week 4 integration priority because
  final demo `recommended_directors` should be capacity-aware when capacity data
  can be loaded.
- Fallback or mock director data should be reserved for cases where real
  capacity data is unavailable, and final report language should clearly label
  which recommendation source was used.
- Azure is no longer blocked at the environment/configuration level; embedding
  access and sample Azure + Chroma retrieval have passed smoke tests.
- Azure-backed Chroma retrieval should still be described as not integrated into
  the official Streamlit RFP path until connected through the RFP engine and
  Streamlit flow.
- Final report language should emphasize stakeholder-facing transparency,
  explainability, and capstone prototype status.
- Any final demo output should distinguish real data processing from heuristic
  scoring, fallback/sample retrieval evidence, Azure embedding and Chroma
  smoke-test success, mock placeholders, and unintegrated Azure-backed
  Streamlit retrieval.

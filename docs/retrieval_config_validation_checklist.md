# Retrieval and Config Validation Checklist

This note records the current retrieval/config checks for Week 5. I kept the wording practical and split the results into pass / fail / still-needs-manual-check so it is easy to share with the team.

## Scope

The checks below focus on:

- local Azure config readability
- Azure embedding smoke testing
- Azure + Chroma retrieval smoke testing
- fallback behavior and retrieval mode reporting
- user-facing wording consistency

## Results

| Check | Result | Notes | Blocker? |
|---|---|---|---|
| `python src/check_env.py` | Pass | Azure env vars are readable locally. The current environment reports `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_EMBEDDINGS_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_REASONING_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, and `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` as present. | No |
| Azure embedding smoke test | Pass | Minimal embedding call returned `{'ok': True, 'vectors': 1, 'dim': 1536}`. This confirms the Azure embedding client is working at smoke-test level. | No |
| Azure + Chroma sample smoke test | Pass | `preferred_retrieval_report('Need cloud migration and dashboard support.', top_k=1)` returned `backend = azure_chroma`, `retrieval_mode = azure_chroma`, and `preferred_path_ready = True`. | No |
| Azure + Chroma full-corpus smoke test | Pass | Full corpus retrieval used `1216` proposal chunks, built a Chroma store with `local_store_size = 1216`, and still returned `retrieval_mode = azure_chroma`. | No |
| `python scripts/smoke_azure_chroma.py` | Fail in current run | The script currently exits with `openai.APIConnectionError: Connection error.` while embedding the sample chunks. This is worth a follow-up check because the lower-level embedding and retrieval calls are otherwise passing. | Yes |
| Retrieval mode/status in RFP output | Pass | `generate_assignment_context('Need cloud migration and dashboard support.', _chat_fn=None)` returned `retrieval_mode = azure_chroma`. The retrieval status also reports `corpus_source = proposal_corpus`, `corpus_chunk_count = 1216`, and `retrieval_has_director_linkage = False`. | No |
| Fallback behavior | Pass | The code still preserves a local fallback path, and the retrieval status / notes clearly distinguish fallback from `azure_chroma`. | No |
| Streamlit wording | Pass with manual-code confirmation | The RFP page now reads the retrieval mode from backend output instead of always saying Azure is not integrated. It only labels Azure/Chroma as active when the backend actually returns that mode. | No |

## Key caveat

Azure embedding and Azure + Chroma retrieval are validated at smoke-test / sample level unless full Streamlit integration is explicitly tested in the browser. In other words, the backend path is working, but if we want to claim the entire app flow is verified, we should still do one explicit UI run.

## Short summary

- Azure config is readable locally.
- Azure embedding smoke test passes.
- Azure + Chroma retrieval passes on both sample and full corpus.
- `generate_assignment_context()` reports `azure_chroma` correctly.
- The one outstanding item from the scripted checks is `scripts/smoke_azure_chroma.py`, which currently needs a follow-up because it exits with a connection error even though the direct embedding/retrieval calls succeed.


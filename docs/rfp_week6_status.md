# RFP Week 6 Status

## Scope

Week 6 focuses on client data replacement and handoff support. The goal is to
make it easier for CGI to place local opportunity spreadsheets, rerun
preprocessing, and launch the app without changing the capacity-scoring formula
or RFP assignment-ranking logic.

Goals:

- Review the preprocessing CLI from a CGI user's perspective.
- Check common failure cases and error-message clarity.
- Confirm local data and generated outputs are not committed.
- Confirm documentation explains preprocessing before launching Streamlit.
- Record usability findings and troubleshooting guidance.

## Current Status

- The opportunity cleaner supports configurable spreadsheet paths, sheet name,
  and output directory.
- The no-argument workflow remains available with the existing default paths.
- CGI's `Json S-Num` field is normalized to `rfp_alias`.
- `has_rfp_alias` indicates whether a cleaned CRM row contains an alias.
- The orange Excel highlighting is visual context only and is not used by the
  preprocessing pipeline.
- Processed outputs remain under `data/processed/` by default.
- The Streamlit dashboard continues to load processed CRM-derived capacity data.
- The RFP page continues to support Azure/Chroma retrieval when configuration,
  optional Chroma dependencies, and a reusable Chroma collection are available;
  local fallback retrieval remains supported otherwise.
- Focused preprocessing, RFP, and retrieval regression checks passed after the
  latest integration (`89 passed`; one external package deprecation warning).

## Client Data Replacement Command

CGI can run preprocessing with explicit local spreadsheet paths:

```bash
python -m src.opportunity_cleaner \
  --opps1-path data/csv_files/<opps1_file>.xlsx \
  --opps2-path data/csv_files/<opps2_file>.xlsx \
  --sheet-name Data \
  --output-dir data/processed
```

The default demo/local workflow remains:

```bash
python -m src.opportunity_cleaner
```

Preprocessing should complete before Streamlit is launched so the dashboard can
read the latest processed CRM-derived outputs.

## Handoff Checks

### Expected workflow

1. Place both opportunity spreadsheets under a local `data/` path.
2. Confirm the workbook sheet name, normally `Data`.
3. Run `src.opportunity_cleaner` with the appropriate paths.
4. Confirm CSV outputs were generated under `data/processed/`.
5. Launch Streamlit.
6. Confirm the Director Capacity Dashboard loads.
7. Confirm the RFP Assignment Tool loads and can analyze pasted or uploaded text.

### Troubleshooting

#### Wrong spreadsheet path

- Symptom: preprocessing fails with a missing-file error, or no new processed
  CSVs appear under `data/processed/`.
- Likely cause: one or both command-line paths do not match the local workbook
  filenames or location.
- Recommended fix: confirm both files exist locally and rerun preprocessing with
  explicit paths:

```bash
python -m src.opportunity_cleaner \
  --opps1-path data/csv_files/<opps1_file>.xlsx \
  --opps2-path data/csv_files/<opps2_file>.xlsx \
  --sheet-name Data \
  --output-dir data/processed
```

#### Missing `Data` sheet

- Symptom: preprocessing fails with an error that the requested sheet cannot be
  read.
- Likely cause: the workbook sheet is named differently from `Data`, or the
  wrong workbook was provided.
- Recommended fix: confirm the sheet name in both local workbooks. If CGI uses a
  different sheet name, pass that name with `--sheet-name`; otherwise use:

```bash
python -m src.opportunity_cleaner
```

or the explicit-path command with `--sheet-name Data`.

#### Only one opportunity spreadsheet provided

- Symptom: preprocessing reports a missing required opportunity file, or merge
  outputs are not generated.
- Likely cause: the cleaner expects both opportunity spreadsheets because the
  merge and audit outputs compare the two source tables.
- Recommended fix: place both local spreadsheets under the expected local path
  or provide both `--opps1-path` and `--opps2-path` values in the custom command.

#### Missing `Json S-Num` / `rfp_alias` column

- Symptom: processed CRM outputs are created, but `rfp_alias` is empty or
  `has_rfp_alias` is false for all rows; RFP-to-CRM linkage fields are missing
  from retrieved proposal metadata.
- Likely cause: the source workbook does not include `Json S-Num`, the column
  name changed, or the local processed output was generated from an older file.
- Recommended fix: confirm whether CGI included the alias/linkage column, then
  rerun preprocessing. `Json S-Num` / `rfp_alias` supports linkage review and
  RFP-to-CRM traceability only; alias linkage does not prove director ownership,
  prior experience, authorship, or delivery responsibility.

#### Empty or missing processed outputs

- Symptom: the dashboard falls back to older processed data, prebuilt output, or
  mock data; expected files such as `cleaned_opportunity_df.csv` are absent or
  empty under `data/processed/`.
- Likely cause: preprocessing was not run after replacing local spreadsheets, it
  failed before writing outputs, or the output directory points somewhere else.
- Recommended fix: rerun preprocessing and confirm the command prints local
  output paths:

```bash
python -m src.opportunity_cleaner
```

For non-default filenames, use the explicit-path command above. Actual CGI
spreadsheets and generated processed outputs must remain local and should not be
committed.

#### Stale Chroma index

- Symptom: Azure/Chroma retrieval returns old examples, omits new linkage
  metadata, or falls back locally even though Azure configuration is present.
- Likely cause: the reusable Chroma collection was built before the proposal
  corpus, RFP-to-CRM linkage metadata, embedding settings, or local vector store
  contents changed.
- Recommended fix: rebuild the local Chroma index from the repository root:

```bash
python scripts/build_rfp_chroma_index.py
```

For explicit maintenance/debug validation of the Streamlit path, launch with:

```bash
RFP_REBUILD_CHROMA=1 streamlit run app/app.py
```

Normal Streamlit use should reuse an existing collection. Do not assume
Azure/Chroma metadata updates automatically without rebuilding the index.

## RFP Alias Interpretation

`Json S-Num` / `rfp_alias` connects a proposal corpus entry to CRM opportunity
context when the alias is present. It supports linkage review and RFP-to-CRM
traceability. Linked metadata can include:

- `opportunity_id`
- `opportunity_owner`
- `opportunity_manager`
- `service_solution`

This is stronger than semantic similarity alone for traceability review, but it
should still be described conservatively. `opportunity_owner` shows CRM
opportunity context; it does not prove director ownership, prior experience,
proposal authorship, or delivery responsibility. Retrieved examples are
supporting semantic/contextual evidence, not final assignment proof.

## Data Safety

- Keep actual CGI spreadsheets, proposal JSON, credentials, and generated
  processed outputs local.
- Do not commit files under private `data/` paths.
- Do not place Azure keys directly in source code.
- Keep local credentials in the ignored environment file.
- Tests should use synthetic fixtures rather than CGI client data.
- The prototype remains a decision-support tool and should not be treated as a
  final staffing or assignment authority.

## Remaining Handoff Notes

- A dedicated, concise client data replacement guide would make the final
  handoff easier to follow; current instructions are spread across the README
  and supporting QA documents.
- Dependency versions should ideally be pinned to reduce differences between
  CGI and team environments.
- The full Azure/Chroma proposal index should be built ahead of use where
  possible. Normal Streamlit use should reuse an existing collection; rebuilds
  should be treated as explicit maintenance/debug work.
- After replacing opportunity data, CGI should rerun preprocessing and validate
  the dashboard before using RFP recommendations as decision-support signals.

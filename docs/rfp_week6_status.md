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
- The RFP page continues to support Azure/Chroma retrieval and local fallback.
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


## RFP Alias Interpretation

`Json S-Num` / `rfp_alias` connects a proposal corpus entry to CRM opportunity
context when the alias is present. Linked metadata can include:

- `opportunity_id`
- `opportunity_owner`
- `opportunity_manager`
- `service_solution`

This is stronger than semantic similarity alone, but it should still be
described conservatively. `opportunity_owner` shows CRM opportunity ownership;
it does not prove that the person personally authored the proposal or delivered
all related work.

## Data Safety

- Keep actual CGI spreadsheets, proposal JSON, credentials, and generated
  processed outputs local.
- Do not commit files under private `data/` paths.
- Do not place Azure keys directly in source code.
- Keep local credentials in the ignored environment file.
- Tests should use synthetic fixtures rather than CGI client data.

## Remaining Handoff Notes

- A dedicated, concise client data replacement guide would make the final
  handoff easier to follow; current instructions are spread across the README
  and supporting QA documents.
- Dependency versions should ideally be pinned to reduce differences between
  CGI and team environments.
- The full Azure/Chroma proposal index should be built ahead of use where
  possible, because rebuilding a large corpus during an RFP analysis can make
  the Streamlit page appear unresponsive.
- After replacing opportunity data, CGI should rerun preprocessing and validate
  the dashboard before relying on RFP recommendations.


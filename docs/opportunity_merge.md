# Opportunity Merge

## Goal

Build the first reproducible merged opportunity dataset, `opportunity_df`, from the two anonymized CGI CRM exports.

## Input Files

- `data/csv_files/anonymized_opps_1.xlsx`
- `data/csv_files/anonymized_opps_2.xlsx`

These files are local-only and not committed.

## Project Plan / EDA Design Decision

`opps1` and `opps2` are different views of the same CRM opportunity data.

`opps2` is used as the base table because it has the richer CRM schema. `opps1` is used only to supplement selected fields:

- `opportunity_product`
- `service_solution`
- `service_solution_estimated_revenue`
- `opportunity_estimated_revenue_base_cad`
- `ip`
- `delivery_territory_center`

## Merge Strategy

- Normalize column names to `snake_case`.
- Use `opportunity_id` as the required join key.
- Use `opps2` as the base opportunity-level table.
- Collapse `opps1` supplemental fields to one row per `opportunity_id` before merging.
- Append `opps1`-exclusive opportunity IDs once each.
- Keep duplicate/detail rows in audit outputs instead of multiplying `opportunity_df`.
- Preserve diagnostics for duplicates, unmatched records, and `opps1`-exclusive records.

## Merge Summary

- join_key_used: opportunity_id
- opps1_row_count: 8435
- opps2_row_count: 8695
- opps1_unique_ids: 7679
- opps2_unique_ids: 8695
- matched_ids: 7628
- opps1_exclusive_ids: 51
- opps2_base_unmatched_ids: 1067
- expected_no_expansion_row_count: 8746
- opportunity_df_row_count: 8746
- row_count_matches_no_expansion: True
- duplicate_join_key_row_count: 0
- opps1_duplicate_id_count: 661
- opps1_duplicate_row_count: 1417
- opps2_duplicate_id_count: 0
- opps2_duplicate_row_count: 0
- supplemental_fields_found: opportunity_product, service_solution, service_solution_estimated_revenue, opportunity_estimated_revenue_base_cad, ip, delivery_territory_center

## Local Outputs Generated

Generated under `data/processed/`:

- `opportunity_df.csv`
- `cleaned_opportunity_df.csv`
- `owner_base_summary.csv`
- `schema_comparison.csv`
- `merge_summary.csv`
- `duplicate_records.csv`
- `opps1_duplicate_records.csv`
- `opps2_duplicate_records.csv`
- `opps1_supplemental_detail.csv`
- `opps1_exclusive_records.csv`
- `unmatched_records.csv`

These are local artifacts and should not be committed.

Running the opportunity output pipeline now produces both the original Week 1
merge artifacts and the Sprint 2 Role 1 handoff artifacts.
`cleaned_opportunity_df.csv` is the prepared opportunity-level handoff for
validation, scoring, and dashboard integration. `owner_base_summary.csv` is the
owner-level validation and scoring sanity-check handoff. All generated CSVs
under `data/processed/` remain local artifacts and should not be committed.

## Sprint 2 Cleaning Note

`opportunity_df` remains the Week 1 merged output: it preserves the original
opportunity-level merge, source diagnostics, unmatched records, and audit
artifacts.

`src/opportunity_cleaner.py::clean_opportunity_df()` creates the Sprint 2
cleaned/prepared dataframe from that merged output. This first non-breaking
cleaning pass preserves all existing columns, coerces known numeric and date
fields when present, and adds downstream-friendly flags for validation,
scoring, and dashboard use:

- `source_file_flag`
- `duplicate_flag`
- `unmatched_flag`
- `opps1_exclusive_flag`

It also adds lightweight data-quality flags for missing owner, probability,
revenue, duration, revenue start date, invalid probability/duration, and
calendar-date `close_date < created_on`.

The cleaned dataframe includes `authoritative_revenue` as the non-additive
opportunity-level revenue fallback:

```text
total_estimated_revenue
else opportunity_estimated_revenue_base_cad
```

`service_solution_estimated_revenue` remains separate and is not summed into
`authoritative_revenue`. Kian still owns validation and reliability review of
the revenue semantics.

`src/opportunity_cleaner.py::build_owner_base_summary()` creates the Sprint 2
Role 1 owner-level handoff artifact from `cleaned_opportunity_df`. It groups
records by `opportunity_owner` and summarizes opportunity counts, open/won/lost
counts using Kian's shared `classify_opportunity_outcome()` taxonomy,
missing-data counts, merge/source flags, and separate revenue totals. Under
that taxonomy Cancelled/Canceled are lost, while CRM Duplicated/Duplicate
outcomes are excluded from open/won/lost counts and remain separate from the
merge-level `duplicate_flag`.

This owner base summary is intended for Kian's validation checks and Lyken's
scoring sanity checks. It is not final capacity scoring: it does not compute
`capacity_score`, `relative_load`, or `capacity_label`. The final
`director_capacity_df` remains part of the scoring module work.

## Checks Completed

- `python -m src.opportunity_cleaner` completed successfully.
- `python -m pytest tests/test_opportunity_cleaner.py` passed with 6 tests.
- `data/processed` outputs are ignored by Git.
- Final `opportunity_df` preserves opportunity-level grain.

## Open Questions / Risks

- Role 2 should validate revenue, date, duration, probability, status, and `sales_stage` fields.
- The 1067 `opps2`-only opportunity IDs should be reviewed as part of unmatched/source coverage notes.
- `opps1` duplicate rows likely reflect service/product-level detail and are preserved in audit outputs.
- Need downstream users to avoid using `opps1_supplemental_detail.csv` as an opportunity-level scoring input.

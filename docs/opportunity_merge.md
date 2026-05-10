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
- supplemental_fields_found: opportunity_product, service_solution, service_solution_estimated_revenue, ip, delivery_territory_center

## Local Outputs Generated

Generated under `data/processed/`:

- `opportunity_df.csv`
- `schema_comparison.csv`
- `merge_summary.csv`
- `duplicate_records.csv`
- `opps1_duplicate_records.csv`
- `opps2_duplicate_records.csv`
- `opps1_supplemental_detail.csv`
- `opps1_exclusive_records.csv`
- `unmatched_records.csv`

These are local artifacts and should not be committed.

## Checks Completed

- `python src/opportunity_cleaner.py` completed successfully.
- `python -m pytest tests/test_opportunity_cleaner.py` passed with 6 tests.
- `data/processed` outputs are ignored by Git.
- Final `opportunity_df` preserves opportunity-level grain.

## Open Questions / Risks

- Role 2 should validate revenue, date, duration, probability, status, and `sales_stage` fields.
- The 1067 `opps2`-only opportunity IDs should be reviewed as part of unmatched/source coverage notes.
- `opps1` duplicate rows likely reflect service/product-level detail and are preserved in audit outputs.
- Need downstream users to avoid using `opps1_supplemental_detail.csv` as an opportunity-level scoring input.

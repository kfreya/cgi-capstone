# Week 2 Yixiao Data Integration Notes

## Goal

Yixiao's Week 2 Role 1 work turns the Week 1 merged opportunity dataset into a
cleaner handoff layer for validation, scoring sanity checks, and future
dashboard integration.

This work does not finalize validation, scoring, revenue reliability review, or
`director_capacity_df`.

## What Changed From Week 1

Week 1 produced the first reproducible merged opportunity dataset,
`opportunity_df`, from the two anonymized CRM exports. It also created schema,
merge, duplicate, unmatched, and opps1-exclusive audit outputs.

Week 2 keeps that merge logic intact and adds a non-breaking preparation layer:

- `clean_opportunity_df()` preserves all existing columns and adds Sprint 2
  alias flags, basic numeric/date coercion, and lightweight data-quality flags.
- `build_owner_base_summary()` creates an owner-level handoff summary grouped
  by `opportunity_owner`.
- `write_outputs()` now writes both Week 1 merge artifacts and Sprint 2 handoff
  artifacts.

## New Sprint 2 Outputs

Generated under `data/processed/` when the opportunity output pipeline is run:

- `cleaned_opportunity_df.csv`
- `owner_base_summary.csv`

These are generated local artifacts and should not be committed.

`cleaned_opportunity_df.csv` is the prepared opportunity-level handoff for
Kian's validation work, Lyken's scoring checks, and Freya's eventual dashboard
integration.

`owner_base_summary.csv` is an owner-level summary for validation and scoring
sanity checks. It is not a final capacity output.

## Key Functions Added

### `clean_opportunity_df(opportunity_df)`

Creates a cleaned/prepared copy of the Week 1 merged opportunity dataframe.

It adds:

- `source_file_flag`
- `duplicate_flag`
- `unmatched_flag`
- `opps1_exclusive_flag`
- missing/invalid data-quality flags for owner, probability, revenue, duration,
  revenue start date, and close-before-created anomalies

It also coerces known numeric and date fields when present and creates
`authoritative_revenue` using `total_estimated_revenue` first, then
`opportunity_estimated_revenue_base_cad` when the primary value is missing.
`service_solution_estimated_revenue` remains separate and is not summed.

### `build_owner_base_summary(cleaned_df)`

Creates an owner-level summary grouped by `opportunity_owner`.

It includes:

- opportunity counts
- simple open/won/lost status buckets using both `status` and `status_reason`
- average probability
- missing-data counts
- duplicate/unmatched/opps1-exclusive counts
- separate revenue sums for `total_estimated_revenue` and
  `opportunity_estimated_revenue_base_cad`

It does not compute `capacity_score`, `relative_load`, or `capacity_label`.

## Output Pipeline Behavior

`write_outputs()` still writes all existing Week 1 outputs:

- `opportunity_df.csv`
- `schema_comparison.csv`
- `merge_summary.csv`
- `duplicate_records.csv`
- `opps1_duplicate_records.csv`
- `opps2_duplicate_records.csv`
- `opps1_supplemental_detail.csv`
- `opps1_exclusive_records.csv`
- `unmatched_records.csv`

It now also writes the Sprint 2 handoff artifacts:

- `cleaned_opportunity_df.csv`
- `owner_base_summary.csv`

## Assumptions

- `opportunity_df` remains the canonical Week 1 merged output.
- `cleaned_opportunity_df` is an additive preparation layer, not a replacement
  for the merge audit trail.
- Blank or missing `opportunity_owner` values are grouped as `Unknown` in
  `owner_base_summary`.
- Owner summary status buckets use simple matching on both `status` and
  `status_reason` values such as open, in progress, active, won, lost,
  cancelled, canceled, duplicated, and duplicate.
- `authoritative_revenue` is a non-additive opportunity-level fallback:
  `total_estimated_revenue`, then `opportunity_estimated_revenue_base_cad`.
- `service_solution_estimated_revenue` remains separate.

## Unresolved Issues

- `service_solution_estimated_revenue` should not be summed with
  `total_estimated_revenue` unless validation confirms the semantics.
- Kian still owns validation and reliability review of the revenue fields.
- Final delivery-window fallback decisions remain validation/scoring work.
- Final capacity scoring and `director_capacity_df` remain scoring module work.
- Status bucket logic may need refinement after validation reviews CRM status
  conventions.

## What Kian Should Review Next

- Confirm data-quality flag definitions and whether more validation flags are
  needed.
- Review revenue field semantics and reliability of the `authoritative_revenue`
  fallback.
- Confirm whether `service_solution_estimated_revenue` is service-line detail
  or another opportunity-level candidate.
- Review date anomalies, especially `close_before_created_flag`.
- Use `owner_base_summary.csv` as a quick owner-level validation sanity check.

## What Lyken Should Know For Scoring

- Use `cleaned_opportunity_df.csv` as the prepared opportunity-level handoff,
  with `authoritative_revenue` available as the non-additive opportunity-level
  revenue fallback.
- `owner_base_summary.csv` is useful for sanity checks only. It is not a final
  scoring table.
- The cleaner does not compute `capacity_score`, `relative_load`, or
  `capacity_label`.
- Duration, probability, and revenue missingness flags can help quantify where
  fallback assumptions affect scoring.

## What Freya Should Know For Dashboard Integration

- `cleaned_opportunity_df.csv` contains downstream-friendly merge and
  data-quality flags that can support filters, badges, or QA views later.
- `owner_base_summary.csv` is an owner-level handoff table for validation and
  sanity checks, not the final dashboard capacity table.
- Final dashboard integration should wait for scoring output, including the
  eventual `director_capacity_df` or equivalent.

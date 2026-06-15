# Opportunity Cleaning

## Purpose

This document describes the prepared opportunity-level layer built from the
merged CRM opportunity dataset. The cleaning process keeps the raw merge output
intact while adding stable fields for validation, capacity scoring, and
dashboard integration.

The source table is `opportunity_df`, produced by the opportunity merge process.
The prepared output is `cleaned_opportunity_df`.

## Inputs and Outputs

Input:

- `data/processed/opportunity_df.csv`

Prepared outputs generated under `data/processed/`:

- `cleaned_opportunity_df.csv`
- `owner_base_summary.csv`

These CSV files are generated local artifacts and should not be committed.

`cleaned_opportunity_df.csv` is the opportunity-level input for validation,
capacity scoring, and dashboard loading. `owner_base_summary.csv` is an
owner-level sanity-check table for validation and scoring review; it is not the
final dashboard capacity table.

## Cleaning Function

`src/opportunity_cleaner.py::clean_opportunity_df(opportunity_df)` returns a
copy of the merged opportunity dataframe with additive preparation fields. It
does not mutate the input dataframe and does not remove the merge audit columns.

The function:

- preserves all existing columns from `opportunity_df`
- coerces known numeric fields when present
- coerces known date fields when present
- adds downstream-friendly source and merge flags
- adds lightweight data-quality flags
- creates `authoritative_revenue` using the opportunity-level revenue fallback
- preserves CGI's client-provided `Json S-Num` alias metadata when present as
  `json_s_num`, `rfp_alias`, and `has_rfp_alias`

## Prepared Fields

### Merge and Source Flags

The cleaned dataframe adds stable aliases for merge/source diagnostics:

- `source_file_flag`
- `duplicate_flag`
- `unmatched_flag`
- `opps1_exclusive_flag`

These fields make the merge provenance easier to use in validation summaries,
scoring checks, and future dashboard QA views.

`duplicate_flag` is the merge-level duplicate indicator. It is separate from
CRM outcome values such as `status_reason == "Duplicated"`.

### Data-Quality Flags

The cleaned dataframe adds lightweight quality flags for common downstream
risks:

- `missing_owner_flag`
- `missing_probability_flag`
- `invalid_probability_flag`
- `missing_revenue_flag`
- `missing_duration_flag`
- `invalid_duration_flag`
- `missing_revenue_start_date_flag`
- `close_before_created_flag`

`close_before_created_flag` uses a normalized calendar-date comparison so a
same-day created/closed record is not incorrectly flagged because of timestamp
granularity.

### RFP Alias Fields

When the opps1 source includes CGI's `Json S-Num` column, the cleaner preserves
it as `json_s_num` and exposes downstream-friendly linkage fields:

- `rfp_alias`
- `has_rfp_alias`

Missing alias values are allowed and should not break preprocessing, capacity
scoring, or dashboard loading. `Json S-Num` / `rfp_alias` supports linkage
review and RFP-to-CRM traceability only; it does not prove director authorship,
opportunity ownership, prior experience, or delivery responsibility.

### Authoritative Revenue

`authoritative_revenue` is a non-additive opportunity-level revenue field:

```text
authoritative_revenue =
    total_estimated_revenue
    else opportunity_estimated_revenue_base_cad
```

`service_solution_estimated_revenue` remains separate. It is not summed into
`authoritative_revenue` because it represents service/solution detail rather
than a confirmed opportunity-level replacement.

## Owner Base Summary

`src/opportunity_cleaner.py::build_owner_base_summary(cleaned_df)` creates an
owner-level validation and scoring sanity-check table from
`cleaned_opportunity_df`.

It summarizes:

- opportunity counts by `opportunity_owner`
- open, won, and lost counts using `src.data_validator.classify_opportunity_outcome()`
- duplicate, unmatched, and opps1-exclusive counts
- missing-data counts
- average probability
- separate revenue totals for `total_estimated_revenue` and
  `opportunity_estimated_revenue_base_cad`

The owner base summary does not compute `capacity_score`, `relative_load`, or
`capacity_label`. Final capacity scoring is produced by the capacity engine and
documented in `docs/capacity_scoring.md`.

## Assumptions

- `opportunity_df` remains the reproducible merged opportunity table and audit
  trail.
- `cleaned_opportunity_df` is an additive preparation layer, not a replacement
  for the merge output.
- Blank or missing `opportunity_owner` values are grouped as `Unknown` in
  `owner_base_summary`.
- Outcome buckets use `classify_opportunity_outcome()`: Open, Active, and In
  Progress count as open; Won counts as won; Lost, Cancelled, and Canceled count
  as lost; Duplicated and Duplicate are excluded from open/won/lost counts.
- The CRM duplicate outcome is separate from the merge-level `duplicate_flag`.
- `authoritative_revenue` uses the non-additive opportunity-level fallback
  described above.
- Missing `Json S-Num` / `rfp_alias` values are expected for some rows and
  should be treated as absent linkage metadata rather than preprocessing
  failures.

## Limitations

- `owner_base_summary.csv` is a validation and sanity-check artifact, not a
  dashboard-ready capacity output.
- `service_solution_estimated_revenue` should remain separate unless its
  semantics are confirmed as opportunity-level revenue.
- Final scoring behavior, capacity labels, and director-level dashboard output
  are owned by the capacity engine.

## Related Documentation

- `docs/opportunity_merge.md` documents the raw Excel merge and audit outputs.
- `docs/cleaned_opportunity_column_dictionary.md` documents the cleaned
  opportunity columns.
- `docs/data_validation.md` documents field reliability, fallback assumptions,
  and data-quality findings.
- `docs/capacity_scoring.md` documents the scoring model built on the cleaned
  opportunity data.

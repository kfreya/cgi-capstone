# Scoring Input Reliability

## Purpose

This document defines the stable input contract for capacity scoring. It
summarizes which fields in `cleaned_opportunity_df` can be used directly, which
fields require documented fallbacks, and which fields should not be used as
scoring inputs yet.

Detailed evidence and validation findings are maintained in
`docs/data_validation.md`. The machine-readable fallback rules are maintained in
`config/fallback_assumptions.yaml`.

Source data: `cleaned_opportunity_df`, the prepared opportunity-level table
produced by `src/opportunity_cleaner.py`.

## Field Reliability for Scoring

The ratings below are generated from
`build_field_reliability_report(cleaned_opportunity_df)` using null and anomaly
rates.

### Reliable: Use Directly

| Field | Fallback rule | Scoring note |
|---|---|---|
| `opportunity_owner` | none | Primary grouping key. |
| `opportunity_manager` | none | Retained as reporting metadata. |
| `status` | `status_reason_outcome` | Use only through `classify_opportunity_outcome()`. |
| `status_reason` | `status_reason_outcome` | Canonical outcome field; use the shared taxonomy helper. |
| `sales_stage` | `late_stage_definition` | Maps to the capacity engine stage-weight table. |
| `probability` | `missing_probability` | Null values should be neutralized to 0 for weighted pipeline calculations. |
| `created_on` | none | Drives historical baselines and `quarters_of_data`. |

### Use With Care: Apply Documented Fallbacks

| Field | Fallback rule | Scoring note |
|---|---|---|
| `total_estimated_revenue` | `revenue_hierarchy` | Primary opportunity-level revenue field. Explicit zero revenue contributes zero load. |
| `opportunity_estimated_revenue_base_cad` | `revenue_hierarchy` | Fallback opportunity-level revenue field when the primary is missing. |
| `close_date` | `delivery_window` | Fallback delivery-window start when `revenue_start_date` is missing. Do not use as a raw time-to-close metric until date anomalies are explained. |
| `revenue_start_date` | `delivery_window` | Preferred delivery-window start for won opportunities. |
| `project_duration_number_of_months` | `missing_duration` | Missing or non-positive durations use the documented duration fallback. Very long durations should be monitored because they can inflate duration-weighted terms. |

### Not Usable for Scoring Yet

| Field | Fallback rule | Scoring note |
|---|---|---|
| `service_solution_estimated_revenue` | `do_not_sum_service_solution_revenue` | Service/solution-level detail. Do not sum into opportunity-level scoring revenue. |

## Revenue Fallback Hierarchy

Capacity scoring should use `authoritative_revenue` when it is present in
`cleaned_opportunity_df`. The equivalent helper is
`src.data_validator.apply_revenue_hierarchy(df)`.

```text
authoritative_revenue =
    total_estimated_revenue                       if not null
    else opportunity_estimated_revenue_base_cad    if not null
    else missing
```

`service_solution_estimated_revenue` is not part of this hierarchy. It should
remain a separate field unless its semantics are confirmed as opportunity-level
revenue.

## Date and Duration Assumptions

Delivery-window scoring uses the following rule:

```text
delivery_start =
    revenue_start_date
    else close_date

delivery_end =
    delivery_start + project_duration_number_of_months
```

Capacity scoring should count delivery load only for opportunities classified
as won and active within the delivery window.

Missing or non-positive `project_duration_number_of_months` values use the
documented duration fallback. The current capacity engine uses a 12-month
fallback and clips duration below 1 month.

`close_date < created_on` is measured on normalized calendar dates. The flag is
useful for data-quality review, but it is not a blocker for the delivery-window
fallback because `close_date` is only used as a start-date fallback when needed.

## Outcome Taxonomy

Capacity scoring must use
`src.data_validator.classify_opportunity_outcome(df)` instead of local string
checks. The helper returns:

```text
won | lost | open | duplicate | unknown
```

Rules:

- `status_reason` is canonical.
- `status` is used only when `status_reason` is null or blank.
- Open, Active, and In Progress are open.
- Won is won.
- Lost, Cancelled, and Canceled are lost-like outcomes.
- Duplicated and Duplicate are their own duplicate bucket and are excluded from
  open/won/lost counts.

Scoring routes:

- `open` rows contribute to sales pipeline load.
- `won` rows can contribute to inferred delivery load if their delivery window
  is active.
- `lost`, `duplicate`, and `unknown` rows do not contribute to current load.

## Capacity-Scoring Assumptions

- Current sales load comes only from open pipeline opportunities.
- Current delivery load comes only from won opportunities that are active in
  the delivery window.
- Current owner load is the sum of current open sales load and active won
  delivery load.
- Historical baseline should use active-quarter workload, not lifetime
  cumulative load.
- Capacity labels are based on each owner's current load relative to that
  owner's historical baseline.
- Low-history owners may have unstable baselines; consumers should use
  `baseline_reliability` when interpreting scores.

## Reproduction

Run the validator report from a local environment with the project dependencies
installed:

```bash
python -c "from src.opportunity_cleaner import build_opportunity_df, clean_opportunity_df; \
from src.data_validator import build_field_reliability_report; \
opp, *_ = build_opportunity_df(); \
print(build_field_reliability_report(clean_opportunity_df(opp)))"
```

The contract tests live in `tests/test_data_validator.py`.

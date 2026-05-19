# Capacity Engine Integration

## Purpose

This document defines the integration contract for the capacity engine. It
describes the expected input shape, processing order, output artifacts,
downstream consumers, and test commands for the director capacity workflow.

Detailed scoring formulas are documented in `docs/capacity_scoring.md`. The
dashboard output schema is documented in
`docs/director_capacity_dashboard_column_dictionary.md`.

## Expected Input

The capacity engine expects a cleaned opportunity-level dataframe matching the
`cleaned_opportunity_df.csv` shape.

Required field families include:

- owner and identifier fields: `opportunity_owner`, `opportunity_id`
- outcome fields: `status`, `status_reason`
- sales fields: `sales_stage`, `probability`
- revenue fields: `authoritative_revenue` when available, otherwise
  `total_estimated_revenue` and `opportunity_estimated_revenue_base_cad`
- delivery-window fields: `project_duration_number_of_months`,
  `revenue_start_date`, `close_date`
- historical-baseline fields: `created_on`
- dashboard metadata: `delivery_territory_center`

Revenue scoring uses `authoritative_revenue` first. If that field is missing,
the engine falls back to `total_estimated_revenue` and then
`opportunity_estimated_revenue_base_cad`. `service_solution_estimated_revenue`
is never added to opportunity-level scoring revenue.

## Pipeline Order

`build_director_capacity_df(opportunity_df, current_date=None)` runs these
steps:

1. `compute_sales_load()` creates per-row `sales_load` using
   `classify_opportunity_outcome()`. Only open rows contribute.
2. `compute_delivery_load()` creates `delivery_load` and `delivery_active`.
   Only won rows inside the delivery window contribute.
3. `compute_current_load_by_owner()` aggregates the current open sales load and
   active won delivery load to one row per `opportunity_owner`.
4. `compute_historical_baseline()` builds active-quarter historical baseline
   metrics and caps the analysis at the current/as-of quarter.
5. `compute_relative_load()` compares current load with each owner's
   historical average load.
6. `compute_capacity_score()` converts relative load into a capped score.
7. `assign_capacity_label()` assigns a temporary relative-load band:
   `Available`, `Near Historical Norm`, `High Load`, `Overextended`, or
   `No baseline`.

The final output column order is fixed by
`DIRECTOR_CAPACITY_DASHBOARD_COLUMNS`. See
`docs/director_capacity_dashboard_column_dictionary.md` for the complete schema.

## Weighted Pipeline Revenue

Open-opportunity weighted pipeline revenue uses:

```text
authoritative_revenue * probability
```

Only opportunities classified as open contribute to weighted pipeline revenue.
Closed, won, lost, duplicate, and unknown outcomes contribute zero current
pipeline revenue.

## Output Artifacts

When `src/capacity_engine.py` is run as a script, it reads:

- `data/processed/cleaned_opportunity_df.csv`

It writes:

- `data/processed/director_capacity_df.csv`
- `data/processed/director_capacity_df_example.csv`

These generated CSVs are local artifacts and should not be committed.

## Dashboard Contract

The Streamlit Director Capacity page should consume the output of
`build_director_capacity_df()` directly. It should not re-aggregate the owner
rows.

The output guarantees:

- one row per `opportunity_owner`
- deterministic output for identical input and `current_date`
- no in-place mutation of the input dataframe
- columns strictly defined by `DIRECTOR_CAPACITY_DASHBOARD_COLUMNS`

The dashboard column contract lives in
`docs/director_capacity_dashboard_column_dictionary.md`.

## Workload Trend Contract

Trend charts should use:

```python
compute_quarterly_workload_by_owner(opportunity_df, as_of_date=...)
```

The trend output uses active-quarter workload and should be filtered to the
latest dashboard window, such as the last eight quarters ending at the current
or as-of quarter.

## Downstream Consumers

Primary consumers:

- Streamlit Director Capacity dashboard
- capacity score review and validation notebooks
- future RFP assignment ranking, where director capacity fields may be used as
  one input to recommendation logic

Downstream consumers should treat `director_capacity_df` as the reporting
interface, not as a raw feature table.

## Testing

Run the capacity engine tests with:

```bash
python -m pytest tests/test_capacity_engine.py
```

Run the full project suite with:

```bash
python -m pytest
```

The capacity tests cover sales-load gating, won-active delivery gating,
owner-level aggregation, historical baselines, relative load, capacity score,
capacity labels, and dashboard output columns.

## Integration Notes

- Missing probability or unmapped sales stage results in zero sales
  contribution.
- Missing delivery-window dates prevent delivery contribution.
- Missing or unusable baselines propagate a missing `capacity_score`.
- Missing or unusable baselines are labeled `No baseline` rather than forcing a
  capacity state.
- Fine-grained overload severity should be interpreted with `relative_load`,
  not only the discrete label.
- Current label thresholds are a temporary project-side decision based on the
  observed director-level distribution and business interpretation; they remain
  subject to CGI judgment.
- Dashboard row-level filters narrow the current opportunity workload being
  viewed. Historical baselines remain anchored to the full selected
  owner/territory history so `relative_load` still compares filtered current
  work against a stable historical norm.

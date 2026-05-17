# Capacity engine — integration notes

## Upstream input

- Expected dataframe: cleaned opportunity extract (from Yixiao, `cleaned_opportunity_df.csv` shape), including at minimum the columns referenced by load and aggregation (`opportunity_owner`, `status_reason`, `sales_stage`, `probability`, revenue fields, `project_duration_number_of_months`, `revenue_start_date`, `close_date`, `created_on`, `opportunity_id`, `delivery_territory_center`, etc.).
- Revenue for scoring uses `_get_revenue_series`: **`authoritative_revenue` first**, else **`total_estimated_revenue` with `opportunity_estimated_revenue_base_cad` fallback** (numeric coercion, missing → NaN then filled/clipped in each step). `service_solution_estimated_revenue` is never added to opportunity revenue.

## Pipeline order

`build_director_capacity_df(opportunity_df, current_date=None)` runs, in order:

1. `compute_sales_load` → per-row `sales_load` using `classify_opportunity_outcome`; only Open rows contribute.
2. `compute_delivery_load` → `delivery_load`, `delivery_active`; only Won rows inside the delivery window contribute.
3. `compute_current_load_by_owner` → one row per `opportunity_owner` with sums and dashboard drivers (`open_deal_count`, `late_stage_deal_count`, `weighted_pipeline_revenue`, `inferred_delivery_commitments`, `territory`, …).
4. `compute_historical_baseline` → active-quarter `historical_avg_load`, `quarters_of_data`, 4-tier `baseline_reliability`, etc., capped at the current/as-of quarter so open opportunities and long delivery windows do not project the dashboard into future years.
5. `compute_relative_load` → merge current + baseline on `opportunity_owner`.
6. `compute_capacity_score` → `capacity_score = max(0, 1 - min(relative_load, 1))` using capped `relative_load`.
7. `assign_capacity_label` → exactly **Available / At Capacity / Overextended**; NaN `capacity_score` → **At Capacity** (see `capacity_engine_scoring_notes.md`).

Final column order is fixed by `DIRECTOR_CAPACITY_DASHBOARD_COLUMNS`.

## Weighted pipeline revenue

Open-opportunity weighted pipeline uses `_rev * _prob_w` as two Series before `np.where`, so the assigned column is always a vector aligned to the frame index (avoids tuple / length mismatch on `groupby`).

## CLI / batch output (`if __name__ == "__main__"`)

- Reads: `data/processed/cleaned_opportunity_df.csv`.
- Writes: `data/processed/director_capacity_df.csv` (full table), `data/processed/director_capacity_df_example.csv` (first 12 rows for quick review).

## Downstream consumers

- Streamlit Director Capacity page should consume the **`build_director_capacity_df`** output shape (see dashboard contract: `opportunity_owner`, `territory`, `historical_avg_load`, `relative_load`, `current_load`, `capacity_score`, `capacity_label`, counts, weighted pipeline, inferred commitments, `quarters_of_data`, `baseline_reliability`).
- Workload trend rows should come from `compute_quarterly_workload_by_owner(..., as_of_date=...)`; the dashboard keeps the last eight quarters ending at the current/as-of quarter, not the maximum projected delivery date in the data.
- Scoring assumptions and label bands are documented separately in `docs/capacity_engine_scoring_notes.md`.

## Contract Guarantee

This module guarantees:

- Input: `cleaned_opportunity_df` (no preprocessing required outside this file)
- Output: exactly one row per `opportunity_owner`
- Output columns: strictly defined by `DIRECTOR_CAPACITY_DASHBOARD_COLUMNS`
- No side effects (no in-place mutation of input dataframe)
- Deterministic output given identical input

## Pytest Results
```bash
python -m pytest tests/test_capacity_engine.py
```
19/19 capacity-engine tests passed as part of the full suite.


## Handoff Notes

### 1. Owner-level aggregation is the final shape
The output of `build_director_capacity_df()` is strictly **one row per `opportunity_owner`**.

- No downstream groupby or re-aggregation should happen
- If duplicates appear, it indicates upstream data issues, not expected behavior

---

### 2. Relative load can be unstable by design
`relative_load = current_load / historical_avg_load`

- If historical baseline is missing or near zero, the metric becomes noisy or undefined
- This is expected for low-data or new owners, not a bug
- Missing or unusable baselines propagate NaN `capacity_score`
- NaN scores are intentionally labeled as `At Capacity` for dashboard stability
- Fine-grained overload severity should be interpreted using `relative_load` directly
---

### 3. Pipeline assumes missing data is already “neutralized”
All missing or incomplete fields are handled inside the scoring layer:

- missing dates → reduce or nullify delivery contribution
- missing revenue → fallback to safe numeric coercion
- missing probability/stage → treated as 0 contribution

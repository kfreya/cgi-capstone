# Capacity Dashboard Changelog

This note documents the relative-load, capacity-label, dashboard, filter, and documentation changes made on 2026-05-19. It is intended as a handoff/review artifact for the prototype.

## Summary

The dashboard now treats `relative_load` as the primary business metric instead of `capacity_score`. `relative_load` compares a director's current workload to that same director's historical norm:

``` text
relative_load = current_load / historical_avg_load
```

This better expresses overextension because `capacity_score` is capped at 0 once `relative_load >= 1`, which makes it unable to distinguish 1.1x from 5.0x historical norm.

## Workload Formula Changes

Current load is now documented and displayed as:

``` text
current_load = sales_load + delivery_load
```

Sales load uses open opportunities only:

``` text
sales_load =
    stage_weight
  * (probability / 100)
  * log1p(authoritative_revenue)
  * duration_weight

duration_weight = log1p(project_duration_number_of_months) / log1p(12)
```

Delivery load uses won active deliveries only:

``` text
monthly_revenue = authoritative_revenue / project_duration_number_of_months
delivery_load = delivery_active * log1p(monthly_revenue)
```

`delivery_active` now requires a won outcome and an active delivery window. Non-won records no longer contribute delivery load.

## Label Calibration

Capacity labels are now assigned from `relative_load`, not from `capacity_score`:

``` text
Available             : relative_load <= 0.85
Near Historical Norm  : 0.85 < relative_load < 1.25
High Load             : 1.25 <= relative_load < 2.00
Overextended          : relative_load >= 2.00
No baseline           : missing or zero historical baseline
```

This is a temporary project-side decision based on the observed director-level distribution and the business interpretation that carrying at least 2x historical workload should be called `Overextended`. CGI should review and adjust these thresholds before production use.

## Historical Baseline And Filters

The original denominator bug was that current load was effectively lifetime accumulated load while historical average was quarterly load. The implemented interpretation is:

``` text
relative_load = current active snapshot / historical quarterly norm
```

Dashboard filters now follow this rule:

``` text
territory + opportunity owner filters:
    define the selected director population for both current workload and baseline

row-level filters:
    status, sales stage, opportunity type, sales model, created date range
    narrow current workload and trend only
    do not recompute the historical baseline denominator
```

This keeps the baseline stable and makes filtered views answer: "How does this filtered current workload compare with the selected directors' normal workload?"

## Dashboard Changes

The dashboard now:

-   Uses real processed opportunity data when available.
-   Shows `Relative Load by Director` instead of capacity score by director.
-   Removes `capacity_score` from tooltips, the explainer, and the director summary table.
-   Shows `Label Mix` with visible category counts.
-   Uses the relative-load label color palette consistently across charts.
-   Uses log scale for `Current Load vs Historical Average` and `Workload Trend` to reduce outlier domination.
-   Removes relative-load threshold reference-line annotations from the main chart.
-   Keeps historical-average markers aligned with category bars.
-   Keeps x-axis labels flat after filtering when the director count is small.
-   Enables the dashboard filters that are currently supported by the real data.

## Documentation Updated

Updated documentation files:

-   `docs/architecture.md`
-   `docs/capacity_engine_integration.md`
-   `docs/capacity_scoring.md`
-   `docs/dashboard_requirements.md`
-   `docs/director_capacity_dashboard_column_dictionary.md`

The architecture document now reflects the implemented formulas, the relative-load-first metric decision, the temporary threshold calibration, the stable-baseline filter decision, and the current dashboard design.

## Code Updated

Updated implementation files:

-   `src/capacity_engine.py`
-   `app/app.py`
-   `app/mock_data.py`

Key implementation changes:

-   Capacity labels are assigned from `relative_load`.
-   `No baseline` is used when relative load cannot be computed.
-   Delivery load is gated to won active deliveries.
-   The app imports and uses the real processed opportunity dataframe.
-   Dashboard filters rebuild current workload from filtered rows while keeping baseline anchored to selected owner/territory history.

## Tests Updated

Updated test file:

-   `tests/test_capacity_engine.py`

Added or updated coverage for:

-   Sales-load log formula.
-   Delivery-load monthly revenue log formula.
-   Won-only delivery-active behavior.
-   Relative-load division.
-   Stable-baseline relative-load behavior under filtered current workload.
-   Relative-load label boundaries.
-   `No baseline` label behavior.

Latest verification:

``` bash
conda run -n cgi-capstone python -m pytest -q
# 72 passed

conda run -n cgi-capstone python -m py_compile app/app.py src/capacity_engine.py app/mock_data.py tests/test_capacity_engine.py

git diff --check
```

## Remaining Review Items

-   CGI should confirm whether the temporary label thresholds are appropriate for business language.
-   CGI should decide whether additional filters should also redefine the baseline population in future versions.
-   The dashboard still uses inferred workload, not measured hours or calendar commitments.
-   `capacity_score` remains in backend output for compatibility, but should not be treated as the main business metric.

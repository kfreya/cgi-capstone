# Director Capacity Dashboard Column Dictionary

`DIRECTOR_CAPACITY_DASHBOARD_COLUMNS` defines the **final contract schema**
produced by `build_director_capacity_df(opportunity_df)`.

This is the **owner-level aggregated output table** used directly by the
Director Capacity dashboard (Streamlit / downstream reporting layer).

The table contains exactly **one row per `opportunity_owner`**, and all
metrics are pre-aggregated. No further transformation or grouping is expected
downstream.

All fields are computed from cleaned opportunity-level data
(`cleaned_opportunity_df`) via the capacity engine pipeline:
sales load → delivery load → owner aggregation → baseline → relative load →
capacity score → labeling.

---

## Column schema

| Column name | Category | Description | Notes / downstream usage |
|---|---|---|---|
| `opportunity_owner` | identifier | Owner / director key used for aggregation. | Primary key of the output table. Exactly one row per owner. |
| `territory` | metadata | First observed `delivery_territory_center` per owner. | Informational grouping field. Not used in scoring logic. May be partially missing depending on upstream coverage. |
| `service_solution` | metadata | Semicolon-separated owner-level service-solution profile derived from opportunity-level `service_solution` values. | Used as a prototype service-fit signal by the RFP Assignment Tool. Values are based on won/open opportunities, sorted by frequency within each owner, and capped to the top observed services. Not used in numeric capacity scoring. |
| `current_load` | core metric | Sum of open sales load plus active won-delivery load per owner. | Primary workload signal used in relative load calculation. Lost, duplicate, cancelled, and inactive records do not contribute. |
| `relative_load` | derived metric | `current_load / historical_avg_load` (baseline-normalized load). | Key normalization signal. Can be unstable for low-history owners. |
| `historical_avg_load` | baseline metric | Mean quarterly load per owner across available history. | Derived from `compute_historical_baseline`. Used as normalization denominator. |
| `capacity_score` | derived metric | `max(0, 1 - min(relative_load, 1))` using capped `relative_load`. | Core capacity indicator used by dashboard visualization. Missing/invalid `relative_load` propagates NaN score. |
| `capacity_label` | classification | Discrete capacity state derived from temporary `relative_load` thresholds. | Values: `Available`, `Near Historical Norm`, `High Load`, `Overextended`, `No baseline`. The current thresholds are a project-side calibration based on observed distribution and business interpretation, subject to CGI review. |
| `open_deal_count` | pipeline metric | Count of opportunities classified as open by the canonical outcome taxonomy. | Simple pipeline activity indicator per owner. |
| `late_stage_deal_count` | pipeline metric | Count of open deals in late pipeline stages (Proposal → Signature). | Indicates near-term delivery risk / workload concentration. |
| `weighted_pipeline_revenue` | pipeline metric | Sum of `revenue × probability` for open opportunities. | Proxy for expected pipeline load; used in forecasting and prioritization. |
| `inferred_delivery_commitments` | delivery metric | Count of won opportunities currently in active delivery window. | Approximates active execution burden per owner. |
| `quarters_of_data` | baseline quality metric | Number of unique quarters contributing to baseline. | Used to assess reliability of historical average load. |
| `baseline_reliability` | baseline quality tier | Four-tier label derived from contributing quarters: `No baseline`, `Low`, `Medium`, or `High`. | Signals whether baseline is statistically stable or noisy. |

---

## Schema guarantees

- Exactly **1 row per `opportunity_owner`**
- No duplicate owners after aggregation
- No additional columns beyond this contract in production output
- All metrics are pre-computed (no downstream transformation required)

---

## Data coverage (from validation run)

- 24 owners processed
- No unexpected / extra columns detected
- High completeness across all core metrics:
  - load metrics: 100%
  - capacity metrics: ≥96%
  - baseline metrics: 100%
- `territory` is the only partially sparse field (~79% coverage)

---

## Design intent

This schema is designed as a **dashboard-ready contract layer**, meaning:

- It is not a raw feature table
- It is not a modeling dataset
- It is a pre-aggregated analytical output

All capacity logic is fully resolved upstream in the capacity engine.

Downstream systems should treat this as a **final reporting interface**, not a computation layer.

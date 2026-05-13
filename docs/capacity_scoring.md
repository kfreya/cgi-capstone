# Capacity Scoring

## Goal

The purpose of `capacity_engine.py` is to build the first prototype workflow for director-level capacity scoring.

The Week 1 version is intentionally lightweight and formula-based. The main goal is to define:

- module structure
- function interfaces
- dataframe input/output formats
- owner-level aggregation workflow

rather than final business-calibrated scoring.

---

## Implemented Functions

The Week 1 prototype implements the following functions:

- `compute_sales_load`
- `compute_delivery_load`
- `compute_current_load_by_owner`
- `compute_historical_baseline`
- `compute_relative_load`
- `assign_capacity_label`
- `compute_capacity_score`

These functions operate on `opportunity_df` and return dashboard-friendly
owner/director-level outputs.

---

## Current Workflow

The current pipeline follows this sequence:

opportunity_df  
→ sales_load_i  
→ delivery_load_i  
→ current_load_owner  
→ historical baseline  
→ relative_load_owner  
→ capacity_score_owner  
→ capacity_label

The output is a director-level dataframe (`director_df`) that can later feed into the dashboard and RFP assignment workflow.

---

## Current Feature Definitions

### Sales Load

The current prototype uses:

sales_load_i =  
stage_weight × probability × log1p(revenue) × duration_weight

This approximates pre-sales workload intensity.

Current assumptions:
- later sales stages imply higher effort
- larger opportunities imply higher coordination effort
- longer projects imply more planning complexity
- higher probability implies higher commitment

Won opportunities are excluded from sales load because they are assumed to have moved into delivery.

---

### Delivery Load

The delivery component currently uses Won opportunities as a proxy for active delivery responsibility.

Delivery load is based on:
- estimated monthly revenue
- inferred active delivery window
- revenue start date / close date
- project duration

Current implementation is intentionally simple and will likely evolve after validation feedback.

---

### Current Load

Director-level workload is currently defined as:

current_load = sales_load + delivery_load

aggregated by `opportunity_owner`.

Additional owner-level prototype fields currently include:
- territory
- late_stage_deal_count
- weighted_pipeline_revenue
- inferred_delivery_commitments

These were added mainly to support downstream dashboard views.

---

### Historical Baseline

Historical baseline is computed from quarterly aggregated load.

Current outputs:
- historical_avg_load
- historical_std_load
- historical_max_load
- quarters_of_data
- baseline_reliability

A reliability flag is also included for owners with limited historical coverage.

---

### Relative Load

Current implementation:

relative_load =  
current_load / historical_avg_load

This keeps workload relative to each director’s own historical pattern rather than comparing all directors globally.

---

### Capacity Score

Current implementation:

capacity_score = 1 - min(relative_load, 1)

The current version intentionally compresses overloaded cases toward zero.

Interpretation:
- closer to 1 → more available capacity
- closer to 0 → heavily loaded

This is still prototype logic and not business validated.

---

### Capacity Labels

Label bands are applied to **`capacity_score`**, not raw `relative_load`, per `docs/architecture.md`:

- **Available**: `capacity_score >= 0.35`
- **At Capacity**: `0.15 <= capacity_score < 0.35`
- **Overextended**: `capacity_score < 0.15`

Earlier drafts used `relative_load` placeholder cutoffs; those are superseded by the architecture contract. Thresholds remain configurable in code.

---

## Known Issues / Open Questions

### 1. Large Number of "Overextended" Labels

The current prototype still produces many directors labeled as "Overextended".

Possible reasons:
- historical baseline window may be too small
- current CRM snapshot may be unusually dense
- delivery assumptions may be overestimating active commitments
- sales and delivery effort may partially overlap
- workload formulas are not yet calibrated

At this stage this is expected and does not necessarily indicate a bug.

---

### 2. Missing and Zero Values

Some directors currently have:
- missing historical baselines
- zero delivery load
- zero or near-zero capacity scores

This appears to be mostly driven by CRM data sparsity rather than code failures.

Week 2 validation work should clarify:
- whether fallback assumptions are needed
- which revenue/date fields are reliable
- whether some owners should be excluded from scoring

---

### 3. Sales vs Delivery Capacity

The current model combines:

capacity = sales_load + delivery_load

However, these likely represent different operational constraints:
- sales bandwidth
- delivery execution responsibility

This distinction may become important later for RFP assignment recommendations.

---

### 4. Structured Experience Signals

The current architecture relies heavily on text similarity for RFP assignment
fit. A future refinement should combine semantic similarity with structured
experience signals such as:

- win rate
- successful similar deals
- average deal size
- client tier
- stage progression behavior

This may improve recommendation quality and reduce bias toward directors with
high volume but low success.

---

### 5. CRM Limitations

The CRM extracts do not contain:
- staffing allocation
- actual utilization
- time tracking
- historical stage transitions
- resource assignments

Therefore, current scores should be interpreted as:
"CRM-derived workload proxies"

rather than true operational utilization metrics.

---

## Tests

`tests/test_capacity_engine.py` covers:

- sales load calculation
- delivery load calculation
- owner-level aggregation
- historical baseline generation
- relative load calculation
- capacity label assignment

The initial Week 1 test suite included 11 capacity-engine tests.

---

## Week 1 Scope Boundary

Week 1 intentionally prioritizes:
- reproducible workflow
- modular functions
- clean dataframe outputs
- dashboard-ready interfaces

over:
- finalized formulas
- calibrated thresholds
- business-approved scoring logic
- production recommendation quality

Formula refinement and validation are expected in Week 2+.

---

## Next Steps

- Connect the scoring workflow to the cleaned `opportunity_df`.
- Refine delivery logic after validation and stakeholder review.
- Improve historical baseline logic.
- Review threshold behavior.
- Integrate capacity outputs into the dashboard.
- Explore structured experience features for RFP assignment.

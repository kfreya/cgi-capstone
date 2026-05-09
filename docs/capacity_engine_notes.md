# Week 1 `capacity_engine.py` Notes

## Goal

The purpose of `capacity_engine.py` is to build the first **prototype** workflow for director-level capacity scoring.  

The Week 1 version is intentionally lightweight and formula-based. The focus is on defining:

- module structure
- function interfaces
- dataframe input/output formats
- owner-level aggregation workflow

rather than final business-calibrated scoring.

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

The output is a director-level dataframe (`director_df`) used later by the dashboard and RFP assignment tool.

---

## Current Feature Definitions

### Sales Load

The current prototype uses:

sales_load_i =
stage_weight
× probability
× log1p(revenue)

This approximates pre-sales effort.

Current assumptions:
- later stages imply higher effort
- larger deals imply higher effort
- higher probability implies more commitment

---

### Delivery Load

The current prototype delivery component uses Won opportunities as a proxy for ongoing delivery responsibility.

The current implementation is intentionally simple and will likely change after CGI validation.

---

### Current Load

Director-level load is currently:

current_load_owner =
sum(sales_load_i + delivery_load_i)

grouped by `opportunity_owner`.

---

### Historical Baseline

Historical baseline is computed from quarterly aggregated load.

Current outputs:
- historical_mean_load
- historical_std_load
- historical_max_load
- quarters_seen

A reliability flag is added for owners with limited historical coverage.

---

### Relative Load

Current implementation:

relative_load_owner =
current_load_owner / historical_mean_load

This keeps director workload relative to their own historical pattern.

---

### Capacity Score

Current implementation:

capacity_score_owner =
min(1 / relative_load_owner, 1)

This intentionally compresses values once directors exceed baseline.

---

### Capacity Labels

Current thresholds:

- Available:
  capacity_score ≥ 0.65

- At Capacity:
  0.35 ≤ capacity_score < 0.65

- Overextended:
  capacity_score < 0.35

These thresholds are placeholders and expected to change after stakeholder review.

---

## Known Issues / Open Questions

### 1. Most directors are currently labeled "Overextended"

The current prototype produces many relative_load values around 5–8x baseline.

Possible reasons:
- historical baseline window is too small
- current pipeline snapshot is unusually dense
- Won deals may still be contributing to sales load
- sales and delivery load may be double-counting effort
- baseline logic may not reflect real operational workload

This is expected at the prototype stage and will be revisited in Week 2.

---

### 2. Sales vs Delivery Capacity

The current model combines:

capacity = sales_load + delivery_load

However, these likely represent different business constraints:
- sales capacity → pre-sales / proposal bandwidth
- delivery capacity → post-sale execution responsibility

This distinction may become important for the RFP recommendation system.

---

### 3. Historical CRM Limitations

The CRM extracts do not contain:
- historical stage transitions
- true utilization
- staffing allocations
- actual hours worked

Therefore, current capacity scores should be interpreted as:
"CRM-derived workload proxies"
rather than true operational utilization.

---

## Week 1 Scope Boundary

Week 1 intentionally prioritizes:
- reproducible workflow
- modular functions
- clean dataframe outputs
- dashboard-ready interfaces

over:
- final calibrated formulas
- business-validated thresholds
- optimized recommendation logic

Formula refinement and stakeholder validation are planned for Week 2+.
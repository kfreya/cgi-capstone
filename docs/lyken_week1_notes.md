# Week 1 Lyken Merge Notes

## Main Work Completed

### 1. Built `capacity_engine.py` skeleton

Implemented the first (prototype) version of the following functions:

- `compute_sales_load`
- `compute_delivery_load`
- `compute_current_load_by_owner`
- `compute_historical_baseline`
- `compute_relative_load`
- `assign_capacity_label`

The functions were designed to operate directly on `opportunity_df` and return dashboard-friendly outputs.

---

### 2. Built owner-level aggregation workflow

The pipeline currently supports:

opportunity-level scoring  
→ owner-level aggregation  
→ historical baseline comparison  
→ final director-level scoring table

Current output columns include:
- current_load
- sales_load
- delivery_load
- historical_mean_load
- historical_std_load
- relative_load
- capacity_score
- capacity_label

This structure is intended to become the base input for the Streamlit dashboard.

---

### 3. Added historical baseline prototype

Implemented a first-pass quarterly historical baseline calculation.

Current outputs:
- historical_mean_load
- historical_std_load
- historical_max_load
- quarters_seen
- baseline_reliability_flag

The purpose is to compare directors against their own historical workload patterns instead of against global averages.

---

### 4. Added unit tests

Created:
- `tests/test_capacity_engine.py`

The tests currently cover:
- sales load calculation
- delivery load calculation
- owner-level aggregation
- historical baseline generation
- relative load calculation
- label assignment

Current pytest status:
- 11 tests passed

---

## Early Findings

### 1. Many directors are currently labeled "Overextended"

This appears to be caused by:
- very small historical baselines for some owners
- large numbers of Won opportunities
- possible overlap between sales and delivery contributions
- historical CRM limitations

This is expected at the prototype stage and does not necessarily indicate a bug in the pipeline structure itself.

---

### 2. Sales load and delivery load tend to represent different types of capacity

Current implementation combines:

$$capacity = sales load + delivery load$$

However:
- sales load reflects pre-sales / proposal effort
- delivery load reflects post-sale operational responsibility

This may become important later for:
- RFP assignment
- recommendation explainability
- director specialization

Possible future direction:
keep separate capacity dimensions instead of forcing a single combined score.

---

### 3. Experience should include structured signals

Current architecture relies heavily on text similarity.

A possible improvement discussed this week:
combine semantic similarity with structured experience signals such as:
- win rate
- successful similar deals
- average deal size
- client tier
- stage progression behavior

This may improve recommendation quality and reduce bias toward directors with only high volume but low success.

---

## Dependencies / Assumptions

The current prototype assumes:
- `opportunity_owner` is the director-level entity
- `opportunity_df` is already deduplicated at opportunity level
- revenue fields are reasonably usable
- Won opportunities can be used as delivery proxies

Further validation from Role 2 and CGI feedback is still needed.

---


## Next Week

Planned Week 2 work:
- connect cleaned `opportunity_df`
- refine delivery logic
- improve historical baseline logic
- review threshold behavior
- integrate outputs into dashboard
- begin structured experience feature design for RFP assignment
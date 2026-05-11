# Data Validation

**Author:** Kian (Data Validation Owner)
**Issue:** [#6 Sprint 1: Validate scoring and owner-level fields](../../issues/6)
**Source data:** Merged `opportunity_df` from `src.opportunity_cleaner.build_opportunity_df()` — 8,746 unique opportunities as of 2026-05-08.
**Companion files:**
- `src/data_validator.py` — reusable validation + owner-aggregate functions
- `tests/test_data_validator.py` — contract tests
- `notebooks/role2_validation.ipynb` — full re-runnable analysis
- `config/fallback_assumptions.yaml` — machine-readable fallback rules for validation/scoring

This document covers the six issue-#6 deliverables in order: missingness, revenue
hierarchy, date/duration validation, fallback assumptions, owner-level summary,
and the reliable-vs-risky list. A short list of open questions for Lyken and CGI
sits at the end.

The machine-readable fallback rules now live in
[`config/fallback_assumptions.yaml`](../config/fallback_assumptions.yaml). Longer
interpretation and review notes remain in this document. Generative AI drafting
assistance was used for the original fallback-rules note; rule definitions,
evidence values, and risk assignments were reviewed by the validation owner.

---

## 1. Missingness summary

Field-by-field null and zero counts on the 13 fields capacity scoring depends
on. Run `summarize_missingness(opportunity_df)` to regenerate.

| field | family | n_null | pct_null | n_zero | n_negative | dtype |
|---|---|---:|---:|---:|---:|---|
| total_estimated_revenue | revenue | 51 | 0.58% | 291 | 0 | float64 |
| opportunity_estimated_revenue_base_cad | revenue | 8,695 | 99.42% | 4 | 0 | float64 |
| service_solution_estimated_revenue | revenue | 3,833 | 43.83% | 148 | 0 | object |
| created_on | date | 51 | 0.58% | — | — | datetime64 |
| close_date | date | 365 | 4.17% | — | — | object |
| revenue_start_date | date | 1,092 | 12.49% | — | — | datetime64 |
| project_duration_number_of_months | duration | 852 | 9.74% | 43 | 0 | float64 |
| status | categorical | 0 | 0.00% | — | — | object |
| status_reason | categorical | 51 | 0.58% | — | — | object |
| sales_stage | categorical | 0 | 0.00% | — | — | object |
| probability | categorical | 77 | 0.88% | 139 | 0 | object |
| opportunity_owner | owner | 0 | 0.00% | — | — | object |
| opportunity_manager | owner | 0 | 0.00% | — | — | object |

**Takeaway.** The columns most central to scoring (`status`, `sales_stage`,
`opportunity_owner`, `opportunity_manager`) are 100% populated. Revenue
fallback resolves the 51-row primary gap. The two real concerns are
`revenue_start_date` (12% null — affects delivery-window calculation) and
`project_duration_number_of_months` (10% null + 152 outliers > 60 months).

The 99.42% null on `opportunity_estimated_revenue_base_cad` is **expected**
and not a problem — see §2.

---

## 2. Revenue field hierarchy

| field | what it is | how to use |
|---|---|---|
| `total_estimated_revenue` | Authoritative CAD revenue from opps2. | **Primary.** Use as the canonical revenue for every load calculation. |
| `opportunity_estimated_revenue_base_cad` | Same metric from the opps1 schema. | **Fallback.** Use only when the primary is null. |
| `service_solution_estimated_revenue` | Per-service-line breakdown collapsed in `opportunity_cleaner`. | **Do not sum onto either of the above.** It is a within-opportunity decomposition, not an additive component. |

**Resolution rule (implemented in `apply_revenue_hierarchy`):**

```text
authoritative_revenue =
    total_estimated_revenue                if not null
    else opportunity_estimated_revenue_base_cad   if not null
    else MISSING (row excluded from load calculation)
```

**Why the two fields look mutually exclusive in the merged data.** EDA earlier
reported 98.7% agreement between the two on overlapping rows. That overlap was
measured *before* `opportunity_cleaner` collapsed and merged the tables. In the
final `opportunity_df`, opps2-sourced rows carry `total_estimated_revenue` and
opps1-exclusive rows carry `opportunity_estimated_revenue_base_cad` — so the
two fields are mutually exclusive, not redundant. There are zero rows where
both are populated and zero rows where both are null. The fallback is
**essential**, not cosmetic — without it the 51 opps1-exclusive opportunities
have no revenue input.

**Outlier flags (advisory, not exclusion):**
- 3 rows with `total_estimated_revenue > $100M` — confirm with CGI whether these
  are real megadeals or unit-scale errors.
- 488 rows with `total_estimated_revenue` between $0 and $100 — possibly
  placeholder / test entries.

---

## 3. Date and duration validation

**Resolved as of:** 2026-05-08.

| metric | value |
|---|---:|
| n_total | 8,746 |
| n_created_on_null | 51 |
| n_close_date_null | 365 |
| n_revenue_start_date_null | 1,092 |
| n_duration_null | 852 |
| n_duration_zero | 43 |
| n_duration_over_60_months | 152 |
| **n_close_before_created** | **3,049** |
| n_won_total | 5,275 |
| n_won_window_resolvable_via_revenue_start_date | 5,275 |
| n_won_window_resolvable_via_close_date_fallback | 0 |
| n_won_window_unresolvable | 0 |

### Three findings

**a. Delivery window is 100% resolvable on Won deals via `revenue_start_date`.**
All 5,275 Won opportunities have a populated `revenue_start_date`. Lyken's
`compute_delivery_load` falls back to `close_date` when `revenue_start_date`
is null, but in the current data the fallback path is never taken. We should
keep it defined — future CRM rows may not be as clean.

**b. `close_date < created_on` on 3,049 rows (~35%).** This is a large
ordering anomaly that needs investigation before any time-series analysis is
trusted. Hypotheses:
1. CRM backdating — opportunities registered after the close was already
   recorded for retrospective tracking.
2. The `close_date` in CRM is the *projected* close date for in-progress
   deals, which can drift earlier than `created_on` for very early-stage
   opportunities.
3. Data entry / migration artefact.

**Action:** raise with CGI in next sync. Until clarified, do **not** use
`close_date - created_on` as a "time to close" metric.

**c. Duration outliers.** 152 opportunities show `project_duration_number_of_months > 60`
(over 5 years). Some of these may be multi-year framework agreements; others
are likely typos. The `clip(lower=1)` in `capacity_engine.py` does not address
these — they currently inflate `duration_weight` substantially.

---

## 4. Fallback assumptions

Full machine-readable rules are in
[`config/fallback_assumptions.yaml`](../config/fallback_assumptions.yaml).
Summary:

| rule_id | primary | fallback | when fallback applies | risk |
|---|---|---|---|---|
| `revenue_hierarchy` | `total_estimated_revenue` | `opportunity_estimated_revenue_base_cad` | primary is null | low |
| `delivery_window` | `revenue_start_date` | `close_date` | primary is null | low |
| `missing_duration` | actual value | 12 months | null or ≤ 0 | medium |
| `missing_probability` | actual value | 0 | null | medium |
| `won_detection` | `status_reason == 'Won'` | (none) | never | low |
| `do_not_sum_service_solution_revenue` | n/a | n/a | always — never sum | low |

The two **medium-risk** rules (`missing_duration`, `missing_probability`) are
the ones whose silent application can mask real data issues. Recommend Lyken
add a counter to `compute_sales_load` and `compute_delivery_load` that exposes
the number of rows on which a default was substituted, so dashboard users can
distinguish "zero sales effort" from "missing data".

---

## 5. Owner-level validation summary

24 distinct opportunity owners — slightly higher than the EDA's earlier
~22 estimate. Zero casing or whitespace variants once normalized; zero
rows where `opportunity_owner == opportunity_manager`.

**Baseline reliability distribution (`quarters_of_data` from `created_on`):**

| reliability | quarters_of_data | n_owners |
|---|---|---:|
| High | ≥ 8 | varies — see notebook |
| Medium | 4–7 | varies — see notebook |
| Low | < 4 | 0 (none observed) |

**Owners with < 10 lifetime opportunities: 7.** These owners have a thin
historical record; their capacity scores should carry a "Low" reliability tag
in the dashboard regardless of `quarters_of_data`. Names are in the notebook
output and should be reviewed with CGI before being shown in the UI.

**`build_owner_aggregates(opportunity_df)` produces** the 7 columns Freya's
dashboard mock expects but Lyken's `director_df` does not (yet) emit:
`opportunity_owner`, `territory`, `late_stage_deal_count`,
`weighted_pipeline_revenue`, `inferred_delivery_commitments`,
`quarters_of_data`, `baseline_reliability`. Lyken can join this onto his
`director_df` on `opportunity_owner` to satisfy the dashboard contract.

The full owner-level table (24 rows) is in the notebook and a CSV copy
under `data/processed/` (gitignored — regenerate locally).

---

## 6. Reliable vs risky fields

| field | rating | notes |
|---|---|---|
| `opportunity_owner` | reliable | 0 nulls, 0 case variants |
| `opportunity_manager` | reliable | 0 nulls; 0 owner-equals-manager rows confirms architecture's assumption |
| `status` | reliable | 0 nulls, 3 distinct values |
| `sales_stage` | reliable | 0 nulls, all 7 values mapped to architecture's stage_weight table |
| `total_estimated_revenue` | reliable (with fallback) | 0.58% null; covered by the revenue hierarchy |
| `created_on` | reliable | 0.58% null |
| `status_reason` | use with care | 0.58% null but disagrees with `status` on 15 rows for Won detection — minor but worth reconciling |
| `probability` | use with care | 0.88% null + 139 explicit zeros; default-fill to 0 is documented but should be counted |
| `project_duration_number_of_months` | use with care | 9.74% null + 43 zeros + 152 over 60mo; default-fill to 12 should be counted |
| `revenue_start_date` | use with care | 12.49% null overall, but 100% present on Won deals |
| `service_solution_estimated_revenue` | use with care | 43.83% null; do **not** add to opportunity-level revenue |
| `close_date` | needs CGI clarification | 4.17% null AND 35% of populated rows pre-date `created_on` |
| `opportunity_estimated_revenue_base_cad` | reliable as fallback only | 99.42% null overall, but exactly the rows where primary is null |

---

## Open questions

**For Lyken (capacity_engine):**
1. Want me to swap `apply_revenue_hierarchy` into `compute_delivery_load` and
   `compute_sales_load`, or you take that on a separate PR?
2. Add row-counter outputs for `probability=0` and `duration=12` default-fills
   so we can tell missing-data rows from real-zero rows?
3. Reconcile `status == "won"` vs `status_reason == "Won"` for Won detection
   (15-row disagreement)? Architecture spec'd `status_reason`.
4. Three column renames + four added aggregate columns to align `director_df`
   with `app/mock_data.py`: I produce the four; you handle the renames?

**For Yixiao (opportunity_cleaner):**
1. The 1,067 opps2-only IDs (~12%) flagged in your merge notes — is that
   expected (CGI staged-loading) or a coverage gap to escalate?
2. Should `opportunity_estimated_revenue_base_cad` be added to
   `SUPPLEMENTAL_FIELDS` so opps2 rows can carry both fields and we have
   real cross-field validation overlap?

**For CGI (Monday sync):**
1. **3,049 rows where `close_date < created_on`** — what's the CRM convention
   driving this? Backdating, projected close date semantics, or a migration
   artefact?
2. 152 rows with `project_duration > 60 months` — are these legitimate
   long-term framework agreements or data entry errors?
3. 3 rows with `total_estimated_revenue > $100M` — confirmable as real?

---

## Use of Generative AI

Anthropic Claude (Opus 4.7) was used for drafting and editing assistance on
this document. All validation logic, computed metrics, and conclusions are
my own — derived from running the validator functions in
`src/data_validator.py` against the team's merged `opportunity_df`, and
verified against the underlying data. No CGI data (opportunity rows, owner
names, revenue figures, proposal text) was sent to the tool.

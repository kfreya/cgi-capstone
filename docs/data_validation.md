# Data Validation

**Author:** Kian (Data Validation Owner)
**Issue:** [#21 Sprint 2: Validate scoring and dashboard input fields](../../issues/21)
**Source data:** `cleaned_opportunity_df` from
`src.opportunity_cleaner.clean_opportunity_df(build_opportunity_df()[0])` —
8,746 opportunity-level rows as of 2026-05-14. This is the Sprint 2 input:
the Week 1 merged `opportunity_df` plus Yixiao's additive cleaning pass
(merge-provenance flags, eight data-quality flags, a precomputed
`authoritative_revenue`).
**Companion files:**
- `src/data_validator.py` — reusable validation, taxonomy, and handoff functions
- `tests/test_data_validator.py` — contract tests
- `notebooks/role2_validation.ipynb` — full re-runnable analysis
- `config/fallback_assumptions.yaml` — machine-readable fallback rules for validation/scoring
- `docs/scoring_input_reliability_handoff.md` — the targeted Kian to Lyken scoring-input contract

This document covers the issue-#21 deliverables: missingness, revenue
hierarchy, date/duration validation, the new data-quality flag summary, the
`status_reason` outcome taxonomy, fallback assumptions, the owner-level
summary, and field reliability for scoring. A list of open questions for
Lyken, Yixiao, and CGI sits at the end.

The machine-readable fallback rules live in
[`config/fallback_assumptions.yaml`](../config/fallback_assumptions.yaml).
Longer interpretation and review notes remain in this document.

---

## 1. Missingness summary

Field-by-field null and zero counts on the 13 business fields capacity
scoring depends on. Run `summarize_missingness(cleaned_opportunity_df)` to
regenerate.

| field | family | n_null | pct_null | n_zero | n_negative | dtype |
|---|---|---:|---:|---:|---:|---|
| total_estimated_revenue | revenue | 51 | 0.58% | 291 | 0 | float64 |
| opportunity_estimated_revenue_base_cad | revenue | 1,067 | 12.20% | 82 | 0 | float64 |
| service_solution_estimated_revenue | revenue | 3,833 | 43.83% | 148 | 0 | float64 |
| created_on | date | 51 | 0.58% | — | — | datetime64 |
| close_date | date | 365 | 4.17% | — | — | datetime64 |
| revenue_start_date | date | 1,092 | 12.49% | — | — | datetime64 |
| project_duration_number_of_months | duration | 852 | 9.74% | 43 | 0 | float64 |
| status | categorical | 0 | 0.00% | — | — | object |
| status_reason | categorical | 51 | 0.58% | — | — | object |
| sales_stage | categorical | 0 | 0.00% | — | — | object |
| probability | categorical | 77 | 0.88% | 139 | 0 | float64 |
| opportunity_owner | owner | 0 | 0.00% | — | — | object |
| opportunity_manager | owner | 0 | 0.00% | — | — | object |

(`n_zero` / `n_negative` are left blank for date and pure-categorical fields
where they are not meaningful.)

**Takeaway.** The columns most central to scoring (`status`, `sales_stage`,
`opportunity_owner`, `opportunity_manager`) are 100% populated. The revenue
hierarchy resolves the 51-row primary gap (see §2). The fields that need
fallback handling are `revenue_start_date` (12.49% null — affects the
delivery-window calculation) and `project_duration_number_of_months` (9.74%
null plus 43 non-positive values and 152 outliers over 60 months).

The 12.20% null on `opportunity_estimated_revenue_base_cad` is **not** a
defect — it is exactly the unmatched opps2 rows (see §2). This is a change
from Sprint 1, where the same field was ~99% null.

---

## 2. Revenue field hierarchy

| field | what it is | how to use |
|---|---|---|
| `total_estimated_revenue` | Authoritative CAD revenue from the opps2 schema. | **Primary.** Use as the canonical revenue for every load calculation. |
| `opportunity_estimated_revenue_base_cad` | The same metric from the opps1 schema. | **Fallback.** Use only when the primary is null. |
| `service_solution_estimated_revenue` | Per-service-line breakdown collapsed in `opportunity_cleaner`. | **Do not sum onto either of the above.** It is a within-opportunity decomposition, not an additive component. |

**Resolution rule (implemented in `apply_revenue_hierarchy`, and precomputed
by the cleaner as `authoritative_revenue`):**

```text
authoritative_revenue =
    total_estimated_revenue                       if not null
    else opportunity_estimated_revenue_base_cad    if not null
    else MISSING (row excluded from load calculation)
```

**The two revenue fields now overlap and cross-validate.** In Sprint 1 the
fields were mutually exclusive in the merged data, so no cross-field check was
possible. Yixiao's Sprint 2 merge adds `opportunity_estimated_revenue_base_cad`
to the supplemental fields carried onto matched rows, so the picture is now:

| row group | count | primary | fallback |
|---|---:|---|---|
| matched opps1 + opps2 | 7,628 | present | present |
| unmatched opps2 (no opps1 match) | 1,067 | present | null |
| opps1-exclusive | 51 | null | present |

On the 7,628 rows where both are populated, they agree within 5% on **99.5%**
of rows (7,590 of 7,628) and match exactly on 7,522. This **validates** the
fallback: the two fields are the same metric measured on different schemas,
not two different numbers. There are **zero** rows where both are null, so
`authoritative_revenue` resolves for every opportunity.

**Outlier flags (advisory, not exclusion):**
- 3 rows with `total_estimated_revenue > $100M` — confirm with CGI whether
  these are real megadeals or unit-scale errors.
- 488 rows with `total_estimated_revenue` between $0 and $100, plus 291 rows
  at exactly $0 — possibly placeholder or test entries. A $0 revenue row
  contributes zero weighted revenue to scoring; that may or may not be the
  intent, so `total_estimated_revenue` is rated *use with care* in §8.

---

## 3. Date and duration validation

**Resolved as of:** 2026-05-14.

| metric | value |
|---|---:|
| n_total | 8,746 |
| n_created_on_null | 51 |
| n_close_date_null | 365 |
| n_revenue_start_date_null | 1,092 |
| n_duration_null | 852 |
| n_duration_zero | 43 |
| n_duration_over_60_months | 152 |
| **n_close_before_created** | **379** |
| n_created_after_today | 0 |
| n_won_total | 5,290 |
| n_won_window_resolvable_primary | 5,275 |
| n_won_window_resolvable_fallback | 15 |
| n_won_window_unresolvable | 0 |

### Three findings

**a. Delivery window is 100% resolvable on Won deals.** All 5,290 Won
opportunities resolve a delivery-window start: 5,275 via `revenue_start_date`
and 15 via the `close_date` fallback. The 15 fallback rows are the
`status == "Won"` opportunities with a null `status_reason` that the Sprint 2
outcome taxonomy now classifies as Won (see §5) — in Sprint 1 they were not
counted as Won at all. Zero Won rows are unresolvable.

**b. `close_date < created_on` is 379 rows (~4%), not 3,049.** The Sprint 1
figure of 3,049 (~35%) was a measurement artefact. `created_on` carries a
full timestamp while `close_date` is recorded at midnight, so comparing the
raw timestamps counted every deal created and closed on the same calendar day
as an ordering violation. `validate_date_duration_fields` now normalizes both
series to calendar date before comparing; the corrected count is **379**
(~4% of all rows, ~4.5% of populated `close_date` rows). This is still a real
anomaly worth a CGI question, but it is an order of magnitude smaller than the
Sprint 1 alarm and no longer blocks time-based analysis wholesale.

Note: Yixiao's `close_before_created_flag` in `opportunity_cleaner.py` still
uses the un-normalized comparison and reports 3,049. The gap (2,670) is
surfaced by `validate_quality_flags` as `flag_discrepancy_close_before_created`
— see §4. This is a finding for Yixiao to fold into `opportunity_cleaner.py`,
not something Role 2 edits in another owner's module.

**c. Duration outliers.** 152 opportunities show
`project_duration_number_of_months > 60` (over 5 years), plus 43 at zero or
below. Some long values may be multi-year framework agreements; others are
likely typos. The `missing_duration` fallback (12 months) covers nulls and
non-positive values; the >60-month rows pass through and currently inflate any
duration-weighted term. Subsets for both anomalies have been exported for the
CGI sync (gitignored under `data/processed/`).

---

## 4. Data-quality and merge flags

`cleaned_opportunity_df` carries four merge-provenance flags and eight
data-quality flags. Run `validate_quality_flags(cleaned_opportunity_df)` to
regenerate.

| flag | count | reading |
|---|---:|---|
| source_file_flag = opps2_base | 8,695 | rows sourced from the opps2 base table |
| source_file_flag = opps1_exclusive | 51 | opportunities found only in opps1 |
| duplicate_flag | 0 | **no duplicate join keys** — the merge is clean on `opportunity_id` |
| unmatched_flag | 1,067 | opps2 rows with no opps1 match — legitimate opportunities, kept |
| opps1_exclusive_flag | 51 | same 51 opps1-exclusive rows as above |
| missing_owner_flag | 0 | every row has an owner |
| missing_probability_flag | 77 | matches `n_probability_null` |
| invalid_probability_flag | 0 | no probability outside [0, 100] |
| missing_revenue_flag | 0 | every row has at least one revenue candidate |
| missing_duration_flag | 852 | matches `n_duration_null` |
| invalid_duration_flag | 43 | duration <= 0 |
| missing_revenue_start_date_flag | 1,092 | matches `n_revenue_start_date_null` |
| close_before_created_flag | 3,049 | the cleaner's un-normalized count (see below) |

**Two cross-checks** confirm the flags reconcile with the field validators:

- `flag_discrepancy_missing_revenue = 0` — `missing_revenue_flag` agrees
  exactly with `validate_revenue_fields`' `n_unscoreable_both_null`.
- `flag_discrepancy_close_before_created = 2,670` — `close_before_created_flag`
  (3,049) minus the corrected calendar-date count (379). The cleaner's flag
  uses the same un-normalized timestamp comparison that was fixed in
  `validate_date_duration_fields` this sprint. **Recommendation for Yixiao:**
  normalize both dates in `opportunity_cleaner.py` so the flag matches the
  corrected count.

`duplicate_flag = 0` is worth calling out: the Sprint 1 worry about duplicate
join keys does not materialise in the merged data, so the duplicate-row
exclusion in `build_owner_aggregates` is a no-op safeguard on the current
data, not an active correction.

---

## 5. status_reason outcome taxonomy

`status_reason` is the architecture-canonical outcome field. Beyond Won / Open
/ Lost it carries `Cancelled ...` and `Duplicated` values, and Sprint 2 had to
decide how those map into outcome buckets. Yixiao's `build_owner_base_summary`
currently folds Cancelled and Duplicated into `lost_opportunity_count` with a
first-pass regex and explicitly deferred the real taxonomy to Role 2.

**The three options considered:**

- **Option A** — Cancelled and Duplicated are both lost-like; anything that is
  not Won or Open is a pipeline exit.
- **Option B** — Cancelled is lost-like; Duplicated is excluded from outcome
  counts as a data-quality marker.
- **Option C** — Lost, Cancelled, and Duplicated become three separate outcome
  columns.

**Evidence (profiled on `cleaned_opportunity_df`):**

- `status` has 3 values: Won (5,290), Closed (3,091), Open (365).
- `status_reason` has 17 non-null values plus 51 nulls. The Cancelled family
  totals 1,925 rows across five labels; the LOST-* family totals 691 rows
  across nine labels; `Duplicated` is 461 rows; `Won` 5,275; `Open` 343.
- **`status_reason == "Duplicated"` has zero overlap with the merge-level
  `duplicate_flag`** (which is 0 for the whole dataset). The 461 Duplicated
  rows are all `status == "Closed"` and are concentrated in just **3 owners**.

**Decision — Option B.** The evidence shows `Duplicated` is a CRM
data-hygiene label (the CRM team marking a record as a duplicate of another
opportunity), not a merge artefact and not a sales win/loss outcome. Folding
461 such records into `lost_opportunity_count` would inflate three owners'
loss counts and distort their win rates with records that never represented a
real pursuit. Cancelled, by contrast, is a genuine pipeline exit — a pursuit
that ended unwon — so it is lost-like. Option C was rejected as a premature
schema cost on Yixiao's `owner_base_summary` and Lyken's scoring before CGI
has even confirmed the semantics.

**Implementation.** `classify_opportunity_outcome(df)` in `src/data_validator.py`
is the shared helper; Yixiao and Lyken should import it rather than re-deriving
buckets. It returns one of `won | lost | open | duplicate | unknown`:

- `status_reason` is read first (canonical); `status` is the fallback for the
  51 null-reason rows.
- CRM `status_reason` values are free text, so the Lost and Cancelled families
  are matched by **prefix** (`lost`, `cancelled`, `canceled`); Won / Open /
  Duplicated are exact.
- Null `status_reason` falls back to `status`: Won → won, Open → open,
  Closed → lost (the opportunity ended unwon; the reason is simply unrecorded).
- This subsumes the Sprint 1 `won_detection` rule — the 15 `status == "Won"`
  rows with a null `status_reason` now resolve to Won.

On the current data the helper yields **won 5,290 / lost 2,630 / duplicate 461
/ open 365 / unknown 0**. `build_owner_aggregates` surfaces
`duplicate_opportunity_count` so the Option B carve-out is auditable per owner.

**Risk: medium** — Option B is the validation owner's recommendation, not a
CGI-confirmed rule. If CGI confirms `Duplicated` should count as a loss, the
change is a one-line move from `DUPLICATE_REASONS` into the lost set; nothing
downstream of `classify_opportunity_outcome` needs to change.

---

## 6. Fallback assumptions

Full machine-readable rules are in
[`config/fallback_assumptions.yaml`](../config/fallback_assumptions.yaml).
Summary:

| rule_id | primary | fallback | when fallback applies | risk |
|---|---|---|---|---|
| `revenue_hierarchy` | `total_estimated_revenue` | `opportunity_estimated_revenue_base_cad` | primary is null | low |
| `delivery_window` | `revenue_start_date` | `close_date` | primary is null | low |
| `missing_duration` | actual value | 12 months | null or <= 0 | medium |
| `missing_probability` | actual value | 0 | null | medium |
| `status_reason_outcome` | `status_reason` | `status` | `status_reason` is null/blank | medium |
| `won_detection` | `status_reason == 'Won'` | (subsumed) | — | low |
| `do_not_sum_service_solution_revenue` | n/a | n/a | always — never sum | low |
| `late_stage_definition` | n/a | n/a | n/a | low |
| `baseline_reliability` | n/a | n/a | n/a | medium |

`won_detection` is now **subsumed by `status_reason_outcome`** — the new rule's
status fallback is exactly the Sprint 1 won-detection fallback, generalised to
every outcome. It is kept in the file as a back-reference only.

The two **medium-risk** fallbacks whose silent application can mask real data
issues are `missing_duration` and `missing_probability`. Recommend Lyken add a
counter to `compute_sales_load` and `compute_delivery_load` that exposes how
many rows triggered a default, so dashboard users can tell "zero effort" from
"missing data". `status_reason_outcome` is medium-risk for a different reason —
the Option B taxonomy is pending CGI confirmation (see §5).

---

## 7. Owner-level validation summary

24 distinct opportunity owners. Zero casing or whitespace variants once
normalized; zero rows where `opportunity_owner == opportunity_manager`, which
confirms the architecture's owner-is-not-manager assumption.

**Baseline reliability distribution** (`quarters_of_data` from `created_on`,
via `build_owner_aggregates`):

| reliability | quarters_of_data | n_owners |
|---|---|---:|
| High | >= 8 | 3 |
| Medium | 4–7 | 13 |
| Low | < 4 | 8 |

This is a change from Sprint 1, which observed no Low-tier owners. Of the 8
Low-tier owners, **2 have `quarters_of_data = 0`** — every one of their rows is
an opps1-exclusive record with a null `created_on`, so they have no usable
historical timeline at all. Their capacity scores cannot be computed against a
real baseline and should be shown with an explicit "insufficient history" state
in the dashboard, not a Low-confidence number.

**Owners with < 10 lifetime opportunities: 7.** These owners have a thin
historical record; their capacity scores should carry a Low reliability tag
regardless of `quarters_of_data`. Names are in the notebook output and should
be reviewed with CGI before being shown in the UI.

**Duplicate-row exclusion.** `build_owner_aggregates` deduplicates
`duplicate_flag` rows on `opportunity_id` (keep first) before aggregating, so a
duplicated join key cannot double-count an owner's revenue or deal counts. On
the current data `duplicate_flag` is 0, so this is a safeguard rather than an
active correction. `unmatched_flag` and `opps1_exclusive_flag` rows are kept —
they are legitimate distinct opportunities.

`build_owner_aggregates(cleaned_opportunity_df)` produces the columns Freya's
dashboard mock expects but Lyken's `director_df` does not yet emit:
`opportunity_owner`, `territory`, `late_stage_deal_count`,
`weighted_pipeline_revenue`, `inferred_delivery_commitments`,
`open_opportunity_count`, `lost_opportunity_count`,
`duplicate_opportunity_count`, `quarters_of_data`, `baseline_reliability`.
Lyken can join this onto his `director_df` on `opportunity_owner`. The full
24-row table is in the notebook and a CSV copy under `data/processed/`
(gitignored — regenerate locally).

---

## 8. Field reliability for scoring

`build_field_reliability_report(cleaned_opportunity_df)` rates each validated
field as a scoring input. The rating is **computed** from null and anomaly
rates, not hand-assigned: a field is `reliable` when the worse of its null
rate and anomaly rate is under 1%, `use_with_care` under 15% (a documented
fallback covers the gap), and `not_yet` at or above 15% or where semantics are
unresolved.

| field | reliability | usable for scoring | fallback rule | notes |
|---|---|---|---|---|
| `opportunity_owner` | reliable | yes | — | 0 nulls, no casing variants; primary grouping key |
| `opportunity_manager` | reliable | yes | — | 0 nulls; distinct from owner on every row |
| `status` | reliable | yes | `status_reason_outcome` | 0 nulls, 3 values; bucketing via `classify_opportunity_outcome` |
| `status_reason` | reliable | yes | `status_reason_outcome` | 0.58% null; the taxonomy helper resolves the Sprint 1 status-disagreement concern |
| `sales_stage` | reliable | yes | `late_stage_definition` | 0 nulls; all 7 values map to the architecture's stage table |
| `probability` | reliable | yes | `missing_probability` | 0.88% null; explicit zeros are valid values; default-fill should be counted |
| `created_on` | reliable | yes | — | 0.58% null; 0 rows dated after today |
| `total_estimated_revenue` | use with care | yes | `revenue_hierarchy` | 0.58% null but 291 explicit zeros (3.3%); covered by the revenue hierarchy |
| `opportunity_estimated_revenue_base_cad` | use with care | yes | `revenue_hierarchy` | 12.20% null (the unmatched opps2 rows); agrees with the primary on 99.5% of the overlap |
| `close_date` | use with care | yes | `delivery_window` | 4.17% null + 379 close-before-created rows (down from a mis-counted 3,049); usable as the delivery-window fallback start |
| `revenue_start_date` | use with care | yes | `delivery_window` | 12.49% null overall, but 100% populated on Won deals where the window is computed |
| `project_duration_number_of_months` | use with care | yes | `missing_duration` | 9.74% null + 43 non-positive + 152 over 60 months; default-fill should be counted |
| `service_solution_estimated_revenue` | not yet | **no** | `do_not_sum_service_solution_revenue` | 43.83% null; a within-opportunity breakdown — must not be summed into scoring revenue |

**Changes from the Sprint 1 ratings.** `status_reason` moves from *use with
care* to *reliable* because `classify_opportunity_outcome` now resolves the
15-row Won-detection disagreement. `close_date` moves from *needs CGI
clarification* to *use with care* because the normalization fix shrank the
ordering anomaly from 3,049 to 379. `total_estimated_revenue` moves to *use
with care* because the report now counts its 291 explicit zeros as anomalies a
scoring consumer should know about. `service_solution_estimated_revenue` is the
only field **not usable for formal scoring**.

The targeted, scoring-focused version of this table — reliable / risky /
not-usable, with fallback hierarchies and the owner-level findings — is in
[`docs/scoring_input_reliability_handoff.md`](scoring_input_reliability_handoff.md),
written for Lyken.

---

## Open questions

**For Lyken (capacity_engine):**
1. Import `classify_opportunity_outcome` for Won/Lost/Open routing, or want
   Role 2 to wire it into `compute_delivery_load` / `compute_sales_load` on a
   separate PR?
2. Add row-counter outputs for `probability = 0` and `duration = 12`
   default-fills so the dashboard can tell missing-data rows from real-zero
   rows?
3. Two owners have `quarters_of_data = 0` (history is entirely opps1-exclusive
   with null `created_on`) — agree they should get an explicit "insufficient
   history" state rather than a Low-confidence score?
4. `build_owner_aggregates` now emits ten columns including
   `open/lost/duplicate_opportunity_count` — confirm the join contract on
   `opportunity_owner` works for `director_df`.

**For Yixiao (opportunity_cleaner):**
1. `close_before_created_flag` uses an un-normalized timestamp comparison and
   over-counts by 2,670 (3,049 vs the corrected 379). Please normalize both
   dates to calendar date in `opportunity_cleaner.py`.
2. Confirm the Option B `status_reason` taxonomy (§5) so `build_owner_base_summary`
   can stop folding `Duplicated` into `lost_opportunity_count` and import
   `classify_opportunity_outcome` instead.
3. The 1,067 unmatched opps2 rows — expected (CGI staged-loading) or a coverage
   gap to escalate?

**For CGI (Monday sync):**
1. **379 rows where `close_date < created_on`** (calendar-date basis) — what is
   the CRM convention: backdating, projected-close-date semantics, or a
   migration artefact?
2. 152 rows with `project_duration > 60 months` — legitimate long-term
   framework agreements or data-entry errors? (subset exported)
3. 3 rows with `total_estimated_revenue > $100M` — confirmable as real?
4. `status_reason == "Duplicated"` (461 rows, 3 owners) — confirm these are CRM
   duplicate records that should be excluded from win/loss counts (Option B).

---

## Use of Generative AI

Anthropic Claude (Opus 4.7) was used for drafting and editing assistance on
this document. All validation logic, computed metrics, and conclusions are my
own — derived from running the validator functions in `src/data_validator.py`
against the team's `cleaned_opportunity_df`, and verified against the
underlying data. No CGI data (opportunity rows, owner names, revenue figures,
proposal text) was sent to the tool.

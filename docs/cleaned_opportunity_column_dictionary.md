# Cleaned Opportunity Column Dictionary

`cleaned_opportunity_df` is the Sprint 2 prepared opportunity-level handoff
created from the Week 1 merged `opportunity_df`.

This dictionary documents the main columns used by validation, scoring, and
dashboard handoff work. The cleaned dataframe preserves the original Week 1
columns and adds non-breaking Sprint 2 alias and data-quality flags.

Revenue fields remain separate in this dataset. No authoritative revenue
fallback is finalized here. In particular,
`service_solution_estimated_revenue` should not be summed with
`total_estimated_revenue` unless validation confirms the field semantics.

| Column name | Category | Description | Notes / downstream usage |
|---|---|---|---|
| `opportunity_id` | identifier | CRM opportunity identifier used as the merge key. | Primary row identifier for joining and duplicate checks. |
| `opportunity_owner` | owner | Owner/director associated with the opportunity. | Primary grouping field for owner-level validation and scoring sanity checks. Blank or missing owners are flagged by `missing_owner_flag`. |
| `opportunity_manager` | owner | Manager or reporting-structure field from CRM. | Retained as metadata. Not the Sprint 2 capacity grouping field. |
| `status` | status | High-level opportunity status. | Used for simple open/won/lost owner summary buckets. Final scoring logic may use more precise validation rules. |
| `sales_stage` | status | CRM sales stage for the opportunity. | Used by scoring to understand pipeline maturity. Validation should check stage coverage against expected stage weights. |
| `probability` | status | Opportunity probability after numeric coercion where present. | Used for weighted pipeline logic. Missing and out-of-range values are flagged separately. |
| `created_on` | date | CRM created date after date coercion where present. | Useful for historical baselines and validation of date plausibility. |
| `close_date` | date | CRM close date after date coercion where present. | Useful as metadata and possible fallback context, but date-order anomalies should be reviewed. |
| `revenue_start_date` | date | Expected or actual revenue start date after date coercion where present. | Used by scoring/validation to reason about delivery windows. Missing values are flagged. |
| `project_duration_number_of_months` | date | Project duration in months after numeric coercion where present. | Used by scoring to estimate load windows. Missing or non-positive values are flagged. |
| `total_estimated_revenue` | revenue | Opportunity-level revenue field from the opps2/base side where available. | Kept separate from other revenue fields. No authoritative fallback is created in the cleaner. |
| `opportunity_estimated_revenue_base_cad` | revenue | Opportunity-level CAD revenue field from the opps1 side where available. | Kept separate as a possible validation/scoring fallback candidate. Fallback hierarchy is not finalized here. |
| `service_solution_estimated_revenue` | revenue | Service or solution-level estimated revenue where available. | Do not add to opportunity-level revenue unless validation confirms semantics. |
| `service_solution` | supplemental | Service/solution label carried from opps1 where available. | Supplemental context for analysis and dashboard filtering. |
| `opportunity_product` | supplemental | Product field carried from opps1 where available. | Supplemental context for analysis and dashboard filtering. |
| `ip` | supplemental | IP-related field carried from opps1 where available. | Supplemental context. Semantics should be confirmed before using in scoring. |
| `source_file_flag` | merge flag | Sprint 2 alias derived from `source_table` when available. Defaults to `unknown` if source metadata is absent. | Downstream-friendly source indicator for validation, scoring, and dashboard handoff. |
| `duplicate_flag` | merge flag | Sprint 2 alias derived from `is_duplicate_join_key` when available. Defaults to `False` if absent. | Indicates rows whose opportunity ID is duplicated in the merged output. |
| `unmatched_flag` | merge flag | Sprint 2 alias derived from `is_unmatched_opps2_base` when available. Defaults to `False` if absent. | Identifies opps2/base records not matched to opps1. |
| `opps1_exclusive_flag` | merge flag | Sprint 2 alias derived from `is_opps1_exclusive` when available. Defaults to `False` if absent. | Identifies opportunities found only in opps1 and appended to the base output. |
| `missing_owner_flag` | data quality flag | True when `opportunity_owner` is null or blank. | Helps validation and owner-level summaries identify records with unclear ownership. |
| `missing_probability_flag` | data quality flag | True when `probability` is missing after numeric coercion. | Helps distinguish true zero probability from missing probability. |
| `invalid_probability_flag` | data quality flag | True when `probability` is below 0 or above 100. | Should be reviewed before probability-weighted scoring. |
| `missing_revenue_flag` | data quality flag | True when both `total_estimated_revenue` and `opportunity_estimated_revenue_base_cad` are missing, where those fields exist. | Does not define authoritative revenue. It only marks rows with no opportunity-level revenue candidate. |
| `missing_duration_flag` | data quality flag | True when `project_duration_number_of_months` is missing after numeric coercion. | Helps quantify rows that may need duration fallback assumptions. |
| `invalid_duration_flag` | data quality flag | True when `project_duration_number_of_months` is less than or equal to 0. | Should be reviewed before delivery-window or load calculations. |
| `missing_revenue_start_date_flag` | data quality flag | True when `revenue_start_date` is missing after date coercion. | Helps validation quantify delivery-window uncertainty. |
| `close_before_created_flag` | data quality flag | True when both dates are present and `close_date` is earlier than `created_on`. | Indicates date-order anomalies that need validation/CGI interpretation before time-to-close analysis. |

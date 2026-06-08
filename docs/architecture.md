# Capacity Analyzer Architecture

## Purpose

The Capacity Analyzer helps CGI Atlantic / Media Atlantic leadership understand
each director's current workload, compare it with that director's historical
workload, and discuss who may have capacity to take on additional sales or
operational work.

The project has two deliverables:

1.  A director capacity dashboard that compares current workload against each director's own historical baseline.
2.  An RFP assignment tool that estimates the effort required by a new RFP and
    recommends directors using capacity, service-fit, and semantic retrieval
    signals.

This prototype is scoped to the CGI Atlantic / Media Atlantic business unit based on the opportunity data currently available. It should not be presented as a Canada-wide dashboard unless broader data becomes available.

The system uses processed CRM-derived opportunity data, historical RFP/proposal
text, standard Python data processing, and optional Azure OpenAI services. LLMs
are used for summarization and explanation, not for core numeric scoring.

## Final Prototype Boundary

This repository represents a stakeholder-facing final capstone prototype, not a
production staffing system. Recommendations are decision-support outputs that
require stakeholder validation before any operational use.

Key boundaries:

- Capacity results are relative workload signals, not exact working hours,
  utilization, or guaranteed availability.
- RFP recommendations are not final CGI assignment decisions.
- Retrieved proposal chunks are semantic evidence only. They do not prove
  director involvement, director experience, or opportunity ownership because
  reliable proposal-to-CRM linkage is not available in the current proposal
  chunks.
- Azure/Chroma retrieval is optional and backend-validated. Local fallback
  retrieval remains supported for demo and development environments.

## Inputs

Expected local inputs:

``` text
data/csv_files/anonymized_opps_1.xlsx
data/csv_files/anonymized_opps_2.xlsx
data/proposals_responses.json
data/.env
```

The data files are local and ignored by git.

## Streamlit Entry Point

The integrated UI entry point is:

```bash
streamlit run app/app.py
```

`app/app.py` owns the two-page Streamlit experience:

1.  **Director Capacity Dashboard**
2.  **RFP Assignment Tool**

The app loads capacity data once through the dashboard data-loading helper and
passes the active capacity dataframe into the RFP assignment flow so
recommendations can use the same capacity signals shown on the dashboard.

## Data Loading Precedence

The dashboard is designed to run against local prepared data without requiring
a live production CRM connection. Data loading proceeds in this order:

1.  Load cleaned/processed opportunity data when available and compute director
    capacity from the capacity engine.
2.  Load a prebuilt `data/processed/director_capacity_df.csv` when live
    computation is unavailable.
3.  Fall back to synthetic mock capacity data for demo/development continuity,
    clearly labelled in the UI.

The final app should describe this as processed or computed CRM-derived data,
not live production CRM integration.

## Core Entities

| Entity | Source | Notes |
|----|----|----|
| Opportunity | `opps1`, `opps2` | CRM opportunity records keyed by `opportunity_id` |
| Director / senior leader | `opportunity_owner` | Primary capacity dashboard entity |
| Opportunity manager | `opportunity_manager` | Optional metadata / supporting reporting field |
| RFP / proposal | `proposals_responses.json` | Historical proposal and response text |
| Service solution | `opps1` | Supplemental opportunity detail; aggregated by owner from open/won opportunities for the RFP service-fit signal |

CGI confirmed that `opportunity_owner` is the primary field representing the director whose capacity should be estimated. `opportunity_manager` is more like a direct-report or reporting-structure field; it can be retained as metadata, but it is not part of the MVP scoring model.

## Data Integration

CGI confirmed that the two opportunity Excel files are different views of the same underlying CRM opportunity data. Use `opps2` as the base opportunity table because it has the richer CRM schema, then supplement it with useful fields from `opps1`.

Merge strategy:

1.  Clean and normalize column names in both Excel files.
2.  Use `opps2` as the base table.
3.  Left-join selected `opps1` fields onto overlapping `opportunity_id` values.
4.  Append `opps1`-exclusive opportunity IDs.
5.  Preserve duplicate opportunity rows initially, but flag them for downstream cleaning.
6.  Cross-match opportunities across both files to fill date, duration, and revenue fields where possible.

Supplemental `opps1` fields:

``` text
opportunity_product
service_solution
service_solution_estimated_revenue
ip
delivery_territory_center
```

Revenue definition:

``` text
authoritative_revenue =
    total_estimated_revenue
    or matched opportunity_estimated_revenue_base_cad when total_estimated_revenue is unavailable
```

CGI confirmed that the total revenue field should be treated as the authoritative opportunity-level revenue. Where the total field is unavailable, use the matched opportunity-level revenue from the other CRM view. Do not calculate opportunity-level revenue as `opportunity_estimated_revenue_base_cad + service_solution_estimated_revenue`. `service_solution_estimated_revenue` can support service mix or solution breakdown analysis, but it should not be added to the opportunity-level revenue because that may double-count revenue.

## Capacity Model

Capacity is derived, not directly available as a source column. The model should compare each director's current workload against that same director's historical baseline.

For v1, current workload is estimated as the sum of two components:

1.  Sales pipeline load
2.  Inferred delivery load

``` text
current_load = sales_load + delivery_load
```

Open opportunities alone are too sparse for a reliable capacity view. The EDA found only 374 currently open opportunities, so the dashboard should also estimate delivery commitments using dates, project duration, and historical workload.

### Sales Pipeline Load

For opportunities still in the sales pipeline, estimate opportunity-level workload with interpretable business factors:

``` text
sales_load_i =
    stage_weight_i
  * (probability_i / 100)
  * log1p(authoritative_revenue_i)
  * duration_weight_i
```

`duration_weight_i` is bounded so that duration does not inflate workload without limit. For v1, compute it from log-scaled `project_duration_number_of_months`, normalized to a 12-month project.

Current implementation:

``` text
duration_weight_i = log1p(project_duration_number_of_months_i) / log1p(12)
```

If `project_duration_number_of_months` is missing, use a documented 12-month default and keep the assumption visible in the methodology.

Initial `stage_weight` values should use the observed CRM `sales_stage` values and can be refined through stakeholder feedback. Example starting point:

``` text
0-Lead/Suspect             : 0.4
1-Identification           : 0.6
2-Qualification            : 0.8
3-Bid Planning             : 1.0
4-Proposal                 : 1.3
5-Client Decision          : 1.5
6-Negotiation&Signature    : 1.7
```

Sales load applies only to opportunities classified as open by the shared opportunity-outcome helper. Won opportunities move to delivery load. Lost, cancelled, duplicated, and closed opportunities should not contribute to current sales pipeline load.

Sales pipeline fields:

``` text
status
status_reason
sales_stage
probability
authoritative_revenue
project_duration_number_of_months
```

### Inferred Delivery Load

For won or historical opportunities that may still be in delivery, estimate delivery load from dates, duration, and revenue:

``` text
monthly_revenue_i = authoritative_revenue_i / project_duration_number_of_months_i

delivery_load_i = delivery_active_i * log1p(monthly_revenue_i)
```

Where:

``` text
delivery_active_i = 1 if opportunity is Won and current_date falls within the estimated delivery window
```

CGI confirmed that using won opportunities plus date and duration fields is a reasonable proxy for delivery load.

Preferred delivery-window logic:

``` text
revenue_start_date <= current_date <= revenue_start_date + project_duration_number_of_months
```

Fallback delivery-window logic when `revenue_start_date` is missing:

``` text
close_date <= current_date <= close_date + project_duration_number_of_months
```

If start date or duration is still missing after cross-matching both Excel files, delivery load should either use a documented fallback assumption or be calculated only for records with enough date information.

For v1, delivery load is treated as active if the current date falls within the estimated delivery window. This means projects receive similar delivery contribution while active, even if one is near the start and another is near the end.

A future refinement may down-weight delivery load as a project approaches its estimated end date, for example by multiplying delivery load by the proportion of estimated delivery time remaining.

Delivery load is inferred from opportunity dates and duration fields. It should be treated as a heuristic estimate, not as an exact measure of director working hours, because the dataset does not include timesheets or calendar data.

Delivery-load fields:

``` text
status
status_reason
authoritative_revenue
revenue_start_date
close_date
project_duration_number_of_months
```

CGI confirmed that the `opportunity_owner` can be assumed to remain responsible during delivery for the MVP. Therefore, inferred delivery load should contribute to the same owner-level capacity model as sales pipeline load.

### Director-Level Current Load

Aggregate opportunity-level sales and delivery load by `opportunity_owner`:

``` text
current_load_owner =
    sum(sales_load_i for active sales pipeline opportunities)
  + sum(delivery_load_i for inferred active delivery commitments)
```

Keep supporting fields for dashboard explainability:

``` text
open_deal_count
late_stage_deal_count
weighted_pipeline_revenue
inferred_delivery_commitments
current_load_owner
```

Then compare against each director's own historical baseline:

``` text
relative_load_owner = current_load_owner / historical_average_load_owner
capacity_score_owner = max(0, 1 - min(relative_load_owner, 1))
```

Use `relative_load_owner` as the primary dashboard metric. The legacy `capacity_score_owner` remains in the backend output for compatibility, but it is not displayed in the dashboard because it is capped at 0 once `relative_load_owner` reaches 1 and therefore does not express overextension severity.

Temporary capacity labels are assigned from `relative_load_owner`, not from
the capped `capacity_score_owner`:

``` text
Available             : relative_load_owner <= 0.85
Near Historical Norm  : 0.85 < relative_load_owner < 1.25
High Load             : 1.25 <= relative_load_owner < 2.00
Overextended          : relative_load_owner >= 2.00
No baseline           : historical_average_load_owner is missing or zero
```

This calibration is a project-side temporary decision based on the observed
director-level `relative_load_owner` distribution and a business interpretation
that carrying at least 2x historical norm should be called `Overextended`.
CGI should review and adjust these thresholds before production use.
Thresholds should remain configurable, either in the dashboard or in a config
file, so they can be refined through stakeholder review.

In the dashboard, row-level filters should narrow the current opportunities
being viewed, while historical baselines remain anchored to the full selected
owner/territory history. This keeps `relative_load_owner` interpretable as
filtered current workload versus a stable historical norm.

## Historical Baseline

Build the historical baseline from the actual date range in the data rather than a hard-coded range, ending no later than the current/as-of quarter. For consistency, the historical baseline should use the same workload contribution logic as the current-load calculation, rather than only counting opportunities.

A simple opportunity count can be used as an initial baseline, but the preferred baseline should include stage, probability, revenue, and estimated duration where available.

For each owner and quarter:

``` text
historical_load_owner_q =
    sum(sales_load_i active during quarter q)
  + sum(delivery_load_i active during quarter q)
```

Historical workload should apply the same status and stage rules as current workload. Lost, cancelled, duplicated, and irrelevant closed records should not inflate the historical baseline.

An opportunity can be considered active during a quarter only if it passes the relevant sales-load or delivery-load filters and:

``` text
created_on <= quarter_end
and
(close_date is null or close_date >= quarter_start)
```

Optional delivery-window estimate:

``` text
revenue_start_date to revenue_start_date + project_duration_number_of_months
```

Baseline outputs:

``` text
historical_mean_load
historical_std_load
historical_max_load
quarters_seen
baseline_reliability_flag
```

Directors with too few historical quarters should be flagged as having a less reliable baseline.

## RFP Assignment

The RFP assignment tool estimates the effort required by a new RFP and ranks directors by capacity and fit.

Historical proposals must be chunked before embedding. The EDA found that most proposal documents exceed the embedding context limit when treated as a single input.

RFP processing pipeline:

1.  Extract proposal and response text.
2.  Chunk documents with overlap.
3.  Load the local proposal corpus when available, with a small sample corpus as fallback.
4.  For a new RFP, extract uploaded TXT/DOCX/text-based PDF content or use
    pasted text. Text-based PDF upload depends on `pypdf` in the active
    environment.
5.  Call `generate_assignment_context()` to orchestrate retrieval, effort
    estimate, summary generation, risk flags, and director recommendations.
6.  Use the submitted RFP text as a query against chunked historical/sample
    corpora.
7.  Prefer Azure OpenAI embeddings with Chroma only when Azure config,
    optional `chromadb`, and a reusable Chroma collection are available.
8.  Reuse an existing Chroma collection by default. Do not rebuild Chroma on
    every Streamlit request.
9.  Rebuild Chroma only when explicitly requested with `RFP_REBUILD_CHROMA=1`,
    usually for backend validation or maintenance.
10. Fall back to local retrieval over the same corpus when Azure/Chroma config,
    `chromadb`, the reusable store, or the Chroma query path is unavailable.
11. Retrieve similar historical proposal/RFP chunks as semantic evidence.
12. Estimate effort level using deterministic heuristics, enriched by Azure
    OpenAI chat when configured.
13. Rank directors using capacity, retrieval similarity, service-solution fit,
    capacity label, and risk flags.

RFP effort features:

``` text
document length
similar historical RFPs
service solution or domain keywords
estimated duration
estimated revenue
delivery complexity
required response effort
client or territory similarity
```

### Experience Definition

Experience should not be based on text similarity alone. Text similarity measures semantic relevance, but it does not measure whether a director has a strong business track record on similar work.

Use two experience components:

``` text
experience_score =
    semantic_relevance_score
  + confidence_adjusted_structured_track_record_score
```

Semantic relevance measures how similar the new RFP is to a director's historical opportunities, proposals, service solutions, or client context.

CGI confirmed that experience should combine semantic relevance with structured track record. Structured track record measures outcome quality and historical success. It should use smoothed rates and confidence adjustment based on sample size and data completeness.

Current prototype boundary: reliable director-to-proposal linkage is not available in the proposal chunks because `opportunity_owner` and `opportunity_id` are not populated consistently. Therefore, retrieved chunks are treated as semantic evidence for the RFP, not proof of a director's prior experience. The final prototype uses director capacity, retrieval similarity, and an owner-level `service_solution` profile as the implemented fit signals.

Candidate features include:

``` text
smoothed_win_rate
revenue_weighted_win_rate
similar_deal_count
successful_similar_deal_count
median_similar_deal_size
average_sales_cycle_length
client_or_sector_recurrence
```

The confidence adjustment reflects the reliability of the structured experience estimate. Larger and more complete samples should be treated as more reliable, while very small samples should be shrunk toward the overall average.

For example, a director with 5 wins out of 5 similar deals should not automatically outrank a director with 80 wins out of 100 similar deals. The 5/5 record is promising, but the 80/100 record is based on much stronger evidence.

Some structured features may require proxies or additional CGI metadata:

``` text
client_tier: not directly available unless CGI provides it; approximate with revenue size or client recurrence if needed
avg_stage_progression_time: not directly available without full CRM stage history; approximate with created_on to close_date if needed
sector: not directly available unless mapped from client, service solution, or additional CGI metadata
```

Assignment score:

``` text
assignment_score =
    capacity_score_weight * capacity_score
  + retrieval_weight * top_retrieval_similarity
  + service_fit_weight * service_solution_match
  + capacity_label_bonus
```

The final prototype ranks every candidate director before selecting the top three recommendations. Because reliable proposal-to-director linkage is not yet available, the implemented ranking is capacity-aware and service-aware, but it should not be described as a validated historical-performance ranking.

The tool should return:

``` text
top recommended directors
capacity justification
similar historical RFPs
estimated effort level
risk flags
LLM-generated explanation
```

## LLM Responsibilities

LLMs should be used for interpretation and explanation, not as the source of truth for numeric scoring.

LLM tasks:

``` text
RFP summarization
effort explanation
director match-reason enrichment
```

Non-LLM tasks:

``` text
data cleaning
capacity scoring
historical baseline calculation
revenue calculations
ranking formula
dashboard metrics
```

## Application Architecture

``` text
DATA LAYER
  anonymized_opps_1.xlsx
  anonymized_opps_2.xlsx
  proposals_responses.json
  data/.env

PROCESSING LAYER
  data_loader.py
    load Excel files
    load proposal JSON
    validate required files

  opportunity_cleaner.py
    clean column names
    normalize date and numeric fields
    merge opps2 base with opps1 supplemental fields
    append opps1-exclusive rows
    flag duplicates and sparse fields

  identity_resolver.py
    define opportunity_owner as director
    retain opportunity_manager as optional metadata

CAPACITY ENGINE
  capacity_engine.py
    compute_sales_load()
    compute_delivery_load()
    compute_current_load_by_owner()
    compute_historical_baseline()
    compute_relative_load()
    compute_capacity_score()
    assign_capacity_label()

RFP ENGINE
  rfp_preprocessor.py
    extract text
    chunk proposal and response documents
    prepare metadata

  vector_store.py
    embed chunks with Azure OpenAI
    store embeddings in Chroma when optional backend dependencies are available
    reuse existing Chroma collections by default
    support explicit rebuild with RFP_REBUILD_CHROMA=1
    query against chunked historical/sample corpora
    provide local fallback retrieval

  rfp_engine.py
    generate_assignment_context()
    retrieve similar RFPs
    estimate RFP effort
    match against director capacity and service_solution profiles
    rank recommended directors
    enrich summary, effort, and match reasons with Azure OpenAI chat when configured

PRESENTATION LAYER
  app/app.py Streamlit app
    Page 1: Director Capacity Dashboard
    Page 2: RFP Assignment Tool
```

## Dashboard Design

Page 1: Director Capacity Dashboard

Flow:

``` text
local processed opportunity data or prebuilt capacity output
-> capacity_engine director-level calculations
-> Streamlit filters and summary cards/charts
-> stakeholder-facing capacity labels and relative-load evidence
```

``` text
relative load by director
capacity label: Available / Near Historical Norm / High Load / Overextended / No baseline
label mix
current load vs historical average on a log scale
open opportunities
weighted pipeline
estimated delivery commitments
late-stage opportunities
workload trend over time on a log scale
owner-level view with optional manager metadata
```

Filters:

``` text
territory
opportunity owner
status
sales stage
opportunity type
sales model
created date range
```

Territory and opportunity-owner filters define the selected population for both current workload and baseline. Row-level filters such as status, sales stage, opportunity type, sales model, and created date range narrow the current workload and trend being viewed, while the historical average remains anchored to the full selected owner/territory history.

Page 2: RFP Assignment Tool

Flow:

``` text
uploaded TXT/DOCX/text-based PDF or pasted RFP text
-> upload text extraction (PDF requires pypdf)
-> generate_assignment_context()
-> retrieval examples from Azure/Chroma reuse or local fallback
-> summary, effort estimate, recommendations, risk flags, and caveats
```

``` text
upload TXT/DOCX/text-based PDF or paste RFP text
estimated effort level
retrieved similar historical RFPs
recommended directors
capacity explanation
experience match explanation
risk flags
```

## Evaluation and Refinement

The project does not train a supervised ML model, but it still needs business-facing evaluation. Evaluation should focus on whether the dashboard outputs and RFP recommendations match CGI stakeholder expectations.

Recommended evaluation methods:

``` text
CGI stakeholder review
sanity checks against known director workload
capacity threshold sensitivity analysis
recommendation justification review
qualitative feedback loop
case studies on selected RFPs and directors
```

Capacity labels and RFP recommendation weights should be refined after CGI reviews early director-level outputs. The feedback loop should test whether specific directors labeled `Available`, `Near Historical Norm`, `High Load`, `Overextended`, or `No baseline` align with business intuition.

## Build Phases

| Phase | Work                                | Output                 |
|-------|-------------------------------------|------------------------|
| 1     | Clean and merge opportunity data    | `opportunity_df`       |
| 2     | Resolve owner-level director entity | `director_df`          |
| 3     | Build historical baseline           | `baseline_df`          |
| 4     | Build current capacity scoring      | `director_capacity_df` |
| 5     | Build Streamlit capacity dashboard  | Deliverable 1          |
| 6     | Chunk and retrieve historical RFPs  | Azure/Chroma path with local fallback |
| 7     | Build RFP effort estimator          | `rfp_engine.py`        |
| 8     | Build director assignment ranking   | Deliverable 2          |
| 9     | Add LLM-generated explanations      | Implemented when Azure chat is configured |

## Design Notes

The architecture reflects these EDA findings and CGI meeting decisions:

1.  The current prototype is scoped to CGI Atlantic / Media Atlantic, not all CGI Canada.
2.  Only a small share of opportunities are currently open, so current load cannot rely only on `status = Open`.
3.  `opportunity_owner` is the director-level capacity entity confirmed by CGI.
4.  `opportunity_manager` should be retained as optional metadata, but it is not part of MVP scoring.
5.  Won opportunities can be used as a delivery-load proxy for the corresponding `opportunity_owner`.
6.  Proposal and RFP documents require chunking before embedding.
7.  `total_estimated_revenue` or matched opportunity-level total revenue is the authoritative revenue input; do not add service-solution revenue to opportunity total revenue.
8.  `service_solution` can support service-fit matching, but the final prototype only uses it as a lightweight owner-level profile, not as proof of director expertise.
9.  Retrieved proposal chunks currently lack reliable `opportunity_owner` / `opportunity_id` linkage, so retrieval evidence should be described as semantic similarity evidence rather than director experience evidence.
10. Some fields are too sparse for capacity scoring, including `proposal_submission_date`, `rfp_release_date`, `comments`, and `free_field_text_2`.

# Dashboard Requirements

## Summary

-   Add `app/app.py` Streamlit dashboard skeleton.
-   Add two-page structure for Director Capacity Dashboard and RFP Assignment Tool placeholder.
-   Display mock capacity score, capacity labels, current load vs historical average, workload trend, and owner-level director summary table.
-   Include architecture fields for open opportunities, late-stage opportunities, weighted pipeline, and estimated delivery commitments.
-   Add placeholder filters for territory, capacity label, opportunity owner, status, sales stage, date range, opportunity type, and sales model.
-   Add RFP input placeholders for document upload and pasted RFP text.
-   Add RFP result placeholders for estimated effort, similar historical RFPs, recommended directors, capacity explanation, experience match explanation, and risk flags.
-   Add `app/mock_data.py` synthetic data helpers for Week 1 UI development.
-   Add Streamlit theme config under `.streamlit/config.toml`.

## Notes

-   RFP Assignment Tool page is UI-only for now.
-   Backend RFP functions/files are expected to be added by Jai's Role 5 work.
-   Dashboard uses synthetic mock data until the cleaned opportunity data and capacity engine are integrated.

## Dashboard Data Contract

The Director Capacity Dashboard expects one owner-level capacity table with one row per `opportunity_owner`.

Required columns:

| Column | Description |
|----|----|
| `opportunity_owner` | Director or owner name displayed in charts and tables. |
| `territory` | Territory or delivery center label used for filtering. |
| `historical_avg_load` | Owner's historical average workload score. |
| `relative_load` | Current load divided by historical average load. |
| `current_load` | Current workload score. |
| `capacity_score` | Availability score from 0 to 1. |
| `capacity_label` | One of `Available`, `At Capacity`, or `Overextended`. |
| `open_deal_count` | Count of currently open opportunities. |
| `late_stage_deal_count` | Count of open opportunities in late sales stages. |
| `weighted_pipeline_revenue` | Probability-weighted open pipeline revenue in CAD. |
| `inferred_delivery_commitments` | Count of active inferred delivery commitments. |
| `quarters_of_data` | Number of historical quarters available for the owner. |
| `baseline_reliability` | Reliability label for the historical baseline. |

The workload trend chart expects one row per owner per quarter.

Required columns:

| Column              | Description                           |
|---------------------|---------------------------------------|
| `opportunity_owner` | Owner name.                           |
| `territory`         | Territory or delivery center label.   |
| `quarter_label`     | Display label, for example `Q1 2026`. |
| `quarter_sort`      | Numeric sort order for charting.      |
| `current_load`      | Workload score for that quarter.      |
| `historical_avg`    | Owner historical average workload.    |

## RFP Integration Contract

For integration, it would be helpful if the RFP pipeline eventually returns a structured object with fields matching the dashboard sections.

Suggested shape:

``` json
{
  "effort": {
    "level": "Low | Medium | High",
    "estimated_duration": "...",
    "rationale": "..."
  },
  "similar_rfps": [
    {
      "title": "...",
      "similarity_score": 0.0,
      "matched_chunk": "...",
      "source": "..."
    }
  ],
  "recommended_directors": [
    {
      "director_name": "...",
      "capacity_label": "Available | At Capacity | Overextended",
      "assignment_score": 0.0,
      "capacity_explanation": "...",
      "experience_match_explanation": "...",
      "risk_flags": ["..."]
    }
  ],
  "notes": "..."
}
```

## Validation

-   Manual browser checked: `conda activate cgi-capstone && python -m streamlit run app/app.py`.
-   Sanity checked mock data output shapes:
    -   8 director capacity rows.
    -   64 trend rows.
-   Streamlit test harness passed:
    -   Dashboard page: 0 exceptions.
    -   RFP page: 0 exceptions.
    -   Dashboard filters detected: 7 selectboxes + 1 date input.
    -   RFP uploader detected: 1 file uploader.
-   Streamlit dashboard page executed without errors.
-   Streamlit RFP placeholder page executed without errors.

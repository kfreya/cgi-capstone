"""
Week 2 regression tests for capacity_engine.py

Focus:
- authoritative_revenue fallback
- open opportunity filtering
- late-stage counting logic
- capacity_score-based labels
- null capacity score handling
"""

import pandas as pd

from capacity_engine import (
    compute_sales_load,
    compute_current_load_by_owner,
    assign_capacity_label,
)


def test_authoritative_revenue_used_over_total_estimated():
    """
    authoritative_revenue should be preferred over
    total_estimated_revenue when both exist.
    """

    df = pd.DataFrame(
        {
            "probability": [100],
            "sales_stage": ["4-Proposal"],
            "status_reason": ["open"],
            "project_duration_number_of_months": [12],

            # intentionally conflicting values
            "authoritative_revenue": [1000],
            "total_estimated_revenue": [999999],
        }
    )

    result = compute_sales_load(df)

    sales_load = result.loc[0, "sales_load"]

    # if authoritative_revenue is used,
    # load should remain relatively small
    assert sales_load < 20


def test_weighted_pipeline_revenue_only_open():
    """
    weighted_pipeline_revenue should only
    include open opportunities.
    """

    df = pd.DataFrame(
        {
            "opportunity_owner": ["Alice", "Alice"],

            "status_reason": [
                "open",
                "won",
            ],

            "sales_stage": [
                "4-Proposal",
                "4-Proposal",
            ],

            "probability": [
                100,
                100,
            ],

            "authoritative_revenue": [
                1000,
                5000,
            ],

            "project_duration_number_of_months": [
                12,
                12,
            ],

            "revenue_start_date": [
                "2026-01-01",
                "2026-01-01",
            ],

            "close_date": [
                "2026-01-01",
                "2026-01-01",
            ],

            "opportunity_id": [
                1,
                2,
            ],

            "delivery_territory_center": [
                "West",
                "West",
            ],
        }
    )

    grouped = compute_current_load_by_owner(df)

    weighted_revenue = grouped.loc[
        0,
        "weighted_pipeline_revenue",
    ]

    # only the open opportunity should count
    assert weighted_revenue == 1000


def test_late_stage_deal_count_only_open():
    """
    late_stage_deal_count should only count
    open late-stage opportunities.
    """

    df = pd.DataFrame(
        {
            "opportunity_owner": [
                "Alice",
                "Alice",
            ],

            "status_reason": [
                "open",
                "won",
            ],

            "sales_stage": [
                "5-Client Decision",
                "5-Client Decision",
            ],

            "probability": [
                100,
                100,
            ],

            "authoritative_revenue": [
                1000,
                1000,
            ],

            "project_duration_number_of_months": [
                12,
                12,
            ],

            "revenue_start_date": [
                "2026-01-01",
                "2026-01-01",
            ],

            "close_date": [
                "2026-01-01",
                "2026-01-01",
            ],

            "opportunity_id": [
                1,
                2,
            ],

            "delivery_territory_center": [
                "West",
                "West",
            ],
        }
    )

    grouped = compute_current_load_by_owner(df)

    late_stage_count = grouped.loc[
        0,
        "late_stage_deal_count",
    ]

    assert late_stage_count == 1


def test_capacity_label_uses_capacity_score():
    """
    capacity labels should be assigned
    using capacity_score thresholds.
    """

    df = pd.DataFrame(
        {
            "capacity_score": [
                0.8,
                0.5,
                0.1,
            ]
        }
    )

    result = assign_capacity_label(df)

    labels = result["capacity_label"].tolist()

    assert labels == [
        "Available",
        "At Capacity",
        "Overextended",
    ]


def test_null_capacity_score_returns_unknown():
    """
    null capacity scores should map to Unknown.
    """

    df = pd.DataFrame(
        {
            "capacity_score": [None]
        }
    )

    result = assign_capacity_label(df)

    assert (
        result.loc[0, "capacity_label"]
        == "Unknown"
    )
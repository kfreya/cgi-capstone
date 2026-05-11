"""
Week 1

Tests for capacity_engine.py.

These tests validate:
- sales load computation
- delivery load computation
- owner-level aggregation
- historical baseline generation
- relative load computation
- capacity score computation
- capacity label assignment

Utilization: python -m pytest tests/test_capacity_engine.py

"""

import pandas as pd

from src.capacity_engine import (
    assign_capacity_label,
    compute_capacity_score,
    compute_current_load_by_owner,
    compute_delivery_load,
    compute_historical_baseline,
    compute_relative_load,
    compute_sales_load,
)


def test_compute_sales_load_creates_positive_sales_load():
    df = pd.DataFrame(
        {
            "status": ["open"],
            "status_reason": ["Open"],
            "sales_stage": ["4-Proposal"],
            "probability": [80],
            "total_estimated_revenue": [100000],
            "project_duration_number_of_months": [12],
        }
    )

    result = compute_sales_load(df)

    assert "sales_load" in result.columns
    assert result.loc[0, "sales_load"] > 0


def test_compute_sales_load_sets_won_status_to_zero():
    df = pd.DataFrame(
        {
            "status": ["closed"],
            "status_reason": ["Won"],
            "sales_stage": ["6-Negotiation&Signature"],
            "probability": [100],
            "total_estimated_revenue": [500000],
            "project_duration_number_of_months": [24],
        }
    )

    result = compute_sales_load(df)

    assert result.loc[0, "sales_load"] == 0


def test_compute_delivery_load_creates_active_delivery_load():
    df = pd.DataFrame(
        {
            "status": ["closed"],
            "status_reason": ["Won"],
            "total_estimated_revenue": [1200000],
            "project_duration_number_of_months": [12],
            "revenue_start_date": ["2026-01-01"],
            "close_date": ["2025-12-01"],
        }
    )

    result = compute_delivery_load(
        df,
        current_date="2026-05-01",
    )

    assert "delivery_load" in result.columns
    assert bool(result.loc[0, "delivery_active"]) is True
    assert result.loc[0, "delivery_load"] > 0


def test_compute_delivery_load_sets_non_won_status_to_zero():
    df = pd.DataFrame(
        {
            "status": ["open"],
            "status_reason": ["Open"],
            "total_estimated_revenue": [500000],
            "project_duration_number_of_months": [12],
            "revenue_start_date": ["2026-01-01"],
            "close_date": ["2025-12-01"],
        }
    )

    result = compute_delivery_load(
        df,
        current_date="2026-05-01",
    )

    assert result.loc[0, "delivery_load"] == 0


def test_compute_current_load_by_owner_aggregates_owner_loads():
    df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B"],
            "opportunity_owner": ["Owner 1", "Owner 1"],
            "status": ["open", "closed"],
            "status_reason": ["Open", "Won"],
            "sales_stage": [
                "4-Proposal",
                "6-Negotiation&Signature",
            ],
            "probability": [80, 100],
            "total_estimated_revenue": [100000, 300000],
            "project_duration_number_of_months": [12, 12],
            "revenue_start_date": ["2026-01-01", "2026-01-01"],
            "close_date": ["2025-12-01", "2025-12-01"],
            "delivery_territory_center": [
                "Atlantic",
                "Atlantic",
            ],
        }
    )

    result = compute_current_load_by_owner(df)

    assert len(result) == 1
    assert list(result["opportunity_owner"]) == ["Owner 1"]
    assert result.loc[0, "current_load"] > 0
    assert result.loc[0, "opportunity_count"] == 2
    assert result.loc[0, "late_stage_deal_count"] == 2


def test_compute_historical_baseline_returns_owner_level_statistics():
    df = pd.DataFrame(
        {
            "opportunity_owner": [
                "Owner 1",
                "Owner 1",
                "Owner 1",
            ],
            "created_on": [
                "2025-01-01",
                "2025-05-01",
                "2025-09-01",
            ],
            "sales_load": [1.0, 2.0, 3.0],
            "delivery_load": [0.5, 0.5, 0.5],
        }
    )

    df["current_load"] = (
        df["sales_load"]
        + df["delivery_load"]
    )

    result = compute_historical_baseline(df)

    assert len(result) == 1
    assert result.loc[0, "historical_avg_load"] > 0
    assert result.loc[0, "historical_max_load"] > 0
    assert result.loc[0, "quarters_of_data"] == 3
    assert bool(result.loc[0, "baseline_reliability"]) is False


def test_compute_relative_load_divides_current_by_baseline():
    current_df = pd.DataFrame(
        {
            "opportunity_owner": ["Owner 1"],
            "current_load": [20],
        }
    )

    baseline_df = pd.DataFrame(
        {
            "opportunity_owner": ["Owner 1"],
            "historical_avg_load": [10],
        }
    )

    result = compute_relative_load(
        current_df,
        baseline_df,
    )

    assert result.loc[0, "relative_load"] == 2


def test_compute_capacity_score_caps_at_zero():
    df = pd.DataFrame(
        {
            "relative_load": [2.0],
        }
    )

    result = compute_capacity_score(df)

    assert result.loc[0, "capacity_score"] == 0


def test_assign_capacity_label_returns_available():
    df = pd.DataFrame(
        {
            "relative_load": [0.5],
        }
    )

    result = assign_capacity_label(df)

    assert result.loc[0, "capacity_label"] == "Available"


def test_assign_capacity_label_returns_at_capacity():
    df = pd.DataFrame(
        {
            "relative_load": [1.0],
        }
    )

    result = assign_capacity_label(df)

    assert result.loc[0, "capacity_label"] == "At Capacity"


def test_assign_capacity_label_returns_overextended():
    df = pd.DataFrame(
        {
            "relative_load": [1.5],
        }
    )

    result = assign_capacity_label(df)

    assert result.loc[0, "capacity_label"] == "Overextended"
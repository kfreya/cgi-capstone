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

import math

import pandas as pd

from src.capacity_engine import (
    assign_capacity_label,
    compute_capacity_score,
    compute_current_load_by_owner,
    compute_delivery_load,
    compute_historical_baseline,
    compute_quarterly_workload_by_owner,
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
            "authoritative_revenue": [100000],
            "project_duration_number_of_months": [12],
        }
    )

    result = compute_sales_load(df)

    assert "sales_load" in result.columns
    assert result.loc[0, "sales_load"] > 0


def test_compute_sales_load_uses_documented_log_formula():
    df = pd.DataFrame(
        {
            "status": ["open"],
            "status_reason": ["Open"],
            "sales_stage": ["4-Proposal"],
            "probability": [80],
            "authoritative_revenue": [100000],
            "project_duration_number_of_months": [12],
        }
    )

    result = compute_sales_load(df)

    expected = 1.3 * 0.8 * math.log1p(100000) * (
        math.log1p(12) / math.log1p(12)
    )
    assert abs(result.loc[0, "sales_load"] - expected) < 1e-12


def test_compute_sales_load_sets_won_status_to_zero():
    df = pd.DataFrame(
        {
            "status": ["closed"],
            "status_reason": ["Won"],
            "sales_stage": ["6-Negotiation&Signature"],
            "probability": [100],
            "total_estimated_revenue": [500000],
            "authoritative_revenue": [500000],
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
            "authoritative_revenue": [1200000],
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


def test_compute_delivery_load_uses_monthly_revenue_log_formula():
    df = pd.DataFrame(
        {
            "status": ["closed"],
            "status_reason": ["Won"],
            "authoritative_revenue": [1200000],
            "project_duration_number_of_months": [12],
            "revenue_start_date": ["2026-01-01"],
            "close_date": ["2025-12-01"],
        }
    )

    result = compute_delivery_load(
        df,
        current_date="2026-05-01",
    )

    assert result.loc[0, "delivery_load"] == math.log1p(100000)


def test_compute_delivery_load_sets_non_won_status_to_zero():
    df = pd.DataFrame(
        {
            "status": ["open"],
            "status_reason": ["Open"],
            "total_estimated_revenue": [500000],
            "authoritative_revenue": [500000],
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


def test_compute_sales_load_prefers_authoritative_revenue():
    df = pd.DataFrame(
        {
            "status": ["open"],
            "status_reason": ["Open"],
            "sales_stage": ["4-Proposal"],
            "probability": [100],
            "total_estimated_revenue": [1],
            "authoritative_revenue": [100000],
            "service_solution_estimated_revenue": [999999999],
            "project_duration_number_of_months": [12],
        }
    )

    result = compute_sales_load(df)

    fallback_df = df.drop(columns=["authoritative_revenue"])
    fallback_result = compute_sales_load(fallback_df)

    assert result.loc[0, "sales_load"] > fallback_result.loc[0, "sales_load"]


def test_compute_sales_load_falls_back_to_total_estimated_revenue():
    df = pd.DataFrame(
        {
            "status": ["open"],
            "status_reason": ["Open"],
            "sales_stage": ["4-Proposal"],
            "probability": [100],
            "total_estimated_revenue": [100000],
            "project_duration_number_of_months": [12],
        }
    )

    result = compute_sales_load(df)

    assert result.loc[0, "sales_load"] > 0


def test_compute_current_load_by_owner_uses_authoritative_revenue_for_weighted_pipeline():
    df = pd.DataFrame(
        {
            "opportunity_id": ["A"],
            "opportunity_owner": ["Owner 1"],
            "status": ["open"],
            "status_reason": ["Open"],
            "sales_stage": ["4-Proposal"],
            "probability": [50],
            "total_estimated_revenue": [100],
            "authoritative_revenue": [1000],
            "service_solution_estimated_revenue": [999999],
            "project_duration_number_of_months": [12],
            "revenue_start_date": ["2026-01-01"],
            "close_date": ["2025-12-01"],
            "delivery_territory_center": ["Atlantic"],
        }
    )

    result = compute_current_load_by_owner(df)

    assert result.loc[0, "weighted_pipeline_revenue"] == 500


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
            "authoritative_revenue": [100000, 300000],
            "project_duration_number_of_months": [12, 12],
            "revenue_start_date": ["2026-01-01", "2026-01-01"],
            "close_date": ["2025-12-01", "2025-12-01"],
            "delivery_territory_center": [
                "Atlantic",
                "Atlantic",
            ],
            "service_solution": [
                "Cloud Infrastructure",
                "Data Analytics",
            ],
        }
    )

    result = compute_current_load_by_owner(df)

    assert len(result) == 1
    assert list(result["opportunity_owner"]) == ["Owner 1"]
    assert result.loc[0, "current_load"] > 0
    assert result.loc[0, "opportunity_count"] == 2
    assert result.loc[0, "service_solution"] == "Cloud Infrastructure; Data Analytics"
    # Late stage counts open opportunities only (Won row is not open).
    assert result.loc[0, "late_stage_deal_count"] == 1


def test_compute_current_load_by_owner_orders_service_solution_profile_by_frequency():
    df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B", "C", "D"],
            "opportunity_owner": ["Owner 1", "Owner 1", "Owner 1", "Owner 1"],
            "status": ["open", "open", "open", "closed"],
            "status_reason": ["Open", "Open", "Open", "Lost"],
            "sales_stage": ["4-Proposal", "4-Proposal", "4-Proposal", "4-Proposal"],
            "probability": [50, 50, 50, 100],
            "authoritative_revenue": [100, 100, 100, 100],
            "project_duration_number_of_months": [12, 12, 12, 12],
            "revenue_start_date": ["2026-01-01", "2026-01-01", "2026-01-01", "2026-01-01"],
            "close_date": ["2025-12-01", "2025-12-01", "2025-12-01", "2025-12-01"],
            "delivery_territory_center": ["Atlantic", "Atlantic", "Atlantic", "Atlantic"],
            "service_solution": [
                "Data Analytics",
                "Cloud Infrastructure",
                "Data Analytics",
                "Lost Only Service",
            ],
        }
    )

    result = compute_current_load_by_owner(df)

    assert result.loc[0, "service_solution"] == "Data Analytics; Cloud Infrastructure"


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
    assert result.loc[0, "baseline_reliability"] == "Low"


def test_compute_sales_load_excludes_lost_and_duplicate_outcomes():
    df = pd.DataFrame(
        {
            "status": ["Closed", "Closed", "Open"],
            "status_reason": ["Lost - Price", "Duplicated", "Open"],
            "sales_stage": ["4-Proposal", "4-Proposal", "4-Proposal"],
            "probability": [100, 100, 100],
            "authoritative_revenue": [100000, 100000, 100000],
            "project_duration_number_of_months": [12, 12, 12],
        }
    )

    result = compute_sales_load(df)

    assert result.loc[0, "sales_load"] == 0
    assert result.loc[1, "sales_load"] == 0
    assert result.loc[2, "sales_load"] > 0


def test_compute_delivery_load_counts_only_won_active_deliveries():
    df = pd.DataFrame(
        {
            "status": ["Won", "Closed", "Open"],
            "status_reason": [pd.NA, "Lost - Price", "Open"],
            "authoritative_revenue": [1200000, 1200000, 1200000],
            "project_duration_number_of_months": [12, 12, 12],
            "revenue_start_date": ["2026-01-01", "2026-01-01", "2026-01-01"],
            "close_date": ["2025-12-01", "2025-12-01", "2025-12-01"],
        }
    )

    result = compute_delivery_load(df, current_date="2026-05-01")

    assert list(result["delivery_active"]) == [True, False, False]
    assert result.loc[0, "delivery_load"] > 0
    assert result.loc[1, "delivery_load"] == 0
    assert result.loc[2, "delivery_load"] == 0


def test_quarterly_workload_is_capped_at_as_of_quarter():
    df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B"],
            "opportunity_owner": ["Owner 1", "Owner 1"],
            "status": ["Open", "Won"],
            "status_reason": ["Open", "Won"],
            "sales_stage": ["4-Proposal", "6-Negotiation&Signature"],
            "probability": [80, 100],
            "authoritative_revenue": [100000, 1200000],
            "project_duration_number_of_months": [120, 120],
            "revenue_start_date": ["2032-01-01", "2026-01-01"],
            "close_date": [pd.NA, "2025-12-01"],
            "created_on": ["2025-01-01", "2025-12-01"],
        }
    )

    result = compute_quarterly_workload_by_owner(
        df,
        as_of_date="2026-05-17",
    )

    assert result["quarter"].max() == pd.Period("2026Q2", freq="Q")
    assert "Q4 2038" not in set(result["quarter_label"])


def test_historical_baseline_is_capped_at_as_of_quarter():
    df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B"],
            "opportunity_owner": ["Owner 1", "Owner 1"],
            "status": ["Open", "Won"],
            "status_reason": ["Open", "Won"],
            "sales_stage": ["4-Proposal", "6-Negotiation&Signature"],
            "probability": [80, 100],
            "authoritative_revenue": [100000, 1200000],
            "project_duration_number_of_months": [120, 120],
            "revenue_start_date": ["2032-01-01", "2026-01-01"],
            "close_date": [pd.NA, "2025-12-01"],
            "created_on": ["2025-01-01", "2025-12-01"],
        }
    )

    result = compute_historical_baseline(
        df,
        as_of_date="2026-05-17",
    )

    assert result.loc[0, "quarters_of_data"] == 6
    assert result.loc[0, "baseline_reliability"] == "Medium"


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

    assert result.loc[0, "relative_load"] == 2.0


def test_relative_load_can_compare_filtered_current_to_stable_baseline():
    filtered_current_df = pd.DataFrame(
        {
            "opportunity_owner": ["Owner 1"],
            "current_load": [20],
        }
    )

    selected_population_baseline_df = pd.DataFrame(
        {
            "opportunity_owner": ["Owner 1"],
            "historical_avg_load": [10],
        }
    )

    filtered_denominator_df = pd.DataFrame(
        {
            "opportunity_owner": ["Owner 1"],
            "historical_avg_load": [20],
        }
    )

    result = compute_relative_load(
        filtered_current_df,
        selected_population_baseline_df,
    )
    filtered_denominator_result = compute_relative_load(
        filtered_current_df,
        filtered_denominator_df,
    )

    assert result.loc[0, "relative_load"] == 2.0
    assert filtered_denominator_result.loc[0, "relative_load"] == 1.0


def test_compute_capacity_score_uses_hard_capped_scoring():
    df = pd.DataFrame(
        {
            "relative_load": [0.5, 1.0, 2.0],
        }
    )

    result = compute_capacity_score(df)

    assert result.loc[0, "capacity_score"] == 0.5
    assert result.loc[1, "capacity_score"] == 0
    assert result.loc[2, "capacity_score"] == 0


def test_assign_capacity_label_returns_available():
    df = pd.DataFrame(
        {
            "relative_load": [0.5],
            "capacity_score": [0.7],
        }
    )

    result = assign_capacity_label(df)

    assert result.loc[0, "capacity_label"] == "Available"


def test_assign_capacity_label_returns_near_historical_norm():
    df = pd.DataFrame(
        {
            "relative_load": [1.0],
            "capacity_score": [0.25],
        }
    )

    result = assign_capacity_label(df)

    assert result.loc[0, "capacity_label"] == "Near Historical Norm"


def test_assign_capacity_label_returns_high_load():
    df = pd.DataFrame(
        {
            "relative_load": [1.5],
            "capacity_score": [0.0],
        }
    )

    result = assign_capacity_label(df)

    assert result.loc[0, "capacity_label"] == "High Load"


def test_assign_capacity_label_nan_relative_load_uses_no_baseline():
    df = pd.DataFrame(
        {
            "relative_load": [float("nan")],
            "capacity_score": [float("nan")],
        }
    )

    result = assign_capacity_label(df)

    assert result.loc[0, "capacity_label"] == "No baseline"


def test_assign_capacity_label_returns_overextended_at_double_norm():
    df = pd.DataFrame(
        {
            "relative_load": [2.0],
            "capacity_score": [0.0],
        }
    )

    result = assign_capacity_label(df)

    assert result.loc[0, "capacity_label"] == "Overextended"


def test_assign_capacity_label_applies_relative_load_boundaries():
    df = pd.DataFrame(
        {
            "relative_load": [0.85, 0.8501, 1.25, 1.9999, 2.0],
            "capacity_score": [0.0, 0.0, 0.0, 0.0, 0.0],
        }
    )

    result = assign_capacity_label(df)

    assert list(result["capacity_label"]) == [
        "Available",
        "Near Historical Norm",
        "High Load",
        "High Load",
        "Overextended",
    ]

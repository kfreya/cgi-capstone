"""
Week 1 

Capacity scoring engine for CGI Capacity Analyzer.

This module takes in the cleaned `opportunity_df` and defines the first-pass workload scoring workflow:
- sales pipeline load
- inferred delivery load
- owner-level aggregation
- historical baseline
- relative load
- capacity score
- capacity labels

"""

from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_STAGE_WEIGHTS = {
    "0-Lead/Suspect": 0.4,
    "1-Identification": 0.6,
    "2-Qualification": 0.8,
    "3-Bid Planning": 1.0,
    "4-Proposal": 1.3,
    "5-Client Decision": 1.5,
    "6-Negotiation&Signature": 1.7,
}


DEFAULT_LABEL_THRESHOLDS = {
    "available": 0.8,
    "at_capacity": 1.2,
}


def compute_sales_load(
    df: pd.DataFrame,
    stage_weights: dict | None = None,
) -> pd.DataFrame:
    df = df.copy()

    if stage_weights is None:
        stage_weights = DEFAULT_STAGE_WEIGHTS

    probability = (
        pd.to_numeric(df["probability"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
    )

    revenue = (
        pd.to_numeric(df["total_estimated_revenue"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
    )

    duration = (
        pd.to_numeric(
            df["project_duration_number_of_months"],
            errors="coerce",
        )
        .fillna(12)
        .clip(lower=1)
    )

    duration_weight = np.log1p(duration) / np.log1p(12)

    stage_weight = (
        df["sales_stage"]
        .map(stage_weights)
        .fillna(0)
    )

    sales_load = (
        stage_weight
        * (probability / 100)
        * np.log1p(revenue)
        * duration_weight
    )

    sales_load = np.where(
        df["status"].astype(str).str.lower() == "won",
        0,
        sales_load,
    )

    df["sales_load"] = sales_load

    return df


def compute_delivery_load(
    df: pd.DataFrame,
    current_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    df = df.copy()

    if current_date is None:
        current_date = pd.Timestamp.today().normalize()

    current_date = pd.Timestamp(current_date)

    revenue = (
        pd.to_numeric(df["total_estimated_revenue"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
    )

    duration = (
        pd.to_numeric(
            df["project_duration_number_of_months"],
            errors="coerce",
        )
        .fillna(12)
        .clip(lower=1)
    )

    revenue_start = pd.to_datetime(
        df["revenue_start_date"],
        errors="coerce",
    )

    close_date = pd.to_datetime(
        df["close_date"],
        errors="coerce",
    )

    effective_start = revenue_start.fillna(close_date)

    effective_end = (
        effective_start
        + pd.to_timedelta(duration * 30, unit="D")
    )

    delivery_active = (
        (effective_start.notna())
        & (effective_start <= current_date)
        & (effective_end >= current_date)
    )

    monthly_revenue = revenue / duration

    delivery_load = (
        delivery_active.astype(int)
        * np.log1p(monthly_revenue)
    )

    delivery_load = np.where(
        df["status"].astype(str).str.lower() == "won",
        delivery_load,
        0,
    )

    df["delivery_load"] = delivery_load
    df["delivery_active"] = delivery_active

    return df


def compute_current_load_by_owner(
    df: pd.DataFrame,
) -> pd.DataFrame:
    working_df = df.copy()

    if "sales_load" not in working_df.columns:
        working_df = compute_sales_load(working_df)

    if "delivery_load" not in working_df.columns:
        working_df = compute_delivery_load(working_df)

    working_df["current_load"] = (
        working_df["sales_load"]
        + working_df["delivery_load"]
    )

    grouped = (
        working_df
        .groupby("opportunity_owner", dropna=False)
        .agg(
            current_load=("current_load", "sum"),
            sales_load=("sales_load", "sum"),
            delivery_load=("delivery_load", "sum"),
            open_deal_count=(
                "status",
                lambda x: (
                    x.astype(str)
                    .str.lower()
                    .eq("open")
                    .sum()
                ),
            ),
            opportunity_count=("opportunity_id", "count"),
        )
        .reset_index()
    )

    return grouped


def compute_historical_baseline(
    df: pd.DataFrame,
) -> pd.DataFrame:
    working_df = df.copy()

    if "current_load" not in working_df.columns:
        working_df["current_load"] = (
            working_df.get("sales_load", 0)
            + working_df.get("delivery_load", 0)
        )

    created_on = pd.to_datetime(
        working_df["created_on"],
        errors="coerce",
    )

    working_df["quarter"] = created_on.dt.to_period("Q")

    grouped = (
        working_df
        .groupby(
            ["opportunity_owner", "quarter"],
            dropna=False,
        )
        .agg(
            quarterly_load=("current_load", "sum"),
        )
        .reset_index()
    )

    baseline = (
        grouped
        .groupby("opportunity_owner", dropna=False)
        .agg(
            historical_mean_load=("quarterly_load", "mean"),
            historical_std_load=("quarterly_load", "std"),
            historical_max_load=("quarterly_load", "max"),
            quarters_seen=("quarter", "nunique"),
        )
        .reset_index()
    )

    baseline["historical_std_load"] = (
        baseline["historical_std_load"]
        .fillna(0)
    )

    baseline["baseline_reliability_flag"] = (
        baseline["quarters_seen"] >= 4
    )

    return baseline


def compute_relative_load(
    current_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
) -> pd.DataFrame:
    merged = current_df.merge(
        baseline_df,
        on="opportunity_owner",
        how="left",
    )

    baseline_mean = (
        pd.to_numeric(
            merged["historical_mean_load"],
            errors="coerce",
        )
        .replace(0, np.nan)
    )

    merged["relative_load"] = (
        merged["current_load"]
        / baseline_mean
    )

    return merged


def compute_capacity_score(
    df: pd.DataFrame,
) -> pd.DataFrame:
    working_df = df.copy()

    working_df["capacity_score"] = (
        1 / working_df["relative_load"]
    )

    working_df["capacity_score"] = (
        working_df["capacity_score"]
        .replace([np.inf, -np.inf], np.nan)
    )

    return working_df


def assign_capacity_label(
    df: pd.DataFrame,
    thresholds: dict | None = None,
) -> pd.DataFrame:
    working_df = df.copy()

    if thresholds is None:
        thresholds = DEFAULT_LABEL_THRESHOLDS

    conditions = [
        working_df["relative_load"] < thresholds["available"],
        (
            working_df["relative_load"]
            < thresholds["at_capacity"]
        ),
    ]

    labels = [
        "Available",
        "At Capacity",
    ]

    working_df["capacity_label"] = np.select(
        conditions,
        labels,
        default="Overextended",
    )

    return working_df

if __name__ == "__main__":
    opportunity_df = pd.read_csv(
        "data/processed/opportunity_df.csv"
    )

    opportunity_df = compute_sales_load(
        opportunity_df
    )

    opportunity_df = compute_delivery_load(
        opportunity_df
    )

    current_df = compute_current_load_by_owner(
        opportunity_df
    )

    baseline_df = compute_historical_baseline(
        opportunity_df
    )

    director_df = compute_relative_load(
        current_df,
        baseline_df,
    )

    director_df = compute_capacity_score(
        director_df
    )

    director_df = assign_capacity_label(
        director_df
    )

    director_df.to_csv(
        "data/processed/director_df.csv",
        index=False,
    )

    print("director_df generated successfully")
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


# Band edges on capacity_score (see docs/architecture.md).
DEFAULT_LABEL_THRESHOLDS = {
    "score_available_min": 0.35,
    "score_at_capacity_min": 0.15,
}


def _get_revenue_series(df: pd.DataFrame) -> pd.Series:
    """Return the revenue series used for capacity scoring.

    Prefer Sprint 2 cleaned `authoritative_revenue` when available.
    Fall back to Week 1 `total_estimated_revenue` for backward compatibility.
    """
    if "authoritative_revenue" in df.columns:
        return pd.to_numeric(
            df["authoritative_revenue"],
            errors="coerce",
        )

    if "total_estimated_revenue" in df.columns:
        return pd.to_numeric(
            df["total_estimated_revenue"],
            errors="coerce",
        )

    return pd.Series(pd.NA, index=df.index, dtype="Float64")


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

    #revenue_source = (
    #    df["authoritative_revenue"]
    #    if "authoritative_revenue" in df.columns
    #    else df["total_estimated_revenue"]
    #)

    revenue = (
        _get_revenue_series(df)
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
        df["status_reason"].astype(str).str.lower() == "won",
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

    #revenue_source = (
    #    df["authoritative_revenue"]
    #    if "authoritative_revenue" in df.columns
    #    else df["total_estimated_revenue"]
    #)

    revenue = (
        _get_revenue_series(df)
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
        df["status_reason"].astype(str).str.lower() == "won",
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

    working_df["is_open"] = (
        working_df["status_reason"]
        .astype(str)
        .str.lower()
        .eq("open")
    )

    working_df["is_late_stage"] = (
        working_df["sales_stage"]
        .isin([
            "4-Proposal",
            "5-Client Decision",
            "6-Negotiation&Signature",
        ])
        & working_df["is_open"]
    )

    # Explicit scalars (avoid accidental tuple from parenthesis/comma layout).
    _rev = _get_revenue_series(working_df).fillna(0)
    _prob_w = (
        pd.to_numeric(
            working_df["probability"],
            errors="coerce",
        ).fillna(0)
        / 100.0
    )
    working_df["weighted_pipeline_revenue"] = np.where(
        working_df["is_open"],
        _rev * _prob_w,
        0.0,
    )

    working_df["inferred_delivery_commitments"] = (
        working_df["delivery_active"]
        .astype(int)
    )

    grouped = (
        working_df
        .groupby("opportunity_owner", dropna=False)
        .agg(
            current_load=("current_load", "sum"),
            sales_load=("sales_load", "sum"),
            delivery_load=("delivery_load", "sum"),

            open_deal_count=(
                "status_reason",
                lambda x: (
                    x.astype(str)
                    .str.lower()
                    .eq("open")
                    .sum()
                ),
            ),

            opportunity_count=("opportunity_id", "count"),
            territory=(
                "delivery_territory_center",
                "first",
            ),
            late_stage_deal_count=(
                "is_late_stage",
                "sum",
            ),
            weighted_pipeline_revenue=(
                "weighted_pipeline_revenue",
                "sum",
            ),
            inferred_delivery_commitments=(
                "inferred_delivery_commitments",
                "sum",
            ),
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
            historical_avg_load=("quarterly_load", "mean"),
            historical_std_load=("quarterly_load", "std"),
            historical_max_load=("quarterly_load", "max"),
            quarters_of_data=("quarter", "nunique"),
        )
        .reset_index()
    )

    baseline["historical_std_load"] = (
        baseline["historical_std_load"]
        .fillna(0)
    )

    baseline["baseline_reliability"] = (
        baseline["quarters_of_data"] >= 4
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
            merged["historical_avg_load"],
            errors="coerce",
        )
        .replace(0, np.nan)
    )

    # Architecture: relative_load_owner = current_load / historical_avg_load
    merged["relative_load"] = (
        merged["current_load"]
        / baseline_mean
    )

    return merged


def compute_capacity_score(
    df: pd.DataFrame,
) -> pd.DataFrame:
    working_df = df.copy()

    capped_relative_load = (
        working_df["relative_load"]
        .clip(upper=1)
    )

    working_df["capacity_score"] = (
        1 - capped_relative_load
    )

    working_df["capacity_score"] = (
        working_df["capacity_score"]
        .clip(lower=0)
    )

    # Preserve NaN scores for owners with unusable baseline
    working_df.loc[
        working_df["relative_load"].isna(),
        "capacity_score",
    ] = np.nan

    return working_df


def assign_capacity_label(
    df: pd.DataFrame,
    thresholds: dict | None = None,
) -> pd.DataFrame:
    working_df = df.copy()

    if thresholds is None:
        thresholds = DEFAULT_LABEL_THRESHOLDS

    lo = thresholds["score_at_capacity_min"]
    hi = thresholds["score_available_min"]
    score = working_df["capacity_score"]

    # Exactly three labels (architecture / dashboard contract).
    labeled = np.select(
        [
            score >= hi,
            (score >= lo) & (score < hi),
        ],
        [
            "Available",
            "At Capacity",
        ],
        default="Overextended",
    )
    working_df["capacity_label"] = labeled
    # Missing score: no usable baseline — neutral band for UI (not a 4th label).
    working_df.loc[score.isna(), "capacity_label"] = "At Capacity"

    return working_df


DIRECTOR_CAPACITY_DASHBOARD_COLUMNS = [
    "opportunity_owner",
    "territory",
    "historical_avg_load",
    "relative_load",
    "current_load",
    "capacity_score",
    "capacity_label",
    "open_deal_count",
    "late_stage_deal_count",
    "weighted_pipeline_revenue",
    "inferred_delivery_commitments",
    "quarters_of_data",
    "baseline_reliability",
]


def build_director_capacity_df(
    opportunity_df: pd.DataFrame,
) -> pd.DataFrame:
    """End-to-end owner-level table matching dashboard contract."""
    df = opportunity_df.copy()
    df = compute_sales_load(df)
    df = compute_delivery_load(df)
    current_df = compute_current_load_by_owner(df)
    baseline_df = compute_historical_baseline(df)
    out = compute_relative_load(current_df, baseline_df)
    out = compute_capacity_score(out)
    out = assign_capacity_label(out)
    missing = [
        c for c in DIRECTOR_CAPACITY_DASHBOARD_COLUMNS
        if c not in out.columns
    ]
    if missing:
        raise ValueError(
            "build_director_capacity_df: missing columns: "
            + ", ".join(missing)
        )
    return out[DIRECTOR_CAPACITY_DASHBOARD_COLUMNS].copy()


if __name__ == "__main__":
    from pathlib import Path

    csv_path = Path("data/processed/cleaned_opportunity_df.csv")

    if not csv_path.exists():
        raise FileNotFoundError(
            "Expected input file not found: "
            f"{csv_path}. "
            "Generate cleaned_opportunity_df.csv before running "
            "capacity_engine.py directly."
        )

    opportunity_df = pd.read_csv(csv_path)

    director_capacity_df = build_director_capacity_df(opportunity_df)

    out_path = Path("data/processed/director_capacity_df.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    director_capacity_df.to_csv(out_path, index=False)

    example_path = Path(
        "data/processed/director_capacity_df_example.csv"
    )
    director_capacity_df.head(12).to_csv(
        example_path,
        index=False,
    )

    print(f"Wrote {out_path} ({len(director_capacity_df)} owners)")
    print(f"Wrote {example_path} (sample rows)")
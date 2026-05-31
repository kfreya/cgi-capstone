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

try:
    from src.data_validator import classify_opportunity_outcome
except ModuleNotFoundError:
    from data_validator import classify_opportunity_outcome


DEFAULT_STAGE_WEIGHTS = {
    "0-Lead/Suspect": 0.4,
    "1-Identification": 0.6,
    "2-Qualification": 0.8,
    "3-Bid Planning": 1.0,
    "4-Proposal": 1.3,
    "5-Client Decision": 1.5,
    "6-Negotiation&Signature": 1.7,
}


# Temporary label calibration on relative_load (see docs/architecture.md).
# These bands are based on the current director-level distribution and a
# business-readable interpretation of workload vs historical norm. They should
# remain configurable and subject to CGI stakeholder review.
DEFAULT_LABEL_THRESHOLDS = {
    "available_max_relative_load": 0.85,
    "high_load_min_relative_load": 1.25,
    "overextended_min_relative_load": 2.0,
}


def _get_revenue_series(df: pd.DataFrame) -> pd.Series:
    """Return the revenue series used for capacity scoring.

    Prefer Sprint 2 cleaned `authoritative_revenue` when available.
    Fall back to Week 1 `total_estimated_revenue` for backward compatibility.
    Do not use `service_solution_estimated_revenue`, which is a service-line
    breakdown rather than opportunity-level scoring revenue.
    """
    if "authoritative_revenue" in df.columns:
        return pd.to_numeric(
            df["authoritative_revenue"],
            errors="coerce",
        )

    primary = (
        pd.to_numeric(df["total_estimated_revenue"], errors="coerce")
        if "total_estimated_revenue" in df.columns
        else pd.Series(pd.NA, index=df.index, dtype="Float64")
    )
    fallback = (
        pd.to_numeric(df["opportunity_estimated_revenue_base_cad"], errors="coerce")
        if "opportunity_estimated_revenue_base_cad" in df.columns
        else pd.Series(pd.NA, index=df.index, dtype="Float64")
    )

    return primary.combine_first(fallback)


def _deduplicate_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    """Avoid double-counting duplicate join-key rows when opportunity_id exists."""
    if "opportunity_id" not in df.columns:
        return df.copy()
    return df.drop_duplicates(subset=["opportunity_id"], keep="first").copy()


def _outcome_series(df: pd.DataFrame) -> pd.Series:
    """Return the shared won/lost/open/duplicate taxonomy for scoring."""
    return classify_opportunity_outcome(df)


def _duration_series(df: pd.DataFrame) -> pd.Series:
    return (
        pd.to_numeric(df["project_duration_number_of_months"], errors="coerce")
        .fillna(12)
        .clip(lower=1)
    )


def _sales_load_values(
    df: pd.DataFrame,
    stage_weights: dict | None = None,
) -> pd.Series:
    if stage_weights is None:
        stage_weights = DEFAULT_STAGE_WEIGHTS

    probability = (
        pd.to_numeric(df["probability"], errors="coerce")
        .fillna(0)
        .clip(lower=0, upper=100)
    )
    revenue = _get_revenue_series(df).fillna(0).clip(lower=0)
    duration = _duration_series(df)
    duration_weight = np.log1p(duration) / np.log1p(12)
    stage_weight = df["sales_stage"].map(stage_weights).fillna(0)
    is_open = _outcome_series(df).eq("open")

    return (
        stage_weight
        * (probability / 100)
        * np.log1p(revenue)
        * duration_weight
    ).where(is_open, 0.0)


def _delivery_window(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    duration = _duration_series(df)
    revenue_start = pd.to_datetime(df["revenue_start_date"], errors="coerce")
    close_date = pd.to_datetime(df["close_date"], errors="coerce")
    effective_start = revenue_start.fillna(close_date)
    effective_end = effective_start + pd.to_timedelta(duration * 30, unit="D")
    return effective_start, effective_end, duration


def _as_of_timestamp(as_of_date: str | pd.Timestamp | None = None) -> pd.Timestamp:
    if as_of_date is None:
        return pd.Timestamp.today().normalize()
    return pd.Timestamp(as_of_date).normalize()


def _analysis_quarters(
    date_values: pd.Series,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.PeriodIndex:
    """Return usable quarters, capped at the current/as-of quarter."""
    date_values = pd.to_datetime(date_values, errors="coerce").dropna()
    if date_values.empty:
        return pd.PeriodIndex([], freq="Q")

    start = date_values.min().to_period("Q")
    data_end = date_values.max().to_period("Q")
    as_of = _as_of_timestamp(as_of_date).to_period("Q")
    end = min(data_end, as_of)

    if start > end:
        return pd.PeriodIndex([], freq="Q")

    return pd.period_range(start=start, end=end, freq="Q")


def compute_sales_load(
    df: pd.DataFrame,
    stage_weights: dict | None = None,
) -> pd.DataFrame:
    df = df.copy()
    df["sales_load"] = _sales_load_values(df, stage_weights=stage_weights)
    return df


def compute_delivery_load(
    df: pd.DataFrame,
    current_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    df = df.copy()

    if current_date is None:
        current_date = pd.Timestamp.today().normalize()

    current_date = pd.Timestamp(current_date)
    revenue = _get_revenue_series(df).fillna(0).clip(lower=0)
    effective_start, effective_end, duration = _delivery_window(df)
    is_won = _outcome_series(df).eq("won")

    delivery_active = (
        is_won
        & (effective_start.notna())
        & (effective_start <= current_date)
        & (effective_end >= current_date)
    )

    monthly_revenue = revenue / duration

    delivery_load = (
        delivery_active.astype(int)
        * np.log1p(monthly_revenue)
    )

    df["delivery_load"] = delivery_load
    df["delivery_active"] = delivery_active

    return df


def compute_current_load_by_owner(
    df: pd.DataFrame,
) -> pd.DataFrame:
    working_df = _deduplicate_opportunities(df)

    if "sales_load" not in working_df.columns:
        working_df = compute_sales_load(working_df)

    if "delivery_load" not in working_df.columns:
        working_df = compute_delivery_load(working_df)

    working_df["current_load"] = (
        working_df["sales_load"]
        + working_df["delivery_load"]
    )

    working_df["_outcome"] = _outcome_series(working_df)
    working_df["is_open"] = working_df["_outcome"].eq("open")

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
                "is_open",
                "sum",
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

    service_profile = _service_solution_profile_by_owner(working_df)
    if not service_profile.empty:
        grouped = grouped.merge(
            service_profile,
            on="opportunity_owner",
            how="left",
        )
    elif "service_solution" not in grouped.columns:
        grouped["service_solution"] = pd.NA

    return grouped


def _service_solution_profile_by_owner(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate opportunity-level service solutions into an owner profile."""

    if "service_solution" not in df.columns:
        return pd.DataFrame(columns=["opportunity_owner", "service_solution"])

    work = df.copy()
    if {"status", "status_reason"}.issubset(work.columns):
        work["_outcome"] = _outcome_series(work)
        work = work[work["_outcome"].isin(["open", "won"])]

    rows = []
    for owner, owner_df in work.groupby("opportunity_owner", dropna=False):
        values = (
            owner_df["service_solution"]
            .dropna()
            .astype(str)
            .map(str.strip)
        )
        values = values[values != ""]
        if values.empty:
            profile = pd.NA
        else:
            counts = values.value_counts()
            ordered = sorted(
                counts.index,
                key=lambda value: (-int(counts[value]), value.lower()),
            )
            profile = "; ".join(ordered[:8])
        rows.append(
            {
                "opportunity_owner": owner,
                "service_solution": profile,
            }
        )

    return pd.DataFrame(rows)


def compute_historical_baseline(
    df: pd.DataFrame,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    working_df = _deduplicate_opportunities(df)
    if {"status", "status_reason"}.difference(working_df.columns):
        if "current_load" not in working_df.columns:
            working_df["current_load"] = (
                working_df.get("sales_load", 0)
                + working_df.get("delivery_load", 0)
            )
        created_on = pd.to_datetime(working_df["created_on"], errors="coerce")
        working_df["quarter"] = created_on.dt.to_period("Q")
        grouped = (
            working_df.groupby(["opportunity_owner", "quarter"], dropna=False)
            .agg(quarterly_load=("current_load", "sum"))
            .reset_index()
        )
        baseline = (
            grouped.groupby("opportunity_owner", dropna=False)
            .agg(
                historical_avg_load=("quarterly_load", "mean"),
                historical_std_load=("quarterly_load", "std"),
                historical_max_load=("quarterly_load", "max"),
                quarters_of_data=("quarter", "nunique"),
            )
            .reset_index()
        )
        baseline["historical_std_load"] = baseline["historical_std_load"].fillna(0)
        baseline["baseline_reliability"] = baseline["quarters_of_data"].apply(
            _baseline_reliability_label
        )
        return baseline

    owners = pd.DataFrame(
        {"opportunity_owner": working_df["opportunity_owner"].drop_duplicates()}
    )

    working_df["_outcome"] = _outcome_series(working_df)
    working_df["_sales_base_load"] = _sales_load_values(working_df)

    revenue = _get_revenue_series(working_df).fillna(0).clip(lower=0)
    effective_start, effective_end, duration = _delivery_window(working_df)
    working_df["_delivery_base_load"] = np.log1p(revenue / duration).where(
        working_df["_outcome"].eq("won"),
        0.0,
    )
    working_df["_created_on"] = pd.to_datetime(
        working_df["created_on"],
        errors="coerce",
    )
    working_df["_close_date"] = pd.to_datetime(
        working_df["close_date"],
        errors="coerce",
    )
    working_df["_effective_start"] = effective_start
    working_df["_effective_end"] = effective_end

    date_values = pd.concat(
        [
            working_df["_created_on"],
            working_df["_close_date"],
            working_df["_effective_start"],
            working_df["_effective_end"],
        ],
        ignore_index=True,
    ).dropna()
    if date_values.empty:
        owners["historical_avg_load"] = np.nan
        owners["historical_std_load"] = 0.0
        owners["historical_max_load"] = np.nan
        owners["quarters_of_data"] = 0
        owners["baseline_reliability"] = "No baseline"
        return owners

    quarters = _analysis_quarters(date_values, as_of_date=as_of_date)
    if len(quarters) == 0:
        owners["historical_avg_load"] = np.nan
        owners["historical_std_load"] = 0.0
        owners["historical_max_load"] = np.nan
        owners["quarters_of_data"] = 0
        owners["baseline_reliability"] = "No baseline"
        return owners

    quarterly_frames = []
    for quarter in quarters:
        quarter_start = quarter.start_time.normalize()
        quarter_end = quarter.end_time.normalize()

        sales_active = (
            working_df["_outcome"].eq("open")
            & working_df["_created_on"].notna()
            & (working_df["_created_on"] <= quarter_end)
            & (
                working_df["_close_date"].isna()
                | (working_df["_close_date"] >= quarter_start)
            )
        )
        delivery_active = (
            working_df["_outcome"].eq("won")
            & working_df["_effective_start"].notna()
            & (working_df["_effective_start"] <= quarter_end)
            & (working_df["_effective_end"] >= quarter_start)
        )

        quarter_load = (
            working_df["_sales_base_load"].where(sales_active, 0.0)
            + working_df["_delivery_base_load"].where(delivery_active, 0.0)
        )
        active = quarter_load > 0
        if not active.any():
            continue

        quarterly_frames.append(
            pd.DataFrame(
                {
                    "opportunity_owner": working_df.loc[active, "opportunity_owner"],
                    "quarter": quarter,
                    "quarterly_load": quarter_load.loc[active],
                }
            )
        )

    if not quarterly_frames:
        grouped = pd.DataFrame(
            columns=["opportunity_owner", "quarter", "quarterly_load"]
        )
    else:
        grouped = (
            pd.concat(quarterly_frames, ignore_index=True)
            .groupby(["opportunity_owner", "quarter"], dropna=False)
            .agg(quarterly_load=("quarterly_load", "sum"))
            .reset_index()
        )

    baseline = (
        grouped.groupby("opportunity_owner", dropna=False)
        .agg(
            historical_avg_load=("quarterly_load", "mean"),
            historical_std_load=("quarterly_load", "std"),
            historical_max_load=("quarterly_load", "max"),
            quarters_of_data=("quarter", "nunique"),
        )
        .reset_index()
    )

    baseline = owners.merge(baseline, on="opportunity_owner", how="left")
    baseline["historical_std_load"] = baseline["historical_std_load"].fillna(0)
    baseline["quarters_of_data"] = baseline["quarters_of_data"].fillna(0).astype(int)
    baseline["baseline_reliability"] = baseline["quarters_of_data"].apply(
        _baseline_reliability_label
    )

    return baseline


def compute_quarterly_workload_by_owner(
    df: pd.DataFrame,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Return active-quarter workload rows for dashboard trend charts."""

    working_df = _deduplicate_opportunities(df)
    working_df["_outcome"] = _outcome_series(working_df)
    working_df["_sales_base_load"] = _sales_load_values(working_df)

    revenue = _get_revenue_series(working_df).fillna(0).clip(lower=0)
    effective_start, effective_end, duration = _delivery_window(working_df)
    working_df["_delivery_base_load"] = np.log1p(revenue / duration).where(
        working_df["_outcome"].eq("won"),
        0.0,
    )
    working_df["_created_on"] = pd.to_datetime(
        working_df["created_on"],
        errors="coerce",
    )
    working_df["_close_date"] = pd.to_datetime(
        working_df["close_date"],
        errors="coerce",
    )
    working_df["_effective_start"] = effective_start
    working_df["_effective_end"] = effective_end

    date_values = pd.concat(
        [
            working_df["_created_on"],
            working_df["_close_date"],
            working_df["_effective_start"],
            working_df["_effective_end"],
        ],
        ignore_index=True,
    ).dropna()
    if date_values.empty:
        return pd.DataFrame(
            columns=[
                "opportunity_owner",
                "quarter",
                "quarter_sort",
                "quarter_label",
                "current_load",
            ]
        )

    quarters = _analysis_quarters(date_values, as_of_date=as_of_date)
    if len(quarters) == 0:
        return pd.DataFrame(
            columns=[
                "opportunity_owner",
                "quarter",
                "quarter_sort",
                "quarter_label",
                "current_load",
            ]
        )

    quarterly_frames = []
    for quarter in quarters:
        quarter_start = quarter.start_time.normalize()
        quarter_end = quarter.end_time.normalize()
        sales_active = (
            working_df["_outcome"].eq("open")
            & working_df["_created_on"].notna()
            & (working_df["_created_on"] <= quarter_end)
            & (
                working_df["_close_date"].isna()
                | (working_df["_close_date"] >= quarter_start)
            )
        )
        delivery_active = (
            working_df["_outcome"].eq("won")
            & working_df["_effective_start"].notna()
            & (working_df["_effective_start"] <= quarter_end)
            & (working_df["_effective_end"] >= quarter_start)
        )
        quarter_load = (
            working_df["_sales_base_load"].where(sales_active, 0.0)
            + working_df["_delivery_base_load"].where(delivery_active, 0.0)
        )
        active = quarter_load > 0
        if not active.any():
            continue
        quarterly_frames.append(
            pd.DataFrame(
                {
                    "opportunity_owner": working_df.loc[active, "opportunity_owner"],
                    "quarter": quarter,
                    "current_load": quarter_load.loc[active],
                }
            )
        )

    if not quarterly_frames:
        return pd.DataFrame(
            columns=[
                "opportunity_owner",
                "quarter",
                "quarter_sort",
                "quarter_label",
                "current_load",
            ]
        )

    trend = (
        pd.concat(quarterly_frames, ignore_index=True)
        .groupby(["opportunity_owner", "quarter"], dropna=False)
        .agg(current_load=("current_load", "sum"))
        .reset_index()
    )
    trend["quarter_sort"] = trend["quarter"].apply(lambda quarter: quarter.ordinal)
    trend["quarter_label"] = trend["quarter"].apply(
        lambda quarter: f"Q{quarter.quarter} {quarter.year}"
    )
    return trend[
        [
            "opportunity_owner",
            "quarter",
            "quarter_sort",
            "quarter_label",
            "current_load",
        ]
    ]


def _baseline_reliability_label(quarters_of_data: int) -> str:
    if quarters_of_data == 0:
        return "No baseline"
    if quarters_of_data >= 8:
        return "High"
    if quarters_of_data >= 4:
        return "Medium"
    return "Low"


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

    available_max = thresholds["available_max_relative_load"]
    high_load_min = thresholds["high_load_min_relative_load"]
    overextended_min = thresholds["overextended_min_relative_load"]
    relative_load = pd.to_numeric(working_df["relative_load"], errors="coerce")

    labeled = np.select(
        [
            relative_load.isna(),
            relative_load <= available_max,
            relative_load < high_load_min,
            relative_load < overextended_min,
        ],
        [
            "No baseline",
            "Available",
            "Near Historical Norm",
            "High Load",
        ],
        default="Overextended",
    )
    working_df["capacity_label"] = labeled

    return working_df


DIRECTOR_CAPACITY_DASHBOARD_COLUMNS = [
    "opportunity_owner",
    "territory",
    "service_solution",
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
    current_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """End-to-end owner-level table matching dashboard contract."""
    df = opportunity_df.copy()
    df = compute_sales_load(df)
    df = compute_delivery_load(df, current_date=current_date)
    current_df = compute_current_load_by_owner(df)
    baseline_df = compute_historical_baseline(df, as_of_date=current_date)
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

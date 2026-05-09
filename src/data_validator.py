"""Field-level validation utilities for the CGI capacity dashboard.

This module sits between Yixiao's `opportunity_cleaner` (which produces the
merged `opportunity_df`) and Lyken's `capacity_engine` (which scores it). It
provides the field-quality summaries called out in Sprint 1 issue #6 and adds
two reusable helpers — `apply_revenue_hierarchy` and `build_owner_aggregates`
— that downstream code can import directly so the architecture's fallback
rules and dashboard-target columns are not reimplemented per role.
"""

from __future__ import annotations

import pandas as pd


JOIN_KEY = "opportunity_id"


class Fields:
    """Canonical column names this validator reads.

    Centralizing names here lets `_require_columns` raise a clear error if
    `opportunity_cleaner.py` later renames a field, instead of failing deep
    in a pandas operation.
    """

    REVENUE_PRIMARY = "total_estimated_revenue"
    REVENUE_FALLBACK = "opportunity_estimated_revenue_base_cad"
    REVENUE_SERVICE = "service_solution_estimated_revenue"
    REVENUE_FIELDS = [REVENUE_PRIMARY, REVENUE_FALLBACK, REVENUE_SERVICE]

    CREATED_ON = "created_on"
    CLOSE_DATE = "close_date"
    REVENUE_START_DATE = "revenue_start_date"
    DURATION_MONTHS = "project_duration_number_of_months"
    DATE_FIELDS = [CREATED_ON, CLOSE_DATE, REVENUE_START_DATE]

    STATUS = "status"
    STATUS_REASON = "status_reason"
    SALES_STAGE = "sales_stage"
    PROBABILITY = "probability"
    CATEGORICAL_FIELDS = [STATUS, STATUS_REASON, SALES_STAGE, PROBABILITY]

    OWNER = "opportunity_owner"
    MANAGER = "opportunity_manager"
    OWNER_FIELDS = [OWNER, MANAGER]

    TERRITORY = "delivery_territory_center"

    ALL_VALIDATED = (
        REVENUE_FIELDS
        + DATE_FIELDS
        + [DURATION_MONTHS]
        + CATEGORICAL_FIELDS
        + OWNER_FIELDS
    )


# Architecture's late-stage definition (see docs/architecture.md). Used for
# `late_stage_deal_count` in build_owner_aggregates.
LATE_STAGE_VALUES = {
    "4-Proposal",
    "5-Client Decision",
    "6-Negotiation&Signature",
}


def _require_columns(df: pd.DataFrame, expected: list[str]) -> None:
    """Raise a clear KeyError if any expected column is missing.

    Fails fast at the public function boundary, before any pandas math, so a
    schema drift in `opportunity_cleaner.py` surfaces with a readable message
    instead of an unrelated downstream error.
    """
    missing = [column for column in expected if column not in df.columns]
    if missing:
        first_columns = ", ".join(df.columns[:10])
        raise KeyError(
            "data_validator: missing required column(s) "
            f"{missing}. First 10 columns present: {first_columns}"
        )


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _is_blank_string(series: pd.Series) -> pd.Series:
    """True for entries that are strings consisting only of whitespace."""
    return series.map(
        lambda value: isinstance(value, str) and value.strip() == ""
    )


def apply_revenue_hierarchy(df: pd.DataFrame) -> pd.DataFrame:
    """Resolve the architecture's revenue fallback into a single column.

    The architecture (`docs/architecture.md`, "Revenue field") names
    `total_estimated_revenue` as canonical, with
    `opportunity_estimated_revenue_base_cad` as the fallback when the primary
    is missing. Lyken's `capacity_engine.py` only reads the primary; this
    function is the drop-in he can call to honour the fallback rule.

    Returns a 2-column DataFrame:
        - `authoritative_revenue` (float): primary if present, else fallback.
        - `revenue_source` (str): "primary", "fallback", or "none".

    Index is preserved so it can be assigned back to the input frame.
    """
    _require_columns(df, [Fields.REVENUE_PRIMARY, Fields.REVENUE_FALLBACK])

    primary = _coerce_numeric(df[Fields.REVENUE_PRIMARY])
    fallback = _coerce_numeric(df[Fields.REVENUE_FALLBACK])

    use_primary = primary.notna()
    use_fallback = (~use_primary) & fallback.notna()

    authoritative = primary.where(use_primary, fallback)

    source = pd.Series("none", index=df.index, dtype="object")
    source = source.where(~use_primary, "primary")
    source = source.where(~use_fallback, "fallback")

    return pd.DataFrame(
        {
            "authoritative_revenue": authoritative,
            "revenue_source": source,
        },
        index=df.index,
    )


def summarize_missingness(df: pd.DataFrame) -> pd.DataFrame:
    """Per-field null/blank/zero/negative counts across all validated fields.

    One row per field in `Fields.ALL_VALIDATED`. Columns:
        field, dtype, n_total, n_null, pct_null,
        n_blank_string, n_zero, n_negative, family

    `family` groups fields into revenue / date / duration / categorical /
    owner so the report can be rolled up.
    """
    _require_columns(df, Fields.ALL_VALIDATED)

    family_lookup = {
        **{name: "revenue" for name in Fields.REVENUE_FIELDS},
        **{name: "date" for name in Fields.DATE_FIELDS},
        Fields.DURATION_MONTHS: "duration",
        **{name: "categorical" for name in Fields.CATEGORICAL_FIELDS},
        **{name: "owner" for name in Fields.OWNER_FIELDS},
    }

    n_total = len(df)
    rows = []
    for field in Fields.ALL_VALIDATED:
        series = df[field]
        n_null = int(series.isna().sum())
        n_blank = int(_is_blank_string(series).sum())

        numeric = _coerce_numeric(series)
        n_zero = int((numeric == 0).sum())
        n_negative = int((numeric < 0).sum())

        rows.append(
            {
                "field": field,
                "dtype": str(series.dtype),
                "n_total": n_total,
                "n_null": n_null,
                "pct_null": round(n_null / n_total * 100, 2) if n_total else 0.0,
                "n_blank_string": n_blank,
                "n_zero": n_zero,
                "n_negative": n_negative,
                "family": family_lookup[field],
            }
        )

    return pd.DataFrame(rows)


def build_owner_aggregates(
    df: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Owner-level aggregates that complement Lyken's `director_df`.

    Lyken's `capacity_engine.compute_*` functions produce score columns
    (`current_load`, `relative_load`, `capacity_score`, `capacity_label`,
    `historical_avg_load`) but not the four aggregate columns Freya's
    `app/mock_data.py::make_director_capacity_df` declares as the dashboard
    contract: `territory`, `late_stage_deal_count`, `weighted_pipeline_revenue`,
    `inferred_delivery_commitments`. This function fills that gap so the two
    outputs join cleanly on `opportunity_owner`.

    Returns columns:
        opportunity_owner, territory, late_stage_deal_count,
        weighted_pipeline_revenue, inferred_delivery_commitments,
        quarters_of_data, baseline_reliability

    Decisions worth flagging in the validation notes:
      * `inferred_delivery_commitments` uses `status_reason == "Won"` per
        the architecture spec, not Lyken's `status == "won"`. Document any
        row count divergence in the validation notes.
      * `weighted_pipeline_revenue` uses the architecture's revenue fallback
        (via `apply_revenue_hierarchy`), not just `total_estimated_revenue`.
      * Open opps for `weighted_pipeline_revenue` are defined as
        `status == "Open"` (case-insensitive).
      * `baseline_reliability` is a coarse signal — High if the owner has
        ≥ 8 quarters of created opportunities, Medium for ≥ 4, else Low.
    """
    required = [
        Fields.OWNER,
        Fields.STATUS,
        Fields.STATUS_REASON,
        Fields.SALES_STAGE,
        Fields.PROBABILITY,
        Fields.CREATED_ON,
        Fields.CLOSE_DATE,
        Fields.REVENUE_START_DATE,
        Fields.DURATION_MONTHS,
        Fields.REVENUE_PRIMARY,
        Fields.REVENUE_FALLBACK,
        Fields.TERRITORY,
    ]
    _require_columns(df, required)

    if as_of is None:
        as_of = pd.Timestamp.today().normalize()

    work = df.copy()

    revenue_resolved = apply_revenue_hierarchy(work)
    work["_authoritative_revenue"] = revenue_resolved["authoritative_revenue"]

    work["_status_lc"] = work[Fields.STATUS].astype(str).str.strip().str.lower()
    work["_status_reason_norm"] = (
        work[Fields.STATUS_REASON].astype(str).str.strip()
    )

    work["_is_open"] = work["_status_lc"] == "open"
    work["_is_won"] = work["_status_reason_norm"].str.lower() == "won"
    work["_is_late_stage"] = work[Fields.SALES_STAGE].isin(LATE_STAGE_VALUES)

    probability = _coerce_numeric(work[Fields.PROBABILITY]).fillna(0).clip(lower=0)
    work["_weighted_revenue"] = (
        (probability / 100) * work["_authoritative_revenue"]
    ).where(work["_is_open"], 0)

    revenue_start = pd.to_datetime(
        work[Fields.REVENUE_START_DATE], errors="coerce"
    )
    close_date = pd.to_datetime(work[Fields.CLOSE_DATE], errors="coerce")
    duration = _coerce_numeric(work[Fields.DURATION_MONTHS]).fillna(12).clip(lower=1)

    effective_start = revenue_start.fillna(close_date)
    effective_end = effective_start + pd.to_timedelta(duration * 30, unit="D")
    work["_delivery_active"] = (
        work["_is_won"]
        & effective_start.notna()
        & (effective_start <= as_of)
        & (effective_end >= as_of)
    )

    created_on = pd.to_datetime(work[Fields.CREATED_ON], errors="coerce")
    work["_quarter"] = created_on.dt.to_period("Q")

    grouped = work.groupby(Fields.OWNER, dropna=False, sort=True)

    aggregates = pd.DataFrame(
        {
            "territory": grouped[Fields.TERRITORY].agg(
                lambda series: series.dropna().mode().iloc[0]
                if not series.dropna().empty
                else pd.NA
            ),
            "late_stage_deal_count": (
                (work["_is_late_stage"] & work["_is_open"])
                .groupby(work[Fields.OWNER], dropna=False, sort=True)
                .sum()
                .astype(int)
            ),
            "weighted_pipeline_revenue": grouped["_weighted_revenue"].sum().round(2),
            "inferred_delivery_commitments": grouped["_delivery_active"].sum().astype(int),
            "quarters_of_data": grouped["_quarter"].nunique(dropna=True).astype(int),
        }
    ).reset_index()

    aggregates["baseline_reliability"] = aggregates["quarters_of_data"].apply(
        _baseline_reliability_from_quarters
    )

    column_order = [
        Fields.OWNER,
        "territory",
        "late_stage_deal_count",
        "weighted_pipeline_revenue",
        "inferred_delivery_commitments",
        "quarters_of_data",
        "baseline_reliability",
    ]
    return aggregates[column_order]


def _baseline_reliability_from_quarters(n_quarters: int) -> str:
    if n_quarters >= 8:
        return "High"
    if n_quarters >= 4:
        return "Medium"
    return "Low"

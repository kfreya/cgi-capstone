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


def _summary_frame(rows: list[tuple[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["metric", "value"])


def validate_revenue_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue field quality summary as a metric/value table.

    Reports null/zero/negative counts on each revenue field, hierarchy
    resolvability, and cross-field agreement on rows where both opportunity-
    level revenue fields are populated. The 98.7% agreement number observed
    in EDA is reproduced here as a regression check.
    """
    _require_columns(df, Fields.REVENUE_FIELDS)

    primary = _coerce_numeric(df[Fields.REVENUE_PRIMARY])
    fallback = _coerce_numeric(df[Fields.REVENUE_FALLBACK])
    service = _coerce_numeric(df[Fields.REVENUE_SERVICE])

    both_null = primary.isna() & fallback.isna()
    both_present = primary.notna() & fallback.notna()

    if both_present.any():
        ratio = (primary[both_present] - fallback[both_present]).abs() / fallback[
            both_present
        ].abs().replace(0, pd.NA)
        within_5pct = (ratio.fillna(0) <= 0.05).sum()
        exact_match = (
            primary[both_present].round(2) == fallback[both_present].round(2)
        ).sum()
    else:
        within_5pct = 0
        exact_match = 0

    rows: list[tuple[str, object]] = [
        ("n_total", len(df)),
        ("n_primary_null", int(primary.isna().sum())),
        ("n_fallback_null", int(fallback.isna().sum())),
        ("n_service_null", int(service.isna().sum())),
        ("n_primary_zero", int((primary == 0).sum())),
        ("n_fallback_zero", int((fallback == 0).sum())),
        ("n_primary_negative", int((primary < 0).sum())),
        ("n_fallback_negative", int((fallback < 0).sum())),
        ("n_unscoreable_both_null", int(both_null.sum())),
        ("n_both_present", int(both_present.sum())),
        ("n_agreement_within_5pct", int(within_5pct)),
        ("n_exact_match", int(exact_match)),
        (
            "pct_agreement_within_5pct_on_overlap",
            round(float(within_5pct) / both_present.sum() * 100, 2)
            if both_present.any()
            else 0.0,
        ),
        ("n_primary_above_100M", int((primary > 100_000_000).sum())),
        ("n_primary_below_100", int(((primary > 0) & (primary < 100)).sum())),
    ]
    return _summary_frame(rows)


def validate_date_duration_fields(
    df: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Date / duration field quality summary.

    Reports coercion failures, null counts, plausibility-range flags, ordering
    violations (close before created), duration sanity, and — most importantly
    for Lyken — the resolvability of the architecture's delivery-window rule
    on the Won subset (primary `revenue_start_date` vs `close_date` fallback).
    """
    _require_columns(
        df,
        Fields.DATE_FIELDS
        + [Fields.DURATION_MONTHS, Fields.STATUS, Fields.STATUS_REASON],
    )

    if as_of is None:
        as_of = pd.Timestamp.today().normalize()

    created = pd.to_datetime(df[Fields.CREATED_ON], errors="coerce")
    close = pd.to_datetime(df[Fields.CLOSE_DATE], errors="coerce")
    revenue_start = pd.to_datetime(df[Fields.REVENUE_START_DATE], errors="coerce")
    duration = _coerce_numeric(df[Fields.DURATION_MONTHS])

    # `created_on` carries a full timestamp; `close_date` is recorded at
    # midnight. Comparing the raw timestamps counts a deal created and closed
    # on the same calendar day as "closed before created" (the created_on
    # time-of-day is always > 00:00:00). Normalize both to calendar date
    # before any ordering comparison — the un-normalized version inflated
    # `n_close_before_created` roughly eightfold (3,049 vs ~379).
    created_date = created.dt.normalize()
    close_date_norm = close.dt.normalize()

    is_won = df[Fields.STATUS_REASON].astype(str).str.strip().str.lower() == "won"

    delivery_resolvable_primary = is_won & revenue_start.notna()
    delivery_resolvable_fallback = (
        is_won & revenue_start.isna() & close.notna()
    )
    delivery_unresolvable = is_won & revenue_start.isna() & close.isna()

    rows: list[tuple[str, object]] = [
        ("n_total", len(df)),
        ("as_of", str(as_of.date())),
        ("n_created_on_null", int(created.isna().sum())),
        ("n_close_date_null", int(close.isna().sum())),
        ("n_revenue_start_date_null", int(revenue_start.isna().sum())),
        ("n_duration_null", int(duration.isna().sum())),
        ("n_duration_zero", int((duration == 0).sum())),
        ("n_duration_negative", int((duration < 0).sum())),
        ("n_duration_over_60_months", int((duration > 60).sum())),
        (
            "n_close_before_created",
            int(
                (
                    close_date_norm.notna()
                    & created_date.notna()
                    & (close_date_norm < created_date)
                ).sum()
            ),
        ),
        (
            "n_created_after_today",
            int((created_date.notna() & (created_date > as_of)).sum()),
        ),
        ("n_won_total", int(is_won.sum())),
        ("n_won_window_resolvable_primary", int(delivery_resolvable_primary.sum())),
        ("n_won_window_resolvable_fallback", int(delivery_resolvable_fallback.sum())),
        ("n_won_window_unresolvable", int(delivery_unresolvable.sum())),
    ]
    return _summary_frame(rows)


def validate_categorical_fields(
    df: pd.DataFrame,
    expected_stage_weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Categorical scoring fields summary.

    Reports null counts, value distributions, sales_stage coverage against
    the architecture's 7-stage table, and probability range/distribution
    consistency. The crosstab of `status` × `status_reason` is left for
    interactive inspection in the notebook (richer output than fits a
    metric/value table).
    """
    _require_columns(df, Fields.CATEGORICAL_FIELDS)

    status = df[Fields.STATUS]
    status_reason = df[Fields.STATUS_REASON]
    sales_stage = df[Fields.SALES_STAGE]
    probability = _coerce_numeric(df[Fields.PROBABILITY])

    if expected_stage_weights is None:
        try:
            from src.capacity_engine import DEFAULT_STAGE_WEIGHTS
            expected_stage_weights = DEFAULT_STAGE_WEIGHTS
        except ImportError:
            expected_stage_weights = {}

    expected_stages = set(expected_stage_weights.keys())
    observed_stages = set(sales_stage.dropna().unique())
    unmapped_stages = sorted(observed_stages - expected_stages)
    n_rows_with_unmapped_stage = int(sales_stage.isin(unmapped_stages).sum())

    rows: list[tuple[str, object]] = [
        ("n_total", len(df)),
        ("n_status_null", int(status.isna().sum())),
        ("n_status_reason_null", int(status_reason.isna().sum())),
        ("n_sales_stage_null", int(sales_stage.isna().sum())),
        ("n_probability_null", int(probability.isna().sum())),
        ("n_probability_negative", int((probability < 0).sum())),
        ("n_probability_above_100", int((probability > 100).sum())),
        ("n_distinct_status", int(status.dropna().nunique())),
        ("n_distinct_status_reason", int(status_reason.dropna().nunique())),
        ("n_distinct_sales_stage", int(sales_stage.dropna().nunique())),
        ("n_unmapped_sales_stage_values", len(unmapped_stages)),
        ("n_rows_with_unmapped_stage", n_rows_with_unmapped_stage),
        ("unmapped_sales_stage_values", "; ".join(unmapped_stages) or "(none)"),
        (
            "n_status_won_vs_status_reason_won_disagreement",
            int(
                (
                    (status.astype(str).str.strip().str.lower() == "won")
                    != (status_reason.astype(str).str.strip().str.lower() == "won")
                ).sum()
            ),
        ),
    ]
    return _summary_frame(rows)


def validate_owner_identity(df: pd.DataFrame) -> pd.DataFrame:
    """Owner / manager identity field summary.

    Reports null/blank counts, distinct value counts, owner-name normalization
    candidates (rows where lowercase + strip + collapse whitespace yields a
    different string from the raw value), and owner/manager overlap. Does
    NOT auto-rewrite owner names — that requires CGI confirmation and is
    explicitly out of Sprint 1 scope.
    """
    _require_columns(df, Fields.OWNER_FIELDS)

    owner = df[Fields.OWNER]
    manager = df[Fields.MANAGER]

    owner_normalized = owner.astype(str).str.strip().str.replace(
        r"\s+", " ", regex=True
    ).str.lower()

    distinct_raw_owners = owner.dropna().nunique()
    distinct_normalized_owners = owner_normalized[owner.notna()].nunique()
    n_owners_with_variants = distinct_raw_owners - distinct_normalized_owners

    owner_str = owner.astype(str).str.strip()
    n_normalization_changes = int(
        (owner.notna() & (owner_str.str.lower() != owner_normalized)).sum()
    )

    n_owner_equals_manager = int(
        (owner.notna() & manager.notna() & (owner == manager)).sum()
    )

    owner_deal_counts = owner.dropna().value_counts()
    n_owners_with_under_10_opps = int((owner_deal_counts < 10).sum())

    rows: list[tuple[str, object]] = [
        ("n_total", len(df)),
        ("n_owner_null", int(owner.isna().sum())),
        ("n_owner_blank_string", int(_is_blank_string(owner).sum())),
        ("n_manager_null", int(manager.isna().sum())),
        ("n_distinct_owner_raw", int(distinct_raw_owners)),
        ("n_distinct_owner_normalized", int(distinct_normalized_owners)),
        ("n_owners_collapsing_under_normalization", int(n_owners_with_variants)),
        ("n_rows_with_normalization_change", n_normalization_changes),
        ("n_owner_equals_manager", n_owner_equals_manager),
        (
            "pct_owner_equals_manager",
            round(
                n_owner_equals_manager / max(int((owner.notna() & manager.notna()).sum()), 1) * 100,
                2,
            ),
        ),
        ("n_owners_with_under_10_opps", n_owners_with_under_10_opps),
    ]
    return _summary_frame(rows)

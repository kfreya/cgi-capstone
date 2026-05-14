"""Field-level validation utilities for the CGI capacity dashboard.

This module sits between Yixiao's `opportunity_cleaner` and Lyken's
`capacity_engine`. As of Sprint 2 (issue #21) the expected input is the
*cleaned* opportunity table — `clean_opportunity_df(opportunity_df)` — which
preserves every business field from the Week 1 merge and adds merge-provenance
flags, data-quality flags, and a precomputed `authoritative_revenue`. The
field validators read only the 13 business fields, so they also accept the
raw merged `opportunity_df`; `validate_quality_flags` requires the cleaned
frame because it reads the flag columns.

Reusable helpers downstream code can import directly so the architecture's
rules are not reimplemented per role:
  * `apply_revenue_hierarchy` — revenue fallback resolution.
  * `classify_opportunity_outcome` — the won/lost/open/duplicate taxonomy.
  * `build_owner_aggregates` — owner-level dashboard-contract columns.
  * `build_field_reliability_report` — the Kian->Lyken scoring-input handoff.
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

    # Sprint 2: clean_opportunity_df folds the revenue fallback into one
    # precomputed column. apply_revenue_hierarchy still recomputes it from
    # source so the validator stays independent of the cleaner's version.
    AUTHORITATIVE_REVENUE = "authoritative_revenue"

    ALL_VALIDATED = (
        REVENUE_FIELDS
        + DATE_FIELDS
        + [DURATION_MONTHS]
        + CATEGORICAL_FIELDS
        + OWNER_FIELDS
    )

    # Sprint 2: clean_opportunity_df adds merge-provenance flags and
    # data-quality flags. These are deliberately NOT part of ALL_VALIDATED —
    # that list drives summarize_missingness over the business fields only.
    # `source_file_flag` is a provenance label ("opps2_base" /
    # "opps1_exclusive" / "unknown"); every other flag is boolean.
    MERGE_FLAG_COLUMNS = [
        "source_file_flag",
        "duplicate_flag",
        "unmatched_flag",
        "opps1_exclusive_flag",
    ]
    QUALITY_FLAG_COLUMNS = [
        "missing_owner_flag",
        "missing_probability_flag",
        "invalid_probability_flag",
        "missing_revenue_flag",
        "missing_duration_flag",
        "invalid_duration_flag",
        "missing_revenue_start_date_flag",
        "close_before_created_flag",
    ]
    FLAG_COLUMNS = MERGE_FLAG_COLUMNS + QUALITY_FLAG_COLUMNS
    BOOLEAN_FLAG_COLUMNS = [
        "duplicate_flag",
        "unmatched_flag",
        "opps1_exclusive_flag",
        "missing_owner_flag",
        "missing_probability_flag",
        "invalid_probability_flag",
        "missing_revenue_flag",
        "missing_duration_flag",
        "invalid_duration_flag",
        "missing_revenue_start_date_flag",
        "close_before_created_flag",
    ]


# Architecture's late-stage definition (see docs/architecture.md). Used for
# `late_stage_deal_count` in build_owner_aggregates.
LATE_STAGE_VALUES = {
    "4-Proposal",
    "5-Client Decision",
    "6-Negotiation&Signature",
}


# status_reason / status outcome taxonomy (Sprint 2, issue #21).
# `status_reason` is the architecture-canonical outcome field; its values are
# free-text CRM labels, so the "lost" and "cancelled" families are matched by
# prefix while the won/open/duplicate labels are exact. Yixiao's
# `build_owner_base_summary` and Lyken's scoring should import
# `classify_opportunity_outcome` rather than re-deriving these buckets.
#   - WON_REASONS / OPEN_REASONS: exact status_reason (and status fallback).
#   - DUPLICATE_REASONS: a CRM data-quality label. Profiling found zero
#     overlap with the merge-level `duplicate_flag` and only ~3 owners
#     affected, so it is NOT a merge artefact and NOT a win/loss business
#     outcome. It gets its own bucket so callers can exclude it from
#     win/lost/open counts (the Sprint 2 "Option B" decision -- see
#     docs/data_validation.md).
#   - LOST_REASON_PREFIXES: "lost-..." and "cancelled ..." labels. A
#     cancelled pursuit ended unwon, so it is treated as lost-like.
WON_REASONS = {"won"}
OPEN_REASONS = {"open"}
DUPLICATE_REASONS = {"duplicated", "duplicate"}
LOST_REASON_PREFIXES = ("lost", "cancelled", "canceled")


# Each validated field's governing rule in config/fallback_assumptions.yaml
# ("" when no fallback applies). Kept next to the field constants so a rename
# in `Fields` or a rule_id change in the YAML surfaces here too. Consumed by
# `build_field_reliability_report` for the Kian->Lyken handoff.
FIELD_FALLBACK_RULES = {
    Fields.REVENUE_PRIMARY: "revenue_hierarchy",
    Fields.REVENUE_FALLBACK: "revenue_hierarchy",
    Fields.REVENUE_SERVICE: "do_not_sum_service_solution_revenue",
    Fields.CREATED_ON: "",
    Fields.CLOSE_DATE: "delivery_window",
    Fields.REVENUE_START_DATE: "delivery_window",
    Fields.DURATION_MONTHS: "missing_duration",
    Fields.STATUS: "status_reason_outcome",
    Fields.STATUS_REASON: "status_reason_outcome",
    Fields.SALES_STAGE: "late_stage_definition",
    Fields.PROBABILITY: "missing_probability",
    Fields.OWNER: "",
    Fields.MANAGER: "",
}

# Qualitative scoring-input context per field. Live numbers belong in the
# report's computed `pct_null` / `n_anomalies` columns, so these notes stay
# qualitative and do not go stale.
FIELD_NOTES = {
    Fields.REVENUE_PRIMARY: (
        "Canonical CAD revenue; the small null gap is covered by the "
        "revenue_hierarchy fallback. Watch the explicit zero-revenue rows."
    ),
    Fields.REVENUE_FALLBACK: (
        "Now populated on matched rows as well as the opps1-exclusive rows "
        "(null only on the unmatched opps2 rows), so it overlaps the primary "
        "and agrees closely with it. A sound revenue_hierarchy fallback."
    ),
    Fields.REVENUE_SERVICE: (
        "Service-line breakdown. Never sum onto authoritative_revenue (rule "
        "do_not_sum_service_solution_revenue); not a scoring input on its own."
    ),
    Fields.CREATED_ON: (
        "Drives historical baselines and quarters_of_data; nearly fully "
        "populated."
    ),
    Fields.CLOSE_DATE: (
        "Usable as the delivery_window fallback start. Carries a "
        "close-before-created ordering anomaly that shrank sharply once the "
        "timestamp comparison was normalized; still open with CGI."
    ),
    Fields.REVENUE_START_DATE: (
        "Null overall but fully populated on Won deals, where the delivery "
        "window is actually computed."
    ),
    Fields.DURATION_MONTHS: (
        "Nulls, non-positive values, and >60-month outliers all present. The "
        "missing_duration fallback (12 months) applies; count the rows it "
        "fires on."
    ),
    Fields.STATUS: (
        "Fully populated, few distinct values. Outcome bucketing goes through "
        "classify_opportunity_outcome."
    ),
    Fields.STATUS_REASON: (
        "Canonical outcome field. classify_opportunity_outcome handles the "
        "null-reason fallback and the Cancelled/Duplicated taxonomy, so the "
        "Sprint 1 status-disagreement concern is now resolved."
    ),
    Fields.SALES_STAGE: (
        "Fully populated; stage coverage against the architecture weight "
        "table is checked in validate_categorical_fields."
    ),
    Fields.PROBABILITY: (
        "Small null gap plus explicit zeros. The missing_probability fallback "
        "(0) applies; count the rows it fires on. A zero probability is a "
        "valid value, not an anomaly."
    ),
    Fields.OWNER: (
        "Fully populated, no casing/whitespace variants. Primary grouping key."
    ),
    Fields.MANAGER: (
        "Fully populated; distinct from owner on every row, consistent with "
        "the architecture."
    ),
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


def _count_close_before_created(df: pd.DataFrame) -> int:
    """Rows where `close_date` precedes `created_on` on a calendar-date basis.

    `created_on` carries a full timestamp; `close_date` is recorded at
    midnight. Both series are normalized to calendar date before the
    comparison so a deal created and closed on the same day is not falsely
    counted (the un-normalized comparison inflated this roughly eightfold —
    3,049 vs the true ~379). Shared by `validate_date_duration_fields` and
    `validate_quality_flags` so the corrected count has a single definition.
    """
    created = pd.to_datetime(df[Fields.CREATED_ON], errors="coerce").dt.normalize()
    close = pd.to_datetime(df[Fields.CLOSE_DATE], errors="coerce").dt.normalize()
    return int((created.notna() & close.notna() & (close < created)).sum())


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


def classify_opportunity_outcome(df: pd.DataFrame) -> pd.Series:
    """Classify each opportunity into a single outcome bucket.

    Returns a Series aligned to `df.index` with values:
        "won" | "lost" | "open" | "duplicate" | "unknown"

    `status_reason` is the architecture-canonical outcome field and is read
    first; `status` is the fallback for the ~51 rows where `status_reason`
    is null/blank. This is the shared Sprint 2 (issue #21) taxonomy helper —
    Yixiao's `build_owner_base_summary` and Lyken's scoring should import it
    rather than re-deriving outcome buckets with their own string checks.

    Taxonomy ("Option B" — see docs/data_validation.md):
      * status_reason "won"                  -> won
      * status_reason "open"                 -> open
      * status_reason "duplicated"           -> duplicate. A CRM data-quality
        label, not a win/loss business outcome (zero overlap with the
        merge-level `duplicate_flag`). Its own bucket so callers can exclude
        it from win/lost/open counts.
      * status_reason prefix "lost"          -> lost
      * status_reason prefix "cancelled"/"canceled" -> lost. A cancelled
        pursuit ended unwon, so it is lost-like.
      * status_reason null/blank -> fall back to `status`: "won" -> won,
        "open" -> open, "closed" -> lost (the opportunity ended unwon; the
        reason is simply unrecorded), anything else -> unknown.

    This subsumes the Sprint 1 `won_detection` fallback rule: the 15 rows
    with `status == "Won"` but a null `status_reason` now resolve to "won".
    """
    _require_columns(df, [Fields.STATUS, Fields.STATUS_REASON])

    reason = (
        df[Fields.STATUS_REASON].astype("string").str.strip().str.lower().fillna("")
    )
    status = (
        df[Fields.STATUS].astype("string").str.strip().str.lower().fillna("")
    )

    outcome = pd.Series("unknown", index=df.index, dtype="object")

    # status fallback first; the canonical status_reason rules below override.
    outcome = outcome.mask(status.isin(WON_REASONS), "won")
    outcome = outcome.mask(status.isin(OPEN_REASONS), "open")
    outcome = outcome.mask(status == "closed", "lost")

    # status_reason is canonical. An empty string (null/blank reason) matches
    # none of these, so the status fallback is preserved for those rows.
    is_lost_reason = reason.str.startswith(LOST_REASON_PREFIXES).fillna(False)
    outcome = outcome.mask(is_lost_reason, "lost")
    outcome = outcome.mask(reason.isin(DUPLICATE_REASONS), "duplicate")
    outcome = outcome.mask(reason.isin(OPEN_REASONS), "open")
    outcome = outcome.mask(reason.isin(WON_REASONS), "won")

    return outcome


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


def _rate_field(pct_null: float, anomaly_pct: float) -> tuple[str, bool]:
    """Reliability rating + scoring-usability flag from computed rates.

    Thresholds (applied to whichever of null-rate / anomaly-rate is worse):
        < 1%  -> reliable, usable
        < 15% -> use_with_care, usable (a documented fallback covers the gap)
        else  -> not_yet, not usable for formal scoring
    """
    worst = max(pct_null, anomaly_pct)
    if worst < 1.0:
        return "reliable", True
    if worst < 15.0:
        return "use_with_care", True
    return "not_yet", False


def build_field_reliability_report(df: pd.DataFrame) -> pd.DataFrame:
    """One row per validated field rating its fitness as a scoring input.

    This is the machine-readable core of the Kian->Lyken handoff: it turns
    the computed missingness and anomaly counts into a reliability rating, a
    go/no-go `usable_for_scoring` flag, and the `fallback_assumptions.yaml`
    rule that applies. Built on `summarize_missingness` so null counts are
    not re-derived, and on the same anomaly definitions the field validators
    use (e.g. `close_date` is judged against the corrected, calendar-date
    `_count_close_before_created`, not the inflated raw-timestamp count).

    Columns:
        field, family, pct_null, n_anomalies, anomaly_kind,
        reliability {reliable | use_with_care | not_yet},
        usable_for_scoring (bool), fallback_rule, notes

    The rating is computed (see `_rate_field`), not hand-coded per field, so
    re-running it after a data refresh re-judges every field automatically.
    """
    missingness = summarize_missingness(df).set_index("field")
    n_total = int(missingness["n_total"].iloc[0]) if len(missingness) else 0

    # Field-specific anomaly counts: the "is the populated value usable"
    # question, kept separate from "is it populated" (that is pct_null).
    duration = _coerce_numeric(df[Fields.DURATION_MONTHS])
    created = pd.to_datetime(df[Fields.CREATED_ON], errors="coerce").dt.normalize()
    today = pd.Timestamp.today().normalize()
    probability = _coerce_numeric(df[Fields.PROBABILITY])
    status_lc = df[Fields.STATUS].astype(str).str.strip().str.lower()
    reason_lc = df[Fields.STATUS_REASON].astype(str).str.strip().str.lower()

    anomalies: dict[str, tuple[int, str]] = {}
    for field in Fields.REVENUE_FIELDS:
        m = missingness.loc[field]
        anomalies[field] = (
            int(m["n_zero"] + m["n_negative"]),
            "zero_or_negative",
        )
    duration_m = missingness.loc[Fields.DURATION_MONTHS]
    anomalies[Fields.DURATION_MONTHS] = (
        int(duration_m["n_zero"] + duration_m["n_negative"])
        + int((duration > 60).sum()),
        "zero_negative_or_over_60_months",
    )
    anomalies[Fields.CLOSE_DATE] = (
        _count_close_before_created(df),
        "close_before_created",
    )
    anomalies[Fields.CREATED_ON] = (
        int((created.notna() & (created > today)).sum()),
        "created_after_today",
    )
    anomalies[Fields.REVENUE_START_DATE] = (0, "none_null_is_the_concern")
    anomalies[Fields.PROBABILITY] = (
        int(((probability < 0) | (probability > 100)).sum()),
        "out_of_range",
    )
    anomalies[Fields.STATUS_REASON] = (
        int(((status_lc == "won") != (reason_lc == "won")).sum()),
        "won_flag_disagreement",
    )
    anomalies[Fields.STATUS] = (0, "none")
    anomalies[Fields.SALES_STAGE] = (0, "coverage_checked_in_categorical")
    anomalies[Fields.OWNER] = (0, "none")
    anomalies[Fields.MANAGER] = (0, "none")

    rows = []
    for field in Fields.ALL_VALIDATED:
        m = missingness.loc[field]
        pct_null = float(m["pct_null"])
        n_anomalies, anomaly_kind = anomalies[field]
        anomaly_pct = (n_anomalies / n_total * 100) if n_total else 0.0
        reliability, usable = _rate_field(pct_null, anomaly_pct)
        rows.append(
            {
                "field": field,
                "family": m["family"],
                "pct_null": round(pct_null, 2),
                "n_anomalies": n_anomalies,
                "anomaly_kind": anomaly_kind,
                "reliability": reliability,
                "usable_for_scoring": usable,
                "fallback_rule": FIELD_FALLBACK_RULES.get(field, ""),
                "notes": FIELD_NOTES.get(field, ""),
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
        open_opportunity_count, lost_opportunity_count,
        duplicate_opportunity_count, quarters_of_data, baseline_reliability

    Decisions worth flagging in the validation notes:
      * Won / lost / open / duplicate are all derived from the shared
        `classify_opportunity_outcome` helper, not from ad-hoc string
        checks. `inferred_delivery_commitments` therefore counts the
        canonical "won" set (status_reason "Won", plus the won-detection
        fallback for null-reason rows). `duplicate_opportunity_count` is
        surfaced so the Option B taxonomy decision is auditable per owner.
      * `weighted_pipeline_revenue` uses the architecture's revenue fallback
        (via `apply_revenue_hierarchy`), not just `total_estimated_revenue`.
      * Open opps for `weighted_pipeline_revenue` are defined as
        `_outcome == "open"` (equivalent to `status == "Open"` in this data).
      * `baseline_reliability` is a coarse signal — High if the owner has
        ≥ 8 quarters of created opportunities, Medium for ≥ 4, else Low.
      * Duplicate join-key rows (`duplicate_flag` / `is_duplicate_join_key`)
        are deduplicated on `opportunity_id` (keep first) before aggregation
        so revenue and deal counts are not double-counted for the affected
        owner. `unmatched_flag` and `opps1_exclusive_flag` rows are kept —
        they are legitimate distinct opportunities.
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

    # Sprint 2: cleaned_opportunity_df may carry duplicate join-key rows
    # (marked by `duplicate_flag` / `is_duplicate_join_key`). Aggregating them
    # as-is double-counts revenue and deal counts for the affected owner, so
    # deduplicate on the join key (keep first) when it is present. Guarded so
    # the function still accepts the flag-less minimal fixture used in the
    # validator tests and any raw frame without `opportunity_id`.
    if JOIN_KEY in work.columns:
        work = work.drop_duplicates(subset=[JOIN_KEY], keep="first")

    revenue_resolved = apply_revenue_hierarchy(work)
    work["_authoritative_revenue"] = revenue_resolved["authoritative_revenue"]

    # Single source of truth for won/lost/open/duplicate — see
    # classify_opportunity_outcome. Replaces the Sprint 1 ad-hoc
    # `status_reason == "won"` check and applies the won-detection fallback.
    work["_outcome"] = classify_opportunity_outcome(work)
    work["_is_open"] = work["_outcome"] == "open"
    work["_is_won"] = work["_outcome"] == "won"
    work["_is_lost"] = work["_outcome"] == "lost"
    work["_is_duplicate"] = work["_outcome"] == "duplicate"
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
            "open_opportunity_count": grouped["_is_open"].sum().astype(int),
            "lost_opportunity_count": grouped["_is_lost"].sum().astype(int),
            "duplicate_opportunity_count": grouped["_is_duplicate"].sum().astype(int),
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
        "open_opportunity_count",
        "lost_opportunity_count",
        "duplicate_opportunity_count",
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

    # `created_on` carries a full timestamp; normalize to calendar date so a
    # row created earlier today is not counted as "created after today"
    # (`as_of` is midnight-normalized). The close/created ordering check uses
    # `_count_close_before_created`, which applies the same normalization.
    created_date = created.dt.normalize()

    # Use the shared taxonomy so the validator's "won" set matches
    # build_owner_aggregates and the architecture's won-detection fallback.
    is_won = classify_opportunity_outcome(df) == "won"

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
        ("n_close_before_created", _count_close_before_created(df)),
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


def validate_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Sprint 2 merge-flag and data-quality-flag summary as a metric/value table.

    Requires the cleaned opportunity frame (`clean_opportunity_df`), which
    carries the merge-provenance flags and data-quality flags;
    `_require_columns` fails fast if a raw frame is passed instead. Reports a
    count for each boolean flag, the `source_file_flag` provenance breakdown,
    and two cross-checks against the field validators:

      * `missing_revenue_flag` should equal `validate_revenue_fields`'
        `n_unscoreable_both_null` — both mean "no opportunity-level revenue
        candidate for `authoritative_revenue`". The signed gap is reported as
        `flag_discrepancy_missing_revenue` (expected 0).
      * `close_before_created_flag` is computed by the cleaner with an
        un-normalized timestamp comparison — the same bug fixed in
        `validate_date_duration_fields`. The flag sum is compared against the
        corrected calendar-date count from `_count_close_before_created`; the
        gap is reported as `flag_discrepancy_close_before_created`. This is a
        documented finding for Yixiao's `opportunity_cleaner.py`, not an edit
        to another owner's module.
    """
    _require_columns(df, Fields.FLAG_COLUMNS)

    rows: list[tuple[str, object]] = [("n_total", len(df))]

    # source_file_flag is a provenance label, not a boolean — break it down.
    source_counts = df["source_file_flag"].astype(str).value_counts(dropna=False)
    for label, count in source_counts.items():
        rows.append((f"source_file_flag::{label}", int(count)))

    for flag in Fields.BOOLEAN_FLAG_COLUMNS:
        rows.append(
            (f"{flag}_count", int(df[flag].fillna(False).astype(bool).sum()))
        )

    # Cross-check 1: missing_revenue_flag vs the revenue validator.
    missing_revenue_flag_count = int(
        df["missing_revenue_flag"].fillna(False).astype(bool).sum()
    )
    revenue_summary = validate_revenue_fields(df)
    revenue_metrics = dict(
        zip(revenue_summary["metric"], revenue_summary["value"])
    )
    n_unscoreable_both_null = int(revenue_metrics["n_unscoreable_both_null"])
    rows.append(
        (
            "flag_discrepancy_missing_revenue",
            missing_revenue_flag_count - n_unscoreable_both_null,
        )
    )

    # Cross-check 2: the cleaner's close_before_created_flag (un-normalized
    # timestamp comparison) vs the corrected calendar-date count. The flag
    # count itself is already emitted by the boolean-flag loop above.
    flag_close_before_created = int(
        df["close_before_created_flag"].fillna(False).astype(bool).sum()
    )
    corrected_close_before_created = _count_close_before_created(df)
    rows.append(
        ("n_close_before_created_corrected", corrected_close_before_created)
    )
    rows.append(
        (
            "flag_discrepancy_close_before_created",
            flag_close_before_created - corrected_close_before_created,
        )
    )

    return _summary_frame(rows)

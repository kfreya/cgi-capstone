from __future__ import annotations

import pandas as pd
import pytest

from src.data_validator import (
    JOIN_KEY,
    Fields,
    apply_revenue_hierarchy,
    build_owner_aggregates,
    summarize_missingness,
    validate_categorical_fields,
    validate_date_duration_fields,
    validate_owner_identity,
    validate_quality_flags,
    validate_revenue_fields,
)


def test_apply_revenue_hierarchy_uses_primary_when_present():
    df = pd.DataFrame(
        {
            Fields.REVENUE_PRIMARY: [100.0, None, None],
            Fields.REVENUE_FALLBACK: [55.0, 200.0, None],
        }
    )

    result = apply_revenue_hierarchy(df)

    assert result.loc[0, "authoritative_revenue"] == 100.0
    assert result.loc[0, "revenue_source"] == "primary"
    assert result.loc[1, "authoritative_revenue"] == 200.0
    assert result.loc[1, "revenue_source"] == "fallback"
    assert pd.isna(result.loc[2, "authoritative_revenue"])
    assert result.loc[2, "revenue_source"] == "none"


def test_apply_revenue_hierarchy_raises_on_missing_columns():
    df = pd.DataFrame({Fields.REVENUE_PRIMARY: [1.0]})
    with pytest.raises(KeyError, match="opportunity_estimated_revenue_base_cad"):
        apply_revenue_hierarchy(df)


def _minimal_validated_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            Fields.REVENUE_PRIMARY: [1000.0, None],
            Fields.REVENUE_FALLBACK: [None, 500.0],
            Fields.REVENUE_SERVICE: [None, None],
            Fields.CREATED_ON: pd.to_datetime(["2024-01-01", "2024-06-01"]),
            Fields.CLOSE_DATE: pd.to_datetime(["2024-03-01", "2024-08-01"]),
            Fields.REVENUE_START_DATE: pd.to_datetime(["2024-04-01", None]),
            Fields.DURATION_MONTHS: [6, 12],
            Fields.STATUS: ["Open", "Won"],
            Fields.STATUS_REASON: ["In Progress", "Won"],
            Fields.SALES_STAGE: ["4-Proposal", "6-Negotiation&Signature"],
            Fields.PROBABILITY: [50, 100],
            Fields.OWNER: ["Alice", "Bob"],
            Fields.MANAGER: ["Carol", "Dave"],
        }
    )


def _cleaned_validated_df() -> pd.DataFrame:
    """Flag-bearing fixture mimicking `clean_opportunity_df` output.

    Extends the minimal business-field frame with the `opportunity_id` join
    key, the four merge-provenance flags, and the eight data-quality flags
    that `clean_opportunity_df` adds. Kept separate from
    `_minimal_validated_df` so the flag-less back-compat path stays tested.
    """
    df = _minimal_validated_df()
    df[Fields.TERRITORY] = ["CAN ATL Atlantic", "CAN ATL Atlantic"]
    df[JOIN_KEY] = ["OPP-1", "OPP-2"]
    df["source_file_flag"] = ["opps2_base", "opps2_base"]
    df["duplicate_flag"] = [False, False]
    df["unmatched_flag"] = [False, False]
    df["opps1_exclusive_flag"] = [False, False]
    df["missing_owner_flag"] = [False, False]
    df["missing_probability_flag"] = [False, False]
    df["invalid_probability_flag"] = [False, False]
    df["missing_revenue_flag"] = [False, False]
    df["missing_duration_flag"] = [False, False]
    df["invalid_duration_flag"] = [False, False]
    df["missing_revenue_start_date_flag"] = [False, True]
    df["close_before_created_flag"] = [False, False]
    return df


def test_summarize_missingness_returns_one_row_per_validated_field():
    df = _minimal_validated_df()

    result = summarize_missingness(df)

    assert set(result["field"]) == set(Fields.ALL_VALIDATED)
    assert len(result) == len(Fields.ALL_VALIDATED)
    assert (result["n_total"] == 2).all()

    primary_row = result[result["field"] == Fields.REVENUE_PRIMARY].iloc[0]
    assert primary_row["n_null"] == 1
    assert primary_row["pct_null"] == 50.0
    assert primary_row["family"] == "revenue"


def test_build_owner_aggregates_schema_matches_dashboard_contract():
    df = _minimal_validated_df()
    df[Fields.TERRITORY] = ["CAN ATL Atlantic", "CAN ATL Atlantic"]

    as_of = pd.Timestamp("2024-09-01")
    result = build_owner_aggregates(df, as_of=as_of)

    expected_columns = [
        Fields.OWNER,
        "territory",
        "late_stage_deal_count",
        "weighted_pipeline_revenue",
        "inferred_delivery_commitments",
        "quarters_of_data",
        "baseline_reliability",
    ]
    assert list(result.columns) == expected_columns
    assert set(result[Fields.OWNER]) == {"Alice", "Bob"}

    alice = result[result[Fields.OWNER] == "Alice"].iloc[0]
    assert alice["late_stage_deal_count"] == 1
    assert alice["weighted_pipeline_revenue"] == 500.0
    assert alice["inferred_delivery_commitments"] == 0

    bob = result[result[Fields.OWNER] == "Bob"].iloc[0]
    assert bob["inferred_delivery_commitments"] == 1
    assert bob["late_stage_deal_count"] == 0
    assert bob["weighted_pipeline_revenue"] == 0


def test_build_owner_aggregates_deduplicates_duplicate_join_key_rows():
    df = _cleaned_validated_df()
    # Duplicate Alice's row under the same opportunity_id, flagged as a dup.
    duplicate_row = df.iloc[[0]].copy()
    duplicate_row["duplicate_flag"] = True
    df.loc[0, "duplicate_flag"] = True
    dup_df = pd.concat([df, duplicate_row], ignore_index=True)

    result = build_owner_aggregates(dup_df, as_of=pd.Timestamp("2024-09-01"))

    alice = result[result[Fields.OWNER] == "Alice"].iloc[0]
    # Without dedup the single late-stage open deal would be counted twice
    # and its weighted revenue ($500) would be doubled.
    assert alice["late_stage_deal_count"] == 1
    assert alice["weighted_pipeline_revenue"] == 500.0


def test_validate_quality_flags_counts_and_cross_checks():
    df = _cleaned_validated_df()

    result = validate_quality_flags(df)

    assert list(result.columns) == ["metric", "value"]
    metrics = dict(zip(result["metric"], result["value"]))
    assert metrics["n_total"] == 2
    assert metrics["source_file_flag::opps2_base"] == 2
    assert metrics["missing_revenue_start_date_flag_count"] == 1
    assert metrics["duplicate_flag_count"] == 0
    # Cross-checks reconcile to zero on clean fixture data.
    assert metrics["flag_discrepancy_missing_revenue"] == 0
    assert metrics["flag_discrepancy_close_before_created"] == 0


def test_validate_quality_flags_requires_flag_columns():
    df = _minimal_validated_df()  # business fields only, no flag columns
    with pytest.raises(KeyError, match="source_file_flag"):
        validate_quality_flags(df)


def test_validate_revenue_fields_returns_metric_value_summary():
    df = _minimal_validated_df()

    result = validate_revenue_fields(df)

    assert list(result.columns) == ["metric", "value"]
    metrics = dict(zip(result["metric"], result["value"]))
    assert metrics["n_total"] == 2
    assert metrics["n_primary_null"] == 1
    assert metrics["n_fallback_null"] == 1
    assert metrics["n_unscoreable_both_null"] == 0


def test_validate_date_duration_flags_close_before_created():
    df = _minimal_validated_df()
    df.loc[0, Fields.CLOSE_DATE] = pd.Timestamp("2023-01-01")  # before created_on

    result = validate_date_duration_fields(
        df, as_of=pd.Timestamp("2024-09-01")
    )

    metrics = dict(zip(result["metric"], result["value"]))
    assert metrics["n_close_before_created"] == 1


def test_validate_date_duration_same_day_close_not_flagged():
    """Regression: created_on carries a time component, close_date is midnight.

    A deal created and closed on the same calendar day must not register as
    `close_date < created_on`. The pre-fix code compared raw timestamps, so
    any same-day row counted (created_on time-of-day is always > 00:00:00),
    inflating the count roughly eightfold.
    """
    df = _minimal_validated_df()
    df.loc[0, Fields.CREATED_ON] = pd.Timestamp("2024-01-01 14:30:00")
    df.loc[0, Fields.CLOSE_DATE] = pd.Timestamp("2024-01-01 00:00:00")

    result = validate_date_duration_fields(
        df, as_of=pd.Timestamp("2024-09-01")
    )

    metrics = dict(zip(result["metric"], result["value"]))
    assert metrics["n_close_before_created"] == 0


def test_validate_categorical_fields_detects_status_disagreement():
    df = _minimal_validated_df()
    df.loc[0, Fields.STATUS] = "Won"
    df.loc[0, Fields.STATUS_REASON] = "Lost"

    result = validate_categorical_fields(df)

    metrics = dict(zip(result["metric"], result["value"]))
    assert metrics["n_status_won_vs_status_reason_won_disagreement"] == 1


def test_validate_owner_identity_counts_overlap():
    df = _minimal_validated_df()
    df.loc[0, Fields.MANAGER] = "Alice"

    result = validate_owner_identity(df)

    metrics = dict(zip(result["metric"], result["value"]))
    assert metrics["n_owner_equals_manager"] == 1
    assert metrics["n_distinct_owner_raw"] == 2

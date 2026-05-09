from __future__ import annotations

import pandas as pd
import pytest

from src.data_validator import (
    Fields,
    apply_revenue_hierarchy,
    build_owner_aggregates,
    summarize_missingness,
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

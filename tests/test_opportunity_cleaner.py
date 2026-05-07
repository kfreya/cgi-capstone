import pandas as pd

from src.opportunity_cleaner import (
    clean_column_name,
    clean_column_names,
    collapse_supplemental_fields,
    compare_schemas,
    merge_opportunity_tables,
)


def test_clean_column_name_normalizes_to_snake_case():
    assert clean_column_name("Opportunity ID") == "opportunity_id"
    assert clean_column_name("(Do Not Modify) Opportunity - Product") == "opportunity_product"
    assert clean_column_name("Delivery Territory / Center") == "delivery_territory_center"


def test_clean_column_names_returns_copy_with_unique_columns():
    df = pd.DataFrame(
        {
            "(Do Not Modify) Modified on": ["first"],
            "Modified on": ["second"],
        }
    )

    cleaned = clean_column_names(df)

    assert list(cleaned.columns) == ["modified_on", "modified_on_2"]
    assert list(df.columns) == ["(Do Not Modify) Modified on", "Modified on"]


def test_compare_schemas_uses_normalized_columns():
    opps1 = pd.DataFrame({"Opportunity ID": ["a"], "Service / solution": ["x"]})
    opps2 = pd.DataFrame({"Opportunity ID": ["a"], "Status": ["open"]})

    schema = compare_schemas(opps1, opps2).set_index("column")

    assert schema.loc["opportunity_id", "location"] == "both"
    assert schema.loc["service_solution", "location"] == "opps1_only"
    assert schema.loc["status", "location"] == "opps2_only"


def test_merge_opportunity_tables_uses_opps2_base_and_flags_records():
    opps1 = pd.DataFrame(
        {
            "Opportunity ID": ["A", "A", "C"],
            "(Do Not Modify) Opportunity - Product": ["p1", "p2", "p3"],
            "Service / solution": ["s1", "s2", "s3"],
            "Service / Solution Estimated revenue": [10, 20, 30],
            "IP": ["i1", "i2", "i3"],
            "Delivery Territory / Center": ["d1", "d2", "d3"],
        }
    )
    opps2 = pd.DataFrame(
        {
            "Opportunity ID": ["A", "B"],
            "Status": ["open", "closed"],
            "Total estimated revenue": [100, 200],
        }
    )

    opportunity_df, merge_summary = merge_opportunity_tables(opps1, opps2)
    summary = merge_summary.set_index("metric")["value"].to_dict()

    assert len(opportunity_df) == 3
    assert summary["join_key_used"] == "opportunity_id"
    assert summary["opps1_unique_ids"] == 2
    assert summary["opps2_unique_ids"] == 2
    assert summary["matched_ids"] == 1
    assert summary["opps1_exclusive_ids"] == 1
    assert summary["opps2_base_unmatched_ids"] == 1
    assert summary["expected_no_expansion_row_count"] == 3
    assert summary["row_count_matches_no_expansion"] is True
    assert summary["opps1_duplicate_id_count"] == 1
    assert summary["opps1_duplicate_row_count"] == 2

    duplicate_rows = opportunity_df[opportunity_df["is_duplicate_join_key"]]
    exclusive_rows = opportunity_df[opportunity_df["is_opps1_exclusive"]]
    unmatched_rows = opportunity_df[opportunity_df["is_unmatched_opps2_base"]]

    assert duplicate_rows.empty
    assert list(exclusive_rows["opportunity_id"]) == ["C"]
    assert list(unmatched_rows["opportunity_id"]) == ["B"]


def test_collapse_supplemental_fields_uses_first_non_empty_value():
    opps1 = pd.DataFrame(
        {
            "opportunity_id": ["A", "A", "B"],
            "service_solution": [" ", "Solution A", None],
            "ip": [None, "IP A", ""],
        }
    )

    collapsed = collapse_supplemental_fields(
        opps1,
        "opportunity_id",
        ["service_solution", "ip"],
    ).set_index("opportunity_id")

    assert len(collapsed) == 2
    assert collapsed.loc["A", "service_solution"] == "Solution A"
    assert collapsed.loc["A", "ip"] == "IP A"
    assert pd.isna(collapsed.loc["B", "service_solution"])


def test_opps1_duplicates_do_not_expand_matching_opps2_row():
    opps1 = pd.DataFrame(
        {
            "Opportunity ID": ["A", "A"],
            "Service / solution": ["Solution A1", "Solution A2"],
        }
    )
    opps2 = pd.DataFrame(
        {
            "Opportunity ID": ["A"],
            "Status": ["open"],
        }
    )

    opportunity_df, merge_summary = merge_opportunity_tables(opps1, opps2)
    summary = merge_summary.set_index("metric")["value"].to_dict()

    assert len(opportunity_df) == 1
    assert list(opportunity_df["opportunity_id"]) == ["A"]
    assert list(opportunity_df["source_table"]) == ["opps2_base"]
    assert int(opportunity_df["is_duplicate_join_key"].sum()) == 0
    assert summary["expected_no_expansion_row_count"] == 1
    assert summary["opportunity_df_row_count"] == 1
    assert summary["row_count_matches_no_expansion"] is True

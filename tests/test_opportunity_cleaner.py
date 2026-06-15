import inspect
import openpyxl
from pathlib import Path

import pandas as pd
import pytest

from src.opportunity_cleaner import (
    EXCEL_SHEET_NAME,
    OPPS1_PATH,
    OPPS2_PATH,
    PROCESSED_DIR,
    build_owner_base_summary,
    clean_column_name,
    clean_column_names,
    clean_opportunity_df,
    collapse_supplemental_fields,
    compare_schemas,
    load_opportunity_files,
    merge_opportunity_tables,
    parse_args,
    write_outputs,
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
            "Opportunity Estimated Revenue Base CAD": [90, 95, 300],
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
    matched_row = opportunity_df[opportunity_df["opportunity_id"] == "A"].iloc[0]

    assert duplicate_rows.empty
    assert matched_row["opportunity_estimated_revenue_base_cad"] == 90
    assert list(exclusive_rows["opportunity_id"]) == ["C"]
    assert list(unmatched_rows["opportunity_id"]) == ["B"]


def test_json_s_num_is_preserved_as_rfp_alias():
    opps1 = pd.DataFrame(
        {
            "Opportunity ID": ["A", "A", "C"],
            "Json S-Num": [" ", "RFP-123", "RFP-999"],
        }
    )
    opps2 = pd.DataFrame(
        {
            "Opportunity ID": ["A", "B"],
            "Status": ["open", "closed"],
        }
    )

    opportunity_df, merge_summary = merge_opportunity_tables(opps1, opps2)
    cleaned = clean_opportunity_df(opportunity_df).set_index("opportunity_id")
    summary = merge_summary.set_index("metric")["value"].to_dict()

    assert "json_s_num" in opportunity_df.columns
    assert "json_s_num" in summary["supplemental_fields_found"]
    assert cleaned.loc["A", "json_s_num"] == "RFP-123"
    assert cleaned.loc["A", "rfp_alias"] == "RFP-123"
    assert bool(cleaned.loc["A", "has_rfp_alias"]) is True
    assert cleaned.loc["C", "rfp_alias"] == "RFP-999"
    assert bool(cleaned.loc["C", "has_rfp_alias"]) is True
    assert pd.isna(cleaned.loc["B", "rfp_alias"])
    assert bool(cleaned.loc["B", "has_rfp_alias"]) is False


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


def test_clean_opportunity_df_adds_sprint2_flags_without_mutating_input():
    opportunity_df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B", "C"],
            "source_table": ["opps2_base", "opps2_base", "opps1_exclusive"],
            "is_duplicate_join_key": [False, True, False],
            "is_unmatched_opps2_base": [False, True, False],
            "is_opps1_exclusive": [False, False, True],
            "opportunity_owner": ["Alice", " ", None],
            "probability": ["75", "105", "bad"],
            "total_estimated_revenue": ["1000", None, None],
            "opportunity_estimated_revenue_base_cad": ["900", None, "500"],
            "service_solution_estimated_revenue": ["20", "bad", None],
            "project_duration_number_of_months": ["12", "0", None],
            "created_on": ["2024-01-10", "2024-02-01", "not a date"],
            "close_date": ["2024-02-10", "2024-01-15", "2024-03-01"],
            "revenue_start_date": ["2024-03-01", None, "bad"],
        }
    )
    original = opportunity_df.copy(deep=True)

    cleaned = clean_opportunity_df(opportunity_df)

    pd.testing.assert_frame_equal(opportunity_df, original)

    for column in original.columns:
        assert column in cleaned.columns

    assert list(cleaned["source_table"]) == list(original["source_table"])
    assert list(cleaned["source_file_flag"]) == [
        "opps2_base",
        "opps2_base",
        "opps1_exclusive",
    ]
    assert list(cleaned["duplicate_flag"]) == [False, True, False]
    assert list(cleaned["unmatched_flag"]) == [False, True, False]
    assert list(cleaned["opps1_exclusive_flag"]) == [False, False, True]

    assert pd.api.types.is_numeric_dtype(cleaned["probability"])
    assert cleaned.loc[0, "probability"] == 75
    assert pd.isna(cleaned.loc[2, "probability"])
    assert pd.api.types.is_numeric_dtype(cleaned["service_solution_estimated_revenue"])
    assert pd.isna(cleaned.loc[1, "service_solution_estimated_revenue"])
    assert "authoritative_revenue" in cleaned.columns
    assert cleaned.loc[0, "authoritative_revenue"] == 1000
    assert pd.isna(cleaned.loc[1, "authoritative_revenue"])
    assert cleaned.loc[2, "authoritative_revenue"] == 500
    assert cleaned.loc[0, "authoritative_revenue"] != (
        cleaned.loc[0, "total_estimated_revenue"]
        + cleaned.loc[0, "service_solution_estimated_revenue"]
    )

    assert pd.api.types.is_datetime64_any_dtype(cleaned["created_on"])
    assert cleaned.loc[0, "created_on"] == pd.Timestamp("2024-01-10")
    assert pd.isna(cleaned.loc[2, "created_on"])

    expected_quality_flags = [
        "missing_owner_flag",
        "missing_probability_flag",
        "invalid_probability_flag",
        "missing_revenue_flag",
        "missing_duration_flag",
        "invalid_duration_flag",
        "missing_revenue_start_date_flag",
        "close_before_created_flag",
    ]
    for flag in expected_quality_flags:
        assert flag in cleaned.columns

    assert list(cleaned["missing_owner_flag"]) == [False, True, True]
    assert list(cleaned["missing_probability_flag"]) == [False, False, True]
    assert list(cleaned["invalid_probability_flag"]) == [False, True, False]
    assert list(cleaned["missing_revenue_flag"]) == [False, True, False]
    assert list(cleaned["missing_duration_flag"]) == [False, False, True]
    assert list(cleaned["invalid_duration_flag"]) == [False, True, False]
    assert list(cleaned["missing_revenue_start_date_flag"]) == [False, True, True]
    assert list(cleaned["close_before_created_flag"]) == [False, True, False]


def test_clean_opportunity_df_close_before_created_uses_calendar_dates():
    opportunity_df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B", "C"],
            "created_on": [
                "2024-01-01 14:30:00",
                "2024-01-02 09:00:00",
                "2024-01-03 09:00:00",
            ],
            "close_date": [
                "2024-01-01 00:00:00",
                "2024-01-01 00:00:00",
                "2024-01-04 00:00:00",
            ],
        }
    )

    cleaned = clean_opportunity_df(opportunity_df)

    assert list(cleaned["close_before_created_flag"]) == [False, True, False]


def test_clean_opportunity_df_uses_safe_defaults_when_week1_columns_missing():
    cleaned = clean_opportunity_df(pd.DataFrame({"opportunity_id": ["A"]}))

    assert cleaned.loc[0, "source_file_flag"] == "unknown"
    assert bool(cleaned.loc[0, "duplicate_flag"]) is False
    assert bool(cleaned.loc[0, "unmatched_flag"]) is False
    assert bool(cleaned.loc[0, "opps1_exclusive_flag"]) is False


def test_build_owner_base_summary_groups_cleaned_opportunities_without_mutating_input():
    cleaned_df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B", "C", "D", "E"],
            "opportunity_owner": ["Alice", "Alice", " ", None, None],
            "status": ["Open", "Closed", "Closed", "Open", "Active"],
            "status_reason": ["In Progress", "Won", "Lost", "Cancelled", "Duplicated"],
            "probability": [50, None, 20, 80, 60],
            "missing_probability_flag": [False, True, False, False, False],
            "missing_revenue_flag": [False, True, False, False, True],
            "missing_duration_flag": [False, True, False, True, False],
            "duplicate_flag": [False, True, False, True, False],
            "unmatched_flag": [False, True, False, False, False],
            "opps1_exclusive_flag": [False, False, True, False, False],
            "total_estimated_revenue": [1000, None, None, None, None],
            "opportunity_estimated_revenue_base_cad": [None, None, 500, 300, None],
            "service_solution_estimated_revenue": [5, 10, 15, 20, 25],
        }
    )
    original = cleaned_df.copy(deep=True)

    summary = build_owner_base_summary(cleaned_df)

    pd.testing.assert_frame_equal(cleaned_df, original)

    expected_columns = [
        "opportunity_owner",
        "opportunity_count",
        "open_opportunity_count",
        "won_opportunity_count",
        "lost_opportunity_count",
        "avg_probability",
        "missing_probability_count",
        "missing_revenue_count",
        "missing_duration_count",
        "duplicate_count",
        "unmatched_count",
        "opps1_exclusive_count",
        "total_estimated_revenue_sum",
        "opportunity_estimated_revenue_base_cad_sum",
    ]
    assert list(summary.columns) == expected_columns
    assert list(summary["opportunity_owner"]) == ["Alice", "Unknown"]

    alice = summary[summary["opportunity_owner"] == "Alice"].iloc[0]
    assert alice["opportunity_count"] == 2
    assert alice["open_opportunity_count"] == 1
    assert alice["won_opportunity_count"] == 1
    assert alice["lost_opportunity_count"] == 0
    assert alice["avg_probability"] == 50
    assert alice["missing_probability_count"] == 1
    assert alice["missing_revenue_count"] == 1
    assert alice["missing_duration_count"] == 1
    assert alice["duplicate_count"] == 1
    assert alice["unmatched_count"] == 1
    assert alice["opps1_exclusive_count"] == 0
    assert alice["total_estimated_revenue_sum"] == 1000
    assert pd.isna(alice["opportunity_estimated_revenue_base_cad_sum"])

    unknown = summary[summary["opportunity_owner"] == "Unknown"].iloc[0]
    assert unknown["opportunity_count"] == 3
    assert unknown["open_opportunity_count"] == 0
    assert unknown["won_opportunity_count"] == 0
    assert unknown["lost_opportunity_count"] == 2
    assert unknown["missing_probability_count"] == 0
    assert unknown["missing_revenue_count"] == 1
    assert unknown["missing_duration_count"] == 1
    assert unknown["duplicate_count"] == 1
    assert unknown["unmatched_count"] == 0
    assert unknown["opps1_exclusive_count"] == 1
    assert pd.isna(unknown["total_estimated_revenue_sum"])
    assert unknown["opportunity_estimated_revenue_base_cad_sum"] == 800
    assert "authoritative_revenue" not in summary.columns


def test_build_owner_base_summary_uses_shared_outcome_taxonomy():
    cleaned_df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B", "C", "D", "E", "F", "G"],
            "opportunity_owner": ["Taxonomy"] * 7,
            "status": [
                "Closed",
                "Closed",
                "Closed",
                "Closed",
                "Open",
                "Won",
                "Closed",
            ],
            "status_reason": [
                "Cancelled",
                "Canceled",
                "Duplicated",
                "Duplicate",
                None,
                " ",
                pd.NA,
            ],
        }
    )

    summary = build_owner_base_summary(cleaned_df)

    row = summary.iloc[0]
    assert row["opportunity_count"] == 7
    assert row["open_opportunity_count"] == 1
    assert row["won_opportunity_count"] == 1
    assert row["lost_opportunity_count"] == 3


def test_build_owner_base_summary_uses_safe_fallbacks_for_missing_optional_columns():
    cleaned_df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B"],
            "probability": ["bad", "25"],
            "total_estimated_revenue": [None, "200"],
            "project_duration_number_of_months": [None, "6"],
            "is_duplicate_join_key": [True, False],
        }
    )

    summary = build_owner_base_summary(cleaned_df)

    assert list(summary["opportunity_owner"]) == ["Unknown"]
    row = summary.iloc[0]
    assert row["opportunity_count"] == 2
    assert row["missing_probability_count"] == 1
    assert row["missing_revenue_count"] == 1
    assert row["missing_duration_count"] == 1
    assert row["duplicate_count"] == 1
    assert row["unmatched_count"] == 0
    assert row["opps1_exclusive_count"] == 0
    assert row["total_estimated_revenue_sum"] == 200


def test_write_outputs_writes_week1_and_sprint2_artifacts_to_temp_dir(tmp_path):
    opportunity_df = pd.DataFrame(
        {
            "opportunity_id": ["A", "B"],
            "source_table": ["opps2_base", "opps1_exclusive"],
            "merge_status_opps2_base": ["matched_opps1", "opps1_exclusive"],
            "is_duplicate_join_key": [False, False],
            "is_opps1_exclusive": [False, True],
            "is_unmatched_opps2_base": [False, False],
            "opportunity_owner": ["Alice", "Bob"],
            "status": ["Open", "Closed Won"],
            "probability": ["50", "100"],
            "total_estimated_revenue": ["1000", None],
            "opportunity_estimated_revenue_base_cad": [None, "500"],
            "project_duration_number_of_months": ["12", "6"],
            "created_on": ["2024-01-01", "2024-02-01"],
            "close_date": ["2024-03-01", "2024-04-01"],
            "revenue_start_date": ["2024-05-01", None],
        }
    )
    schema_comparison = pd.DataFrame(
        {
            "column": ["opportunity_id"],
            "in_opps1": [True],
            "in_opps2": [True],
            "location": ["both"],
        }
    )
    merge_summary = pd.DataFrame(
        {
            "metric": ["opportunity_df_row_count"],
            "value": [2],
        }
    )

    written_paths = write_outputs(
        opportunity_df,
        schema_comparison,
        merge_summary,
        output_dir=tmp_path,
    )
    written_names = {path.name for path in written_paths}

    expected_week1_outputs = {
        "opportunity_df.csv",
        "schema_comparison.csv",
        "merge_summary.csv",
        "duplicate_records.csv",
        "opps1_duplicate_records.csv",
        "opps2_duplicate_records.csv",
        "opps1_supplemental_detail.csv",
        "opps1_exclusive_records.csv",
        "unmatched_records.csv",
    }
    expected_sprint2_outputs = {
        "cleaned_opportunity_df.csv",
        "owner_base_summary.csv",
    }

    assert expected_week1_outputs.issubset(written_names)
    assert expected_sprint2_outputs.issubset(written_names)
    for filename in expected_week1_outputs | expected_sprint2_outputs:
        assert (tmp_path / filename).exists()

    cleaned_written = pd.read_csv(tmp_path / "cleaned_opportunity_df.csv")
    owner_summary_written = pd.read_csv(tmp_path / "owner_base_summary.csv")

    assert "source_file_flag" in cleaned_written.columns
    assert "duplicate_flag" in cleaned_written.columns
    assert "missing_revenue_flag" in cleaned_written.columns
    assert "authoritative_revenue" in cleaned_written.columns

    expected_owner_columns = {
        "opportunity_owner",
        "opportunity_count",
        "open_opportunity_count",
        "won_opportunity_count",
        "missing_probability_count",
        "missing_revenue_count",
        "missing_duration_count",
        "duplicate_count",
        "unmatched_count",
        "opps1_exclusive_count",
        "total_estimated_revenue_sum",
        "opportunity_estimated_revenue_base_cad_sum",
    }
    assert expected_owner_columns.issubset(set(owner_summary_written.columns))
    assert set(owner_summary_written["opportunity_owner"]) == {"Alice", "Bob"}


# ---------------------------------------------------------------------------
# Week 6 regression tests: CLI input workflow and RFP alias preservation
# ---------------------------------------------------------------------------


def _make_minimal_xlsx(path, sheet_name="Data", rows=None):
    """Create a minimal .xlsx fixture using openpyxl. No real CGI data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(["Opportunity ID", "Status"])
    for row in (rows or [["A001", "Open"]]):
        ws.append(row)
    wb.save(path)
    return path


def test_load_opportunity_files_raises_on_missing_files(tmp_path):
    """FileNotFoundError is raised when both input files are absent."""
    missing1 = tmp_path / "not_here_1.xlsx"
    missing2 = tmp_path / "not_here_2.xlsx"
    with pytest.raises(FileNotFoundError, match="Missing required opportunity file"):
        load_opportunity_files(opps1_path=missing1, opps2_path=missing2)


@pytest.mark.parametrize("which_missing", ["opps1", "opps2"])
def test_load_opportunity_files_error_names_missing_file(tmp_path, which_missing):
    """Error message includes the name of whichever file is missing (both positions)."""
    real = tmp_path / "real.xlsx"
    _make_minimal_xlsx(real)
    missing = tmp_path / "definitely_missing.xlsx"
    opps1 = missing if which_missing == "opps1" else real
    opps2 = missing if which_missing == "opps2" else real
    with pytest.raises(FileNotFoundError) as exc_info:
        load_opportunity_files(opps1_path=opps1, opps2_path=opps2)
    assert "definitely_missing.xlsx" in str(exc_info.value)


def test_load_opportunity_files_raises_on_missing_sheet(tmp_path):
    """ValueError is raised when the requested sheet name does not exist."""
    opps1 = tmp_path / "opps1.xlsx"
    opps2 = tmp_path / "opps2.xlsx"
    _make_minimal_xlsx(opps1, sheet_name="WrongSheet")
    _make_minimal_xlsx(opps2, sheet_name="WrongSheet")
    with pytest.raises(ValueError, match="[Ss]heet"):
        load_opportunity_files(opps1_path=opps1, opps2_path=opps2, sheet_name="Data")


def test_load_opportunity_files_accepts_custom_paths(tmp_path):
    """load_opportunity_files successfully reads two caller-supplied xlsx paths."""
    opps1 = tmp_path / "my_opps1.xlsx"
    opps2 = tmp_path / "my_opps2.xlsx"
    _make_minimal_xlsx(opps1)
    _make_minimal_xlsx(opps2)
    df1, df2 = load_opportunity_files(opps1_path=opps1, opps2_path=opps2)
    assert len(df1) == 1
    assert len(df2) == 1
    assert "Opportunity ID" in df1.columns


def test_load_opportunity_files_default_paths_match_module_constants():
    """Function signature defaults equal the module-level path constants."""
    sig = inspect.signature(load_opportunity_files)
    assert sig.parameters["opps1_path"].default == OPPS1_PATH
    assert sig.parameters["opps2_path"].default == OPPS2_PATH
    assert sig.parameters["sheet_name"].default == EXCEL_SHEET_NAME


def test_parse_args_defaults_match_module_constants(monkeypatch):
    """parse_args() with no flags returns the same defaults as module constants."""
    monkeypatch.setattr("sys.argv", ["opportunity_cleaner"])
    args = parse_args()
    assert args.opps1_path == OPPS1_PATH
    assert args.opps2_path == OPPS2_PATH
    assert args.sheet_name == EXCEL_SHEET_NAME
    assert args.output_dir == PROCESSED_DIR


def test_parse_args_accepts_custom_paths(monkeypatch, tmp_path):
    """parse_args() maps all four CLI flags to the expected Namespace attributes."""
    custom_opps1 = str(tmp_path / "client_opps1.xlsx")
    custom_opps2 = str(tmp_path / "client_opps2.xlsx")
    monkeypatch.setattr(
        "sys.argv",
        [
            "opportunity_cleaner",
            "--opps1-path", custom_opps1,
            "--opps2-path", custom_opps2,
            "--sheet-name", "ClientSheet",
            "--output-dir", str(tmp_path),
        ],
    )
    args = parse_args()
    assert args.opps1_path == Path(custom_opps1)
    assert args.opps2_path == Path(custom_opps2)
    assert args.sheet_name == "ClientSheet"
    assert args.output_dir == tmp_path


def test_clean_opportunity_df_rfp_alias_na_when_json_s_num_absent():
    """rfp_alias and has_rfp_alias are present even when json_s_num column is absent."""
    df = pd.DataFrame({"opportunity_id": ["A", "B"]})
    cleaned = clean_opportunity_df(df)
    assert "rfp_alias" in cleaned.columns, "rfp_alias must always be present"
    assert "has_rfp_alias" in cleaned.columns, "has_rfp_alias must always be present"
    assert cleaned["rfp_alias"].isna().all(), "rfp_alias should be NA when no json_s_num"
    assert list(cleaned["has_rfp_alias"]) == [False, False]

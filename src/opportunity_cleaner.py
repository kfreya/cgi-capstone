from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from src.data_validator import classify_opportunity_outcome


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CSV_DIR = DATA_DIR / "csv_files"
PROCESSED_DIR = DATA_DIR / "processed"

OPPS1_PATH = CSV_DIR / "anonymized_opps_1.xlsx"
OPPS2_PATH = CSV_DIR / "anonymized_opps_2.xlsx"
EXCEL_SHEET_NAME = "Data"
JOIN_KEY = "opportunity_id"

SUPPLEMENTAL_FIELDS = [
    "opportunity_product",
    "service_solution",
    "service_solution_estimated_revenue",
    "opportunity_estimated_revenue_base_cad",
    "ip",
    "delivery_territory_center",
    "json_s_num",
]

NUMERIC_FIELDS = [
    "probability",
    "total_estimated_revenue",
    "opportunity_estimated_revenue_base_cad",
    "service_solution_estimated_revenue",
    "project_duration_number_of_months",
]

DATE_FIELDS = [
    "created_on",
    "close_date",
    "revenue_start_date",
]

UNKNOWN_OWNER = "Unknown"


def clean_column_name(column: str) -> str:
    """Normalize a source column name to snake_case."""
    normalized = str(column).strip().lower()
    normalized = re.sub(r"\(do not modify\)", "", normalized, flags=re.IGNORECASE)
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def _make_unique_column_names(columns: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    unique_columns: list[str] = []

    for column in columns:
        count = counts.get(column, 0)
        if count == 0:
            unique_columns.append(column)
        else:
            unique_columns.append(f"{column}_{count + 1}")
        counts[column] = count + 1

    return unique_columns


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with normalized, unique column names."""
    cleaned = df.copy()
    normalized_columns = [clean_column_name(column) for column in cleaned.columns]
    cleaned.columns = _make_unique_column_names(normalized_columns)
    return cleaned


def _safe_bool_flag(df: pd.DataFrame, column: str, default: bool = False) -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype="bool")
    return df[column].fillna(default).astype(bool)


def _blank_or_missing(series: pd.Series) -> pd.Series:
    return series.isna() | series.map(
        lambda value: isinstance(value, str) and value.strip() == ""
    )


def _first_available_bool_flag(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    for column in columns:
        if column in df.columns:
            return _safe_bool_flag(df, column)
    return pd.Series(False, index=df.index, dtype="bool")


def clean_opportunity_df(opportunity_df: pd.DataFrame) -> pd.DataFrame:
    """Return a Sprint 2 cleaned/prepared copy of the merged opportunity table.

    This additive cleaning pass preserves the Week 1 merge output while adding
    downstream-friendly alias flags, basic type coercion, and lightweight data
    quality flags. Revenue hierarchy decisions remain in validation/scoring.
    """
    cleaned = opportunity_df.copy(deep=True)

    cleaned["source_file_flag"] = (
        cleaned["source_table"].fillna("unknown")
        if "source_table" in cleaned.columns
        else pd.Series("unknown", index=cleaned.index, dtype="object")
    )
    cleaned["duplicate_flag"] = _safe_bool_flag(cleaned, "is_duplicate_join_key")
    cleaned["unmatched_flag"] = _safe_bool_flag(cleaned, "is_unmatched_opps2_base")
    cleaned["opps1_exclusive_flag"] = _safe_bool_flag(cleaned, "is_opps1_exclusive")

    json_alias = (
        cleaned["json_s_num"].astype("string").str.strip()
        if "json_s_num" in cleaned.columns
        else pd.Series(pd.NA, index=cleaned.index, dtype="string")
    )
    json_alias = json_alias.mask(json_alias == "", pd.NA)
    if "rfp_alias" in cleaned.columns:
        existing_alias = cleaned["rfp_alias"].astype("string").str.strip()
        existing_alias = existing_alias.mask(existing_alias == "", pd.NA)
        cleaned["rfp_alias"] = json_alias.combine_first(existing_alias)
    else:
        cleaned["rfp_alias"] = json_alias
    cleaned["has_rfp_alias"] = cleaned["rfp_alias"].notna()

    for field in NUMERIC_FIELDS:
        if field in cleaned.columns:
            cleaned[field] = pd.to_numeric(cleaned[field], errors="coerce")

    primary_revenue = (
        cleaned["total_estimated_revenue"]
        if "total_estimated_revenue" in cleaned.columns
        else pd.Series(pd.NA, index=cleaned.index, dtype="Float64")
    )
    fallback_revenue = (
        cleaned["opportunity_estimated_revenue_base_cad"]
        if "opportunity_estimated_revenue_base_cad" in cleaned.columns
        else pd.Series(pd.NA, index=cleaned.index, dtype="Float64")
    )
    cleaned["authoritative_revenue"] = primary_revenue.combine_first(fallback_revenue)

    for field in DATE_FIELDS:
        if field in cleaned.columns:
            cleaned[field] = pd.to_datetime(cleaned[field], errors="coerce")

    cleaned["missing_owner_flag"] = (
        _blank_or_missing(cleaned["opportunity_owner"])
        if "opportunity_owner" in cleaned.columns
        else pd.Series(False, index=cleaned.index, dtype="bool")
    )

    if "probability" in cleaned.columns:
        cleaned["missing_probability_flag"] = cleaned["probability"].isna()
        cleaned["invalid_probability_flag"] = (
            (cleaned["probability"] < 0) | (cleaned["probability"] > 100)
        ).fillna(False)
    else:
        cleaned["missing_probability_flag"] = False
        cleaned["invalid_probability_flag"] = False

    revenue_fields = [
        field
        for field in [
            "total_estimated_revenue",
            "opportunity_estimated_revenue_base_cad",
        ]
        if field in cleaned.columns
    ]
    cleaned["missing_revenue_flag"] = (
        cleaned[revenue_fields].isna().all(axis=1)
        if revenue_fields
        else pd.Series(False, index=cleaned.index, dtype="bool")
    )

    if "project_duration_number_of_months" in cleaned.columns:
        duration = cleaned["project_duration_number_of_months"]
        cleaned["missing_duration_flag"] = duration.isna()
        cleaned["invalid_duration_flag"] = (duration <= 0).fillna(False)
    else:
        cleaned["missing_duration_flag"] = False
        cleaned["invalid_duration_flag"] = False

    cleaned["missing_revenue_start_date_flag"] = (
        cleaned["revenue_start_date"].isna()
        if "revenue_start_date" in cleaned.columns
        else pd.Series(False, index=cleaned.index, dtype="bool")
    )

    if {"created_on", "close_date"}.issubset(cleaned.columns):
        created_date = pd.to_datetime(
            cleaned["created_on"], errors="coerce"
        ).dt.normalize()
        close_date = pd.to_datetime(
            cleaned["close_date"], errors="coerce"
        ).dt.normalize()
        cleaned["close_before_created_flag"] = (
            close_date.notna()
            & created_date.notna()
            & (close_date < created_date)
        )
    else:
        cleaned["close_before_created_flag"] = False

    return cleaned


def build_owner_base_summary(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize cleaned opportunities by owner for Sprint 2 handoff.

    Outcome buckets use Kian's shared `classify_opportunity_outcome` taxonomy
    so CRM `Duplicated` / `Duplicate` outcomes are excluded from open/won/lost
    counts. This artifact is for validation and scoring sanity checks, not
    final capacity scoring.
    """
    work = cleaned_df.copy(deep=True)

    if "opportunity_owner" in work.columns:
        owner = work["opportunity_owner"].astype("string").str.strip()
        work["_summary_owner"] = owner.mask(
            owner.isna() | (owner == ""),
            UNKNOWN_OWNER,
        )
    else:
        work["_summary_owner"] = UNKNOWN_OWNER

    for field in ["status", "status_reason"]:
        if field not in work.columns:
            work[field] = pd.NA

    outcome = classify_opportunity_outcome(work)
    work["_open_opportunity"] = outcome == "open"
    work["_won_opportunity"] = outcome == "won"
    work["_lost_opportunity"] = outcome == "lost"

    if "probability" in work.columns:
        work["_probability"] = pd.to_numeric(work["probability"], errors="coerce")
    else:
        work["_probability"] = pd.Series(pd.NA, index=work.index, dtype="Float64")

    work["_missing_probability"] = (
        _safe_bool_flag(work, "missing_probability_flag")
        if "missing_probability_flag" in work.columns
        else work["_probability"].isna()
    )

    revenue_fields = [
        field
        for field in [
            "total_estimated_revenue",
            "opportunity_estimated_revenue_base_cad",
        ]
        if field in work.columns
    ]
    work["_missing_revenue"] = (
        _safe_bool_flag(work, "missing_revenue_flag")
        if "missing_revenue_flag" in work.columns
        else (
            work[revenue_fields].apply(pd.to_numeric, errors="coerce").isna().all(axis=1)
            if revenue_fields
            else pd.Series(False, index=work.index, dtype="bool")
        )
    )

    if "project_duration_number_of_months" in work.columns:
        duration = pd.to_numeric(
            work["project_duration_number_of_months"],
            errors="coerce",
        )
    else:
        duration = pd.Series(pd.NA, index=work.index, dtype="Float64")
    work["_missing_duration"] = (
        _safe_bool_flag(work, "missing_duration_flag")
        if "missing_duration_flag" in work.columns
        else duration.isna()
    )

    work["_duplicate"] = _first_available_bool_flag(
        work,
        ["duplicate_flag", "is_duplicate_join_key"],
    )
    work["_unmatched"] = _first_available_bool_flag(
        work,
        ["unmatched_flag", "is_unmatched_opps2_base"],
    )
    work["_opps1_exclusive"] = _first_available_bool_flag(
        work,
        ["opps1_exclusive_flag", "is_opps1_exclusive"],
    )

    for field in [
        "total_estimated_revenue",
        "opportunity_estimated_revenue_base_cad",
    ]:
        summary_field = f"_{field}"
        if field in work.columns:
            work[summary_field] = pd.to_numeric(work[field], errors="coerce")
        else:
            work[summary_field] = pd.Series(pd.NA, index=work.index, dtype="Float64")

    grouped = work.groupby("_summary_owner", dropna=False, sort=True)

    summary = pd.DataFrame(
        {
            "opportunity_count": grouped.size(),
            "open_opportunity_count": grouped["_open_opportunity"].sum().astype(int),
            "won_opportunity_count": grouped["_won_opportunity"].sum().astype(int),
            "lost_opportunity_count": grouped["_lost_opportunity"].sum().astype(int),
            "avg_probability": grouped["_probability"].mean(),
            "missing_probability_count": grouped["_missing_probability"].sum().astype(int),
            "missing_revenue_count": grouped["_missing_revenue"].sum().astype(int),
            "missing_duration_count": grouped["_missing_duration"].sum().astype(int),
            "duplicate_count": grouped["_duplicate"].sum().astype(int),
            "unmatched_count": grouped["_unmatched"].sum().astype(int),
            "opps1_exclusive_count": grouped["_opps1_exclusive"].sum().astype(int),
            "total_estimated_revenue_sum": grouped["_total_estimated_revenue"].sum(
                min_count=1
            ),
            "opportunity_estimated_revenue_base_cad_sum": grouped[
                "_opportunity_estimated_revenue_base_cad"
            ].sum(min_count=1),
        }
    ).reset_index(names="opportunity_owner")

    columns = [
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
    return summary[columns].sort_values("opportunity_owner").reset_index(drop=True)


def _format_path(path: Path) -> str:
    """Return a readable path relative to the project root when possible."""
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _read_opportunity_workbook(path: Path, sheet_name: str) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=sheet_name)
    except ValueError as exc:
        raise ValueError(
            f"Unable to read sheet {sheet_name!r} from {_format_path(path)}: {exc}"
        ) from exc


def load_opportunity_files(
    opps1_path: Path = OPPS1_PATH,
    opps2_path: Path = OPPS2_PATH,
    sheet_name: str = EXCEL_SHEET_NAME,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the local opportunity Excel workbooks."""
    opps1_path = Path(opps1_path)
    opps2_path = Path(opps2_path)
    missing_files = [path for path in [opps1_path, opps2_path] if not path.exists()]
    if missing_files:
        missing = ", ".join(_format_path(path) for path in missing_files)
        raise FileNotFoundError(f"Missing required opportunity file(s): {missing}")

    opps1 = _read_opportunity_workbook(opps1_path, sheet_name)
    opps2 = _read_opportunity_workbook(opps2_path, sheet_name)
    return opps1, opps2


def compare_schemas(opps1: pd.DataFrame, opps2: pd.DataFrame) -> pd.DataFrame:
    """Compare normalized schemas between both opportunity tables."""
    opps1_columns = set(clean_column_names(opps1).columns)
    opps2_columns = set(clean_column_names(opps2).columns)
    all_columns = sorted(opps1_columns | opps2_columns)

    records = []
    for column in all_columns:
        in_opps1 = column in opps1_columns
        in_opps2 = column in opps2_columns
        if in_opps1 and in_opps2:
            location = "both"
        elif in_opps1:
            location = "opps1_only"
        else:
            location = "opps2_only"

        records.append(
            {
                "column": column,
                "in_opps1": in_opps1,
                "in_opps2": in_opps2,
                "location": location,
            }
        )

    return pd.DataFrame(records)


def _require_join_key(df: pd.DataFrame, table_name: str) -> None:
    if JOIN_KEY not in df.columns:
        columns_preview = ", ".join(df.columns[:10])
        raise KeyError(
            f"Required join key '{JOIN_KEY}' was not found in {table_name} after "
            f"column normalization. First normalized columns: {columns_preview}"
        )


def _unique_non_null_count(series: pd.Series) -> int:
    return int(series.dropna().nunique())


def _id_set(series: pd.Series) -> set[object]:
    return set(series.dropna().unique())


def _first_non_missing(series: pd.Series) -> object:
    non_missing = series.dropna()
    if non_missing.empty:
        return pd.NA

    if pd.api.types.is_string_dtype(non_missing):
        non_missing = non_missing[non_missing.astype(str).str.strip() != ""]
    else:
        non_missing = non_missing[
            ~non_missing.map(lambda value: isinstance(value, str) and value.strip() == "")
        ]

    if non_missing.empty:
        return pd.NA

    return non_missing.iloc[0]


def collapse_supplemental_fields(
    opps1: pd.DataFrame,
    join_key: str,
    supplemental_fields: list[str],
) -> pd.DataFrame:
    """Collapse opps1 detail rows to one supplemental row per opportunity.

    opps1 may contain service/product-level detail, but opportunity_df must
    remain opportunity-level for downstream owner capacity scoring. For each
    opportunity and supplemental field, keep the first non-null, non-empty value.
    """
    if join_key not in opps1.columns:
        raise KeyError(f"Required join key '{join_key}' was not found in opps1.")

    fields_found = [field for field in supplemental_fields if field in opps1.columns]
    collapse_columns = [join_key, *fields_found]
    if not fields_found:
        return opps1[[join_key]].drop_duplicates(subset=[join_key], keep="first").copy()

    return (
        opps1[collapse_columns]
        .groupby(join_key, as_index=False, sort=False, dropna=False)
        .agg({field: _first_non_missing for field in fields_found})
    )


def _duplicate_id_count(df: pd.DataFrame) -> int:
    return int((df[JOIN_KEY].value_counts(dropna=False) > 1).sum())


def _duplicate_row_count(df: pd.DataFrame) -> int:
    return int(df[JOIN_KEY].duplicated(keep=False).sum())


def _build_merge_summary(
    opps1: pd.DataFrame,
    opps2: pd.DataFrame,
    opportunity_df: pd.DataFrame,
    supplemental_fields_found: list[str],
) -> pd.DataFrame:
    opps1_ids = _id_set(opps1[JOIN_KEY])
    opps2_ids = _id_set(opps2[JOIN_KEY])
    matched_ids = opps1_ids & opps2_ids
    opps1_exclusive_ids = opps1_ids - opps2_ids
    opps2_unmatched_ids = opps2_ids - opps1_ids
    expected_no_expansion_row_count = len(opps2) + len(opps1_exclusive_ids)

    rows = [
        ("join_key_used", JOIN_KEY),
        ("opps1_row_count", len(opps1)),
        ("opps2_row_count", len(opps2)),
        ("opps1_unique_ids", _unique_non_null_count(opps1[JOIN_KEY])),
        ("opps2_unique_ids", _unique_non_null_count(opps2[JOIN_KEY])),
        ("matched_ids", len(matched_ids)),
        ("opps1_exclusive_ids", len(opps1_exclusive_ids)),
        ("opps2_base_unmatched_ids", len(opps2_unmatched_ids)),
        ("expected_no_expansion_row_count", expected_no_expansion_row_count),
        ("opportunity_df_row_count", len(opportunity_df)),
        ("row_count_matches_no_expansion", len(opportunity_df) == expected_no_expansion_row_count),
        ("duplicate_join_key_row_count", int(opportunity_df["is_duplicate_join_key"].sum())),
        ("opps1_duplicate_id_count", _duplicate_id_count(opps1)),
        ("opps1_duplicate_row_count", _duplicate_row_count(opps1)),
        ("opps2_duplicate_id_count", _duplicate_id_count(opps2)),
        ("opps2_duplicate_row_count", _duplicate_row_count(opps2)),
        ("supplemental_fields_found", ", ".join(supplemental_fields_found)),
    ]

    return pd.DataFrame(rows, columns=["metric", "value"])


def merge_opportunity_tables(opps1: pd.DataFrame, opps2: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge opportunity tables using opps2 as the opportunity-level base.

    opps1 can contain service/product-level detail rows. It is collapsed before
    the merge so final opportunity_df does not multiply opps2 base records.
    """
    opps1_clean = clean_column_names(opps1)
    opps2_clean = clean_column_names(opps2)

    _require_join_key(opps1_clean, "opps1")
    _require_join_key(opps2_clean, "opps2")

    supplemental_fields_found = [
        field for field in SUPPLEMENTAL_FIELDS if field in opps1_clean.columns
    ]
    opps1_supplement = collapse_supplemental_fields(
        opps1_clean,
        JOIN_KEY,
        supplemental_fields_found,
    )

    opps1_ids = _id_set(opps1_clean[JOIN_KEY])
    opps2_ids = _id_set(opps2_clean[JOIN_KEY])

    base = opps2_clean.copy()
    base["source_table"] = "opps2_base"
    base["merge_status_opps2_base"] = base[JOIN_KEY].isin(opps1_ids).map(
        {True: "matched_opps1", False: "unmatched_opps2_base"}
    )
    base["is_opps1_exclusive"] = False
    base["is_unmatched_opps2_base"] = ~base[JOIN_KEY].isin(opps1_ids)

    merged_base = base.merge(
        opps1_supplement,
        on=JOIN_KEY,
        how="left",
        suffixes=("", "_opps1"),
    )

    opps1_exclusive_ids = opps1_ids - opps2_ids
    opps1_exclusive_fields = [column for column in opps1_clean.columns if column != JOIN_KEY]
    opps1_collapsed = collapse_supplemental_fields(
        opps1_clean,
        JOIN_KEY,
        opps1_exclusive_fields,
    )
    opps1_exclusive = opps1_collapsed[opps1_collapsed[JOIN_KEY].isin(opps1_exclusive_ids)].copy()
    opps1_exclusive["source_table"] = "opps1_exclusive"
    opps1_exclusive["merge_status_opps2_base"] = "opps1_exclusive"
    opps1_exclusive["is_opps1_exclusive"] = True
    opps1_exclusive["is_unmatched_opps2_base"] = False

    opportunity_df = pd.concat([merged_base, opps1_exclusive], ignore_index=True, sort=False)
    opportunity_df["is_duplicate_join_key"] = opportunity_df.duplicated(
        subset=[JOIN_KEY],
        keep=False,
    )

    diagnostic_columns = [
        "source_table",
        "merge_status_opps2_base",
        "is_duplicate_join_key",
        "is_opps1_exclusive",
        "is_unmatched_opps2_base",
    ]
    front_columns = [JOIN_KEY, *diagnostic_columns]
    remaining_columns = [column for column in opportunity_df.columns if column not in front_columns]
    opportunity_df = opportunity_df[[*front_columns, *remaining_columns]]

    merge_summary = _build_merge_summary(
        opps1_clean,
        opps2_clean,
        opportunity_df,
        supplemental_fields_found,
    )
    return opportunity_df, merge_summary


def build_opportunity_df(
    opps1_path: Path = OPPS1_PATH,
    opps2_path: Path = OPPS2_PATH,
    sheet_name: str = EXCEL_SHEET_NAME,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    """Run the full opportunity data merge pipeline."""
    opps1, opps2 = load_opportunity_files(opps1_path, opps2_path, sheet_name)
    schema_comparison = compare_schemas(opps1, opps2)
    opportunity_df, merge_summary = merge_opportunity_tables(opps1, opps2)

    opps1_clean = clean_column_names(opps1)
    opps2_clean = clean_column_names(opps2)
    supplemental_fields_found = [
        field for field in SUPPLEMENTAL_FIELDS if field in opps1_clean.columns
    ]
    audit_tables = {
        "opps1_duplicate_records": opps1_clean[opps1_clean[JOIN_KEY].duplicated(keep=False)],
        "opps2_duplicate_records": opps2_clean[opps2_clean[JOIN_KEY].duplicated(keep=False)],
        "opps1_supplemental_detail": opps1_clean[[JOIN_KEY, *supplemental_fields_found]].copy(),
    }
    return opportunity_df, schema_comparison, merge_summary, audit_tables


def write_outputs(
    opportunity_df: pd.DataFrame,
    schema_comparison: pd.DataFrame,
    merge_summary: pd.DataFrame,
    audit_tables: dict[str, pd.DataFrame] | None = None,
    output_dir: Path = PROCESSED_DIR,
) -> list[Path]:
    """Write local, ignored pipeline artifacts under data/processed."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_tables = audit_tables or {}
    cleaned_opportunity_df = clean_opportunity_df(opportunity_df)
    owner_base_summary = build_owner_base_summary(cleaned_opportunity_df)

    outputs = {
        "opportunity_df.csv": opportunity_df,
        "cleaned_opportunity_df.csv": cleaned_opportunity_df,
        "owner_base_summary.csv": owner_base_summary,
        "schema_comparison.csv": schema_comparison,
        "merge_summary.csv": merge_summary,
        "duplicate_records.csv": opportunity_df[opportunity_df["is_duplicate_join_key"]],
        "opps1_duplicate_records.csv": audit_tables.get(
            "opps1_duplicate_records",
            pd.DataFrame(),
        ),
        "opps2_duplicate_records.csv": audit_tables.get(
            "opps2_duplicate_records",
            pd.DataFrame(),
        ),
        "opps1_supplemental_detail.csv": audit_tables.get(
            "opps1_supplemental_detail",
            pd.DataFrame(),
        ),
        "opps1_exclusive_records.csv": opportunity_df[opportunity_df["is_opps1_exclusive"]],
        "unmatched_records.csv": opportunity_df[opportunity_df["is_unmatched_opps2_base"]],
    }

    written_paths = []
    for filename, df in outputs.items():
        path = output_dir / filename
        df.to_csv(path, index=False)
        written_paths.append(path)

    return written_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build merged and cleaned opportunity CSV outputs."
    )
    parser.add_argument(
        "--opps1-path",
        type=Path,
        default=OPPS1_PATH,
        help="Path to the first opportunity spreadsheet.",
    )
    parser.add_argument(
        "--opps2-path",
        type=Path,
        default=OPPS2_PATH,
        help="Path to the second opportunity spreadsheet.",
    )
    parser.add_argument(
        "--sheet-name",
        default=EXCEL_SHEET_NAME,
        help="Excel sheet name to read from both opportunity spreadsheets.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="Directory for processed opportunity CSV outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    opportunity_df, schema_comparison, merge_summary, audit_tables = build_opportunity_df(
        args.opps1_path,
        args.opps2_path,
        args.sheet_name,
    )
    written_paths = write_outputs(
        opportunity_df,
        schema_comparison,
        merge_summary,
        audit_tables,
        args.output_dir,
    )

    print("Opportunity merge complete.")
    print()
    print("Merge summary:")
    for row in merge_summary.itertuples(index=False):
        print(f"- {row.metric}: {row.value}")
    print()
    print("Local outputs written:")
    for path in written_paths:
        print(f"- {_format_path(path)}")


if __name__ == "__main__":
    main()

# Opportunity Cleaner Regression Test Notes

Owner: Kian  
Sprint: Week 6 — Client Data Replacement and Handoff Support  
Scope: `tests/test_opportunity_cleaner.py` regression coverage for the new CLI input workflow

---

## Scope

This document records the regression test coverage added in Week 6 for Yixiao's CLI
opportunity input changes (PRs #89 and #93). It is a companion to
`docs/rfp_opportunity_linkage_implementation.md`.

The tests use small synthetic fixtures created with `openpyxl`. No actual CGI
spreadsheets or generated processed outputs are committed.

---

## What Yixiao's PRs Added

| Change | Location |
| --- | --- |
| `load_opportunity_files(opps1_path, opps2_path, sheet_name)` | `src/opportunity_cleaner.py` |
| `parse_args()` with `--opps1-path`, `--opps2-path`, `--sheet-name`, `--output-dir` | `src/opportunity_cleaner.py` |
| `json_s_num` → `rfp_alias` / `has_rfp_alias` in `clean_opportunity_df` | `src/opportunity_cleaner.py` |
| `test_json_s_num_is_preserved_as_rfp_alias` | `tests/test_opportunity_cleaner.py` (Yixiao, already merged) |

---

## Coverage Added in Week 6

### `load_opportunity_files` — file path handling

| Test | Scenario | Expected |
| --- | --- | --- |
| `test_load_opportunity_files_raises_on_missing_files` | Both files absent | `FileNotFoundError` with message "Missing required opportunity file" |
| `test_load_opportunity_files_error_names_missing_file` | One file present, one absent | Error message includes the missing filename |
| `test_load_opportunity_files_raises_on_missing_sheet` | File exists but sheet name not found | `ValueError` |
| `test_load_opportunity_files_accepts_custom_paths` | Both files exist at caller-supplied paths | DataFrames load successfully |
| `test_load_opportunity_files_default_paths_match_module_constants` | No args | `inspect.signature` confirms defaults equal `OPPS1_PATH`, `OPPS2_PATH`, `EXCEL_SHEET_NAME` |

### `parse_args` — CLI argument mapping

| Test | Scenario | Expected |
| --- | --- | --- |
| `test_parse_args_defaults_match_module_constants` | No CLI flags | `Namespace` attributes equal module constants |
| `test_parse_args_accepts_custom_paths` | All four flags provided | `Namespace` attributes reflect supplied values as `Path` objects |

### `clean_opportunity_df` — RFP alias defaults

| Test | Scenario | Expected |
| --- | --- | --- |
| `test_clean_opportunity_df_rfp_alias_na_when_json_s_num_absent` | No `json_s_num` column | `rfp_alias` present and all-NA; `has_rfp_alias` all `False` |
| `test_json_s_num_is_preserved_as_rfp_alias` (Yixiao, existing) | `Json S-Num` present in opps1 | Mapped to `rfp_alias`; `has_rfp_alias` reflects presence |

---

## What Is Not Tested Here

- Orange Excel cell highlight: not used as pipeline logic, no test needed. This is
  documented in `docs/rfp_opportunity_linkage_implementation.md`.
- Capacity scoring formula: unchanged. No new tests required for scoring.
- RFP assignment ranking: unchanged. No new tests required.
- Actual CGI spreadsheet filenames: not used in any fixture.

---

## Regression Summary

All pre-existing tests in `tests/test_opportunity_cleaner.py` continue to pass
after the Week 6 additions. The new tests confirm:

1. The default no-argument workflow still resolves to the same demo file paths and
   sheet name as before the CLI changes.
2. CLI-provided paths are parsed to the correct `Namespace` attributes by `parse_args`.
3. Missing file and missing sheet conditions raise clear, informative errors that a
   CGI tester can act on.
4. `rfp_alias` and `has_rfp_alias` are always present in `cleaned_opportunity_df`,
   defaulting to NA / False when `Json S-Num` is not in the source data.

---

## Conservative Wording Reminder

`rfp_alias` / `Json S-Num` is a CRM linkage field, not validated director ownership
proof. Retrieved RFP proposal chunks are semantic evidence only. The system remains a
stakeholder-facing decision-support prototype.

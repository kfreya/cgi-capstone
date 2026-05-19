"""
Mock data for the Week 1 skeleton dashboard.

All data is synthetic — no real CGI data is used here.
Replace calls to these functions with real pipeline outputs once
Role 1/2 data and the capacity engine are ready.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

np.random.seed(42)

# ── Director roster ───────────────────────────────────────────────────────────

_DIRECTORS: list[tuple[str, str]] = [
    ("Alice Martin",  "Atlantic"),
    ("Bob Chen",      "Atlantic"),
    ("Carol Davis",   "Atlantic"),
    ("David Park",    "Media Atlantic"),
    ("Emma Wilson",   "Media Atlantic"),
    ("Frank Nguyen",  "Atlantic"),
    ("Grace Lee",     "Media Atlantic"),
    ("Henry Brooks",  "Atlantic"),
]

_SALES_STAGES = [
    "0-Lead/Suspect",
    "1-Identification",
    "2-Qualification",
    "3-Bid Planning",
    "4-Proposal",
    "5-Client Decision",
    "6-Negotiation&Signature",
]

_STATUS_LIST   = ["Open", "Won", "Lost", "Cancelled"]
_STATUS_WEIGHTS = [0.40,   0.30,  0.20,   0.10]

# ── Capacity data ─────────────────────────────────────────────────────────────
# Each row: (name, territory, hist_avg_load, relative_load)
# capacity_score = max(0, 1 - min(relative_load, 1))
# current_load   = relative_load * hist_avg_load

_RAW: list[tuple[str, str, float, float]] = [
    ("Alice Martin",  "Atlantic",       80.0, 0.28),
    ("Bob Chen",      "Atlantic",       90.0, 0.55),
    ("Carol Davis",   "Atlantic",       75.0, 0.72),
    ("David Park",    "Media Atlantic", 70.0, 0.95),
    ("Emma Wilson",   "Media Atlantic", 95.0, 1.45),
    ("Frank Nguyen",  "Atlantic",       85.0, 0.40),
    ("Grace Lee",     "Media Atlantic", 88.0, 2.20),
    ("Henry Brooks",  "Atlantic",       72.0, 0.48),
]

_OPEN_DEALS    = [4,  7,  9,  11, 13, 5,  15, 6]
_LATE_STAGE    = [1,  2,  4,  5,  6,  1,  8,  2]
_PIPELINE_REV  = [
    1_200_000, 3_400_000, 5_100_000,  6_800_000,
    9_200_000, 2_100_000, 11_500_000, 2_800_000,
]
_DELIVERIES    = [2,  3,  5,  6,  7,  2,  9,  3]
_QUARTERS_SEEN = [12, 10, 14, 8,  12, 11, 9,  13]
_RELIABILITY   = ["High", "High", "High", "Medium", "High", "High", "Medium", "High"]


def _capacity_label(relative_load: float) -> str:
    if pd.isna(relative_load):
        return "No baseline"
    if relative_load <= 0.85:
        return "Available"
    if relative_load < 1.25:
        return "Near Historical Norm"
    if relative_load < 2.0:
        return "High Load"
    return "Overextended"


def make_director_capacity_df() -> pd.DataFrame:
    """Current-period director capacity scores (mock)."""
    rows = []
    for i, (name, territory, hist_avg, rel_load) in enumerate(_RAW):
        current_load   = round(rel_load * hist_avg, 1)
        capacity_score = round(max(0.0, 1.0 - min(rel_load, 1.0)), 3)
        rows.append({
            "opportunity_owner":           name,
            "territory":                   territory,
            "historical_avg_load":         hist_avg,
            "relative_load":               round(rel_load, 3),
            "current_load":                current_load,
            "capacity_score":              capacity_score,
            "capacity_label":              _capacity_label(rel_load),
            "open_deal_count":             _OPEN_DEALS[i],
            "late_stage_deal_count":       _LATE_STAGE[i],
            "weighted_pipeline_revenue":   _PIPELINE_REV[i],
            "inferred_delivery_commitments": _DELIVERIES[i],
            "quarters_of_data":            _QUARTERS_SEEN[i],
            "baseline_reliability":        _RELIABILITY[i],
        })
    return pd.DataFrame(rows)


def make_trend_df() -> pd.DataFrame:
    """Eight-quarter workload trend per director (mock)."""
    quarters = pd.period_range(start="2024Q1", periods=8, freq="Q")
    rows = []
    for name, territory, hist_avg, current_rel in _RAW:
        current_load = current_rel * hist_avg
        for q_idx, q in enumerate(quarters):
            if q_idx == len(quarters) - 1:
                load = current_load
            else:
                noise = np.random.normal(0, hist_avg * 0.08)
                load = max(5.0, hist_avg + noise)
            rows.append({
                "opportunity_owner": name,
                "territory":         territory,
                "quarter_label":     f"Q{q.quarter} {q.year}",
                "quarter_sort":      q_idx,
                "current_load":      round(load, 2),
                "historical_avg":    hist_avg,
            })
    return pd.DataFrame(rows)

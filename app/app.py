"""
CGI Capacity Analyzer – Streamlit dashboard (Week 2).

Two pages:
  Page 1 – Director Capacity Dashboard
  Page 2 – RFP Assignment Tool

Data loading precedence:
  1. Computed live from data/processed/opportunity_df.csv via capacity_engine
  2. Pre-built data/processed/director_capacity_df.csv
  3. Synthetic mock data (app/mock_data.py)
"""

from __future__ import annotations

import html
import hashlib
import io
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Allow imports from both app/ and src/
_APP_DIR = Path(__file__).parent
_PROJECT_ROOT = _APP_DIR.parent
sys.path.insert(0, str(_APP_DIR))
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from mock_data import make_director_capacity_df, make_trend_df
from rfp_engine import generate_assignment_context

try:
    from capacity_engine import (
        assign_capacity_label,
        build_director_capacity_df,
        compute_capacity_score,
        compute_current_load_by_owner,
        compute_historical_baseline,
        compute_quarterly_workload_by_owner,
        compute_relative_load,
    )
    from data_validator import classify_opportunity_outcome
    from opportunity_cleaner import clean_opportunity_df
    _ENGINE_AVAILABLE = True
except ImportError:
    _ENGINE_AVAILABLE = False


def _extract_uploaded_rfp_text(uploaded_file) -> tuple[str, str | None]:
    """Extract text from an uploaded TXT, DOCX, or PDF file."""

    if uploaded_file is None:
        return "", None

    filename = str(getattr(uploaded_file, "name", "") or "")
    suffix = Path(filename).suffix.lower()
    data = uploaded_file.getvalue()

    if suffix == ".txt":
        return _extract_txt_upload(data)
    if suffix == ".docx":
        return _extract_docx_upload(data)
    if suffix == ".pdf":
        return _extract_pdf_upload(data)

    return "", "Unsupported file type. Upload a TXT, DOCX, or PDF file."


def _extract_txt_upload(data: bytes) -> tuple[str, str | None]:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(encoding).strip(), None
        except UnicodeDecodeError:
            continue
    return "", "Could not decode the uploaded TXT file."


def _extract_docx_upload(data: bytes) -> tuple[str, str | None]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile):
        return "", "Could not read the uploaded DOCX file."

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError:
        return "", "Could not parse the uploaded DOCX file."

    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(
            node.text or ""
            for node in paragraph.iter(f"{namespace}t")
        ).strip()
        if text:
            paragraphs.append(text)

    extracted = "\n\n".join(paragraphs).strip()
    if not extracted:
        return "", "No readable text was found in the uploaded DOCX file."
    return extracted, None


def _extract_pdf_upload(data: bytes) -> tuple[str, str | None]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "", "PDF upload requires the pypdf package in the project environment."

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [
            page.extract_text() or ""
            for page in reader.pages
        ]
    except Exception as exc:
        return "", f"Could not read the uploaded PDF file: {exc}"

    extracted = "\n\n".join(page.strip() for page in pages if page.strip()).strip()
    if not extracted:
        return "", "No readable text was found in the uploaded PDF file."
    return extracted, None

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CGI Capacity Analyzer",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand palette ─────────────────────────────────────────────────────────────
CGI_RED = "#CC0000"
APP_BG  = "#F8FAFC"

LABEL_COLORS = {
    "Available":            "#7DA0B1",
    "Near Historical Norm": "#6F6685",
    "High Load":            "#581C87",
    "Overextended":         "#991B1B",
    "No baseline":          "#475569",
}

LABEL_TINTS = {
    "Available":            "#E6F3F1",
    "Near Historical Norm": "#EFECF4",
    "High Load":            "#F1E7F8",
    "Overextended":         "#F8E7E7",
    "No baseline":          "#F1F5F9",
}

LABEL_INK = {
    "Available":            "#476A7C",
    "Near Historical Norm": "#514960",
    "High Load":            "#4C1D75",
    "Overextended":         "#7F1D1D",
    "No baseline":          "#334155",
}

LABEL_NEUTRAL = "#475569"

BRAND_PALETTE = [
    "#1E293B",
    "#334155",
    "#475569",
    "#5F7280",
    "#7DA0B1",
    "#6F6685",
    "#581C87",
    "#991B1B",
]

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  .stApp {{ background-color: {APP_BG}; }}
  [data-testid="stAppViewContainer"] > .main {{ background-color: {APP_BG}; }}

  .block-container {{
    padding-top: 4rem !important;
    padding-bottom: 2rem !important;
    max-width: 1440px;
  }}

  [data-testid="stSidebar"] > div:first-child {{
    background: #18181B;
    border-right: 1px solid #27272A;
  }}
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] div {{ color: #D4D4D8 !important; }}

  .cgi-header {{
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.3rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1.6rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }}
  .cgi-wordmark {{
    font-size: 2rem;
    font-weight: 900;
    color: {CGI_RED};
    letter-spacing: 0.12em;
    line-height: 1;
    flex-shrink: 0;
  }}
  .cgi-vdivider {{
    width: 1px;
    height: 2.4rem;
    background: #E2E8F0;
    flex-shrink: 0;
  }}
  .cgi-title-group {{ flex: 1; }}
  .cgi-page-title {{
    color: #0F172A;
    font-size: 1.3rem;
    font-weight: 700;
    margin: 0 0 0.18rem;
    letter-spacing: 0.01em;
  }}
  .cgi-page-sub {{
    color: #64748B;
    font-size: 0.77rem;
    letter-spacing: 0.025em;
  }}

  .kpi-wrap {{
    background: #fff;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }}
  .kpi-body {{ padding: 1rem 1rem 1.1rem; text-align: center; }}
  .kpi-value {{
    font-size: 2.3rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 0.25rem;
  }}
  .kpi-label {{
    font-size: 0.69rem;
    color: #78716C;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 500;
  }}

  .sec-head {{
    font-size: 0.87rem;
    font-weight: 600;
    color: #1C1917;
    margin: 1.4rem 0 0.6rem;
    padding-left: 0.65rem;
    position: relative;
    letter-spacing: 0.01em;
  }}
  .sec-head::before {{
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: #CC0000;
    border-radius: 2px;
  }}

  .chart-card {{
    background: #fff;
    border: 1px solid #EDE9E3;
    border-radius: 10px;
    padding: 0.75rem 0.75rem 0.25rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 0.75rem;
  }}

  .badge {{ border-radius: 4px; padding: 2px 9px; font-size: 0.72rem; font-weight: 600; display: inline-block; }}
  .badge-available    {{ background: {LABEL_TINTS['Available']}; color: {LABEL_INK['Available']}; }}
  .badge-nearnorm     {{ background: {LABEL_TINTS['Near Historical Norm']}; color: {LABEL_INK['Near Historical Norm']}; }}
  .badge-highload     {{ background: {LABEL_TINTS['High Load']}; color: {LABEL_INK['High Load']}; }}
  .badge-overextended {{ background: {LABEL_TINTS['Overextended']}; color: {LABEL_INK['Overextended']}; }}
  .badge-nobaseline   {{ background: {LABEL_TINTS['No baseline']}; color: {LABEL_INK['No baseline']}; }}

  .rec-card {{
    background: #fff;
    border: 1px solid #EDE9E3;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.6rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  }}
  .rec-rank      {{ font-size: 0.67rem; color: #A8A29E; text-transform: uppercase; letter-spacing: 0.07em; }}
  .rec-name      {{ font-size: 1.05rem; font-weight: 700; color: #1C1917; margin: 0.1rem 0 0.3rem; }}
  .rec-meta      {{ font-size: 0.79rem; color: #78716C; margin-bottom: 0.4rem; }}
  .rec-rationale {{ font-size: 0.81rem; color: #44403C; line-height: 1.6; }}

  .effort-high   {{ background: #F8E7E7; color: #7F1D1D; border-radius: 5px; padding: 3px 12px; font-weight: 700; font-size: 0.83rem; }}
  .effort-medium {{ background: #F1E7F8; color: #4C1D75; border-radius: 5px; padding: 3px 12px; font-weight: 700; font-size: 0.83rem; }}
  .effort-low    {{ background: #EAF2F6; color: #476A7C; border-radius: 5px; padding: 3px 12px; font-weight: 700; font-size: 0.83rem; }}

  .pipeline-box {{
    background: #F5F2EC;
    border: 1px solid #E7E2D8;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    font-size: 0.8rem;
    color: #57534E;
    line-height: 2.1;
  }}

  .data-banner {{
    border-radius: 6px;
    padding: 0.4rem 1rem;
    font-size: 0.78rem;
    margin-bottom: 1.1rem;
  }}
  .data-banner-real {{
    background: #ECFDF5;
    border: 1px solid #A7F3D0;
    color: #065F46;
  }}
  .data-banner-mock {{
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    color: #92400E;
  }}

  .table-wrap {{
    max-height: 600px;
    overflow: auto;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background: #FFFFFF;
  }}
  .table-wrap table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.76rem;
  }}
  .table-wrap th {{
    position: sticky;
    top: 0;
    z-index: 1;
    background: #F8FAFC;
    color: #334155;
    font-weight: 700;
    text-align: left;
    padding: 0.55rem 0.65rem;
    border-bottom: 1px solid #E2E8F0;
  }}
  .table-wrap td {{
    padding: 0.5rem 0.65rem;
    border-bottom: 1px solid #EEF2F7;
    color: #334155;
    vertical-align: top;
  }}
  .table-wrap tr:last-child td {{ border-bottom: 0; }}

  [data-testid="stExpander"] {{
    background: #fff !important;
    border: 1px solid #EDE9E3 !important;
    border-radius: 8px !important;
    margin-bottom: 1rem;
  }}

  ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
  ::-webkit-scrollbar-track {{ background: #F5F2EC; }}
  ::-webkit-scrollbar-thumb {{ background: #C9C0B5; border-radius: 3px; }}
</style>
""", unsafe_allow_html=True)

# ── Shared chart defaults ─────────────────────────────────────────────────────
_CHART_FONT  = dict(family="Inter, system-ui, sans-serif", size=12, color="#1C1917")
_CHART_PAPER = "rgba(0,0,0,0)"
_CHART_PLOT  = "rgba(0,0,0,0)"
_GRID_COLOR  = "#E2E8F0"

_HOVER = dict(
    bgcolor="#FFFFFF",
    bordercolor="#E7E2D8",
    font=dict(family="Inter, system-ui, sans-serif", size=12, color="#1C1917"),
)

# ── Data loading ──────────────────────────────────────────────────────────────

def _build_trend_from_opportunity_df(
    opp_df: pd.DataFrame,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Build last-8-quarter workload trend from active-quarter engine output."""
    df = opp_df.copy()
    trend = compute_quarterly_workload_by_owner(df, as_of_date=as_of_date)
    if trend.empty:
        return pd.DataFrame(
            columns=[
                "opportunity_owner",
                "territory",
                "quarter_label",
                "quarter_sort",
                "current_load",
                "historical_avg",
            ]
        )

    hist_avg = (
        trend.groupby("opportunity_owner")
        .agg(historical_avg=("current_load", "mean"))
        .reset_index()
    )
    trend = trend.merge(hist_avg, on="opportunity_owner", how="left")

    territory = (
        df.groupby("opportunity_owner")["delivery_territory_center"]
        .first()
        .reset_index()
        .rename(columns={"delivery_territory_center": "territory"})
    )
    trend = trend.merge(territory, on="opportunity_owner", how="left")

    # Keep last 8 quarters only, matching chart heading
    max_sort = trend["quarter_sort"].max()
    trend = trend[trend["quarter_sort"] >= (max_sort - 7)]

    return trend.sort_values(["opportunity_owner", "quarter_sort"]).reset_index(drop=True)


def _select_options(df: pd.DataFrame | None, column: str) -> list[str]:
    if df is None or column not in df.columns:
        return ["All"]
    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )
    return ["All"] + sorted(v for v in values.unique() if v)


def _filter_by_status(work: pd.DataFrame, selected: str) -> pd.DataFrame:
    if selected == "All" or work.empty:
        return work

    outcomes = classify_opportunity_outcome(work)
    reason = work["status_reason"].astype("string").str.strip().str.lower().fillna("")
    cancelled = reason.str.startswith(("cancelled", "canceled")).fillna(False)

    if selected == "Cancelled":
        return work[cancelled]
    if selected == "Lost":
        return work[outcomes.eq("lost") & ~cancelled]
    return work[outcomes.eq(selected.lower())]


def _filter_opportunities(
    opp_df: pd.DataFrame,
    *,
    territory: str,
    owner: str,
    status: str,
    sales_stage: str,
    date_range: object,
    opportunity_type: str,
    sales_model: str,
) -> pd.DataFrame:
    work = opp_df.copy()

    if territory != "All" and "delivery_territory_center" in work.columns:
        work = work[work["delivery_territory_center"].eq(territory)]
    if owner != "All" and "opportunity_owner" in work.columns:
        work = work[work["opportunity_owner"].eq(owner)]
    if sales_stage != "All" and "sales_stage" in work.columns:
        work = work[work["sales_stage"].eq(sales_stage)]
    if opportunity_type != "All" and "opportunity_type" in work.columns:
        work = work[work["opportunity_type"].eq(opportunity_type)]
    if sales_model != "All" and "sales_model" in work.columns:
        work = work[work["sales_model"].eq(sales_model)]

    work = _filter_by_status(work, status)

    if "created_on" in work.columns and isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        if start is not None and end is not None:
            created = pd.to_datetime(work["created_on"], errors="coerce").dt.date
            work = work[(created >= start) & (created <= end)]

    return work


def _baseline_population(
    opp_df: pd.DataFrame,
    *,
    territory: str,
    owner: str,
) -> pd.DataFrame:
    work = opp_df.copy()
    if territory != "All" and "delivery_territory_center" in work.columns:
        work = work[work["delivery_territory_center"].eq(territory)]
    if owner != "All" and "opportunity_owner" in work.columns:
        work = work[work["opportunity_owner"].eq(owner)]
    return work


def _build_capacity_from_filtered_current(
    current_opp_df: pd.DataFrame,
    baseline_opp_df: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    current_df = compute_current_load_by_owner(current_opp_df)
    baseline_df = compute_historical_baseline(
        baseline_opp_df,
        as_of_date=as_of_date,
    )
    out = compute_relative_load(current_df, baseline_df)
    out = compute_capacity_score(out)
    out = assign_capacity_label(out)
    return out


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None, str, str | None]:
    """Load capacity data. Returns capacity, trend, opportunity rows, source, warning.

    warning is None on success or a short error description when the preferred
    source failed and mock data was used instead.
    """
    cleaned_path = _PROJECT_ROOT / "data" / "processed" / "cleaned_opportunity_df.csv"
    opp_path = _PROJECT_ROOT / "data" / "processed" / "opportunity_df.csv"
    prebuilt  = _PROJECT_ROOT / "data" / "processed" / "director_capacity_df.csv"

    # Option 1: compute live from preferred cleaned data, or clean raw data.
    if _ENGINE_AVAILABLE and (cleaned_path.exists() or opp_path.exists()):
        try:
            as_of_date = pd.Timestamp.today().normalize()
            if cleaned_path.exists():
                opp_df = pd.read_csv(cleaned_path, low_memory=False)
            else:
                opp_df = clean_opportunity_df(pd.read_csv(opp_path, low_memory=False))
            cap_df = build_director_capacity_df(
                opp_df,
                current_date=as_of_date,
            )
            trd_df = _build_trend_from_opportunity_df(
                opp_df,
                as_of_date=as_of_date,
            )
            return cap_df, trd_df, opp_df, "real", None
        except Exception as exc:
            _live_err = f"Live scoring failed ({type(exc).__name__}: {exc})"
    else:
        _live_err = None

    # Option 2: pre-built CSV
    if prebuilt.exists():
        try:
            as_of_date = pd.Timestamp.today().normalize()
            cap_df = pd.read_csv(prebuilt)
            opp_df = None
            if _ENGINE_AVAILABLE and (cleaned_path.exists() or opp_path.exists()):
                if cleaned_path.exists():
                    opp_df = pd.read_csv(cleaned_path, low_memory=False)
                else:
                    opp_df = clean_opportunity_df(pd.read_csv(opp_path, low_memory=False))
                trd_df = _build_trend_from_opportunity_df(
                    opp_df,
                    as_of_date=as_of_date,
                )
            else:
                trd_df = make_trend_df()
            warning = _live_err  # surface live-scoring error even though we recovered
            return cap_df, trd_df, opp_df, "prebuilt", warning
        except Exception as exc:
            _prebuilt_err = f"Pre-built CSV failed ({type(exc).__name__}: {exc})"
    else:
        _prebuilt_err = None

    # Option 3: mock — build a combined warning so the operator can diagnose
    parts = [e for e in [_live_err, _prebuilt_err] if e]
    warning = "; ".join(parts) if parts else "Real data unavailable — mock data shown."
    return make_director_capacity_df(), make_trend_df(), None, "mock", warning


capacity_df, trend_df, opportunity_df, _data_source, _load_warning = load_data()

# Normalise baseline_reliability: bool True/False → "Reliable"/"Limited"
if capacity_df["baseline_reliability"].dtype == bool or capacity_df["baseline_reliability"].isin([True, False]).all():
    capacity_df["baseline_reliability"] = capacity_df["baseline_reliability"].map(
        {True: "Reliable", False: "Limited"}
    ).fillna("Limited")

# ── Sidebar ───────────────────────────────────────────────────────────────────
PAGE_OPTIONS = ["Director Capacity Dashboard", "RFP Assignment Tool"]
if "page_nav" not in st.session_state:
    st.session_state["page_nav"] = PAGE_OPTIONS[0]

with st.sidebar:
    st.markdown(
        "<div style='padding:0.6rem 0 2rem'>"
        "  <div style='font-size:1.7rem;font-weight:900;color:#CC0000;letter-spacing:0.1em'>CGI</div>"
        "  <div style='font-size:0.72rem;color:#71717A;margin-top:0.1rem;letter-spacing:0.04em'>Capacity Analyzer</div>"
        "  <div style='margin-top:1rem;height:2px;"
        "    background:linear-gradient(90deg,#991B1B,#7DA0B1);border-radius:2px;width:36px'></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    page = st.radio(
        "nav",
        PAGE_OPTIONS,
        key="page_nav",
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color:#27272A;margin:1.5rem 0 1.2rem'>", unsafe_allow_html=True)

    _src_color = "#4ADE80" if _data_source == "real" else "#FBB040"
    _src_label = {
        "real":     "Live CRM data",
        "prebuilt": "Pre-built CSV",
        "mock":     "Synthetic mock data",
    }[_data_source]

    st.markdown(
        "<div style='font-size:0.69rem;color:#52525B;line-height:1.9'>"
        "Scope: CGI Atlantic · Media Atlantic<br>"
        "Source: CRM opportunity records<br>"
        f"<br><span style='color:{_src_color};font-weight:600'>● {_src_label}</span>"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="cgi-header">
      <div class="cgi-wordmark">CGI</div>
      <div class="cgi-vdivider"></div>
      <div class="cgi-title-group">
        <div class="cgi-page-title">{page}</div>
        <div class="cgi-page-sub">CGI Atlantic · Media Atlantic Business Unit · Week 4 Final Prototype</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Data source banner ────────────────────────────────────────────────────────
if _data_source == "real":
    st.markdown(
        "<div class='data-banner data-banner-real'>"
        "<b>Live data</b> — Director capacity scores computed from CRM opportunity records "
        f"({len(capacity_df)} owners)."
        "</div>",
        unsafe_allow_html=True,
    )
elif _data_source == "prebuilt":
    st.markdown(
        "<div class='data-banner data-banner-real'>"
        "<b>Pre-built data</b> — Loaded from <code>director_capacity_df.csv</code>. "
        "Re-run the capacity engine to refresh."
        "</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div class='data-banner data-banner-mock'>Displaying <b>synthetic mock data</b> — "
        "real pipeline outputs replace this once the capacity engine and merged "
        "opportunity data are integrated.</div>",
        unsafe_allow_html=True,
    )

if _load_warning:
    st.warning(f"Data loading fell back to a lower-priority source. Details: {_load_warning}")


# ==============================================================================
#  PAGE 1 – Director Capacity Dashboard
# ==============================================================================
if page == "Director Capacity Dashboard":

    row_filters_available = opportunity_df is not None and _ENGINE_AVAILABLE
    created_dates = (
        pd.to_datetime(opportunity_df["created_on"], errors="coerce").dropna()
        if row_filters_available and "created_on" in opportunity_df.columns
        else pd.Series(dtype="datetime64[ns]")
    )
    if not created_dates.empty:
        created_min = created_dates.min().date()
        created_max = created_dates.max().date()
        created_default = ()
    else:
        created_min = created_max = pd.Timestamp.today().date()
        created_default = ()

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("Filters", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            territories = (
                _select_options(opportunity_df, "delivery_territory_center")
                if row_filters_available
                else ["All"] + sorted(capacity_df["territory"].dropna().unique())
            )
            sel_territory = st.selectbox("Territory", territories)
        with fc2:
            owners = (
                _select_options(opportunity_df, "opportunity_owner")
                if row_filters_available
                else ["All"] + sorted(capacity_df["opportunity_owner"].dropna().unique())
            )
            sel_owner = st.selectbox("Opportunity Owner", owners)
        with fc3:
            labels = [
                "All",
                "Available",
                "Near Historical Norm",
                "High Load",
                "Overextended",
                "No baseline",
            ]
            sel_label = st.selectbox("Capacity Label", labels)
        with fc4:
            sel_status = st.selectbox(
                "Status",
                ["All", "Open", "Won", "Lost", "Cancelled", "Duplicate"],
                disabled=not row_filters_available,
                help=None if row_filters_available else "Requires live opportunity data",
            )

        fc5, fc6, fc7, fc8 = st.columns(4)
        with fc5:
            sel_sales_stage = st.selectbox(
                "Sales Stage",
                _select_options(opportunity_df, "sales_stage"),
                disabled=not row_filters_available,
                help=None if row_filters_available else "Requires live opportunity data",
            )
        with fc6:
            sel_date_range = st.date_input(
                "Created Date Range",
                value=created_default,
                min_value=created_min,
                max_value=created_max,
                disabled=not row_filters_available or created_dates.empty,
                help=None if row_filters_available else "Requires live opportunity data",
            )
        with fc7:
            sel_opportunity_type = st.selectbox(
                "Opportunity Type",
                _select_options(opportunity_df, "opportunity_type"),
                disabled=not row_filters_available,
                help=None if row_filters_available else "Requires live opportunity data",
            )
        with fc8:
            sel_sales_model = st.selectbox(
                "Sales Model",
                _select_options(opportunity_df, "sales_model"),
                disabled=not row_filters_available,
                help=None if row_filters_available else "Requires live opportunity data",
            )

    if row_filters_available:
        filtered_opp_df = _filter_opportunities(
            opportunity_df,
            territory=sel_territory,
            owner=sel_owner,
            status=sel_status,
            sales_stage=sel_sales_stage,
            date_range=sel_date_range,
            opportunity_type=sel_opportunity_type,
            sales_model=sel_sales_model,
        )
        if filtered_opp_df.empty:
            fdf = capacity_df.iloc[0:0].copy()
            active_trend_df = trend_df.iloc[0:0].copy()
        else:
            as_of_date = pd.Timestamp.today().normalize()
            baseline_opp_df = _baseline_population(
                opportunity_df,
                territory=sel_territory,
                owner=sel_owner,
            )
            fdf = _build_capacity_from_filtered_current(
                filtered_opp_df,
                baseline_opp_df,
                as_of_date,
            )
            active_trend_df = _build_trend_from_opportunity_df(
                filtered_opp_df,
                as_of_date=as_of_date,
            )
    else:
        fdf = capacity_df.copy()
        active_trend_df = trend_df
        if sel_territory != "All":
            fdf = fdf[fdf["territory"] == sel_territory]
        if sel_owner != "All":
            fdf = fdf[fdf["opportunity_owner"] == sel_owner]

    if sel_label != "All":
        fdf = fdf[fdf["capacity_label"] == sel_label]

    if fdf.empty:
        st.info("No directors match the selected filters. Adjust the filters above.")
        st.stop()

    # ── KPI row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    kpi_cfg = [
        ("Directors",      len(fdf), "#222222"),
        ("Available",      (fdf["capacity_label"] == "Available").sum(), LABEL_COLORS["Available"]),
        ("Near Norm",      (fdf["capacity_label"] == "Near Historical Norm").sum(), LABEL_COLORS["Near Historical Norm"]),
        ("High Load",      (fdf["capacity_label"] == "High Load").sum(), LABEL_COLORS["High Load"]),
        ("Overextended",   (fdf["capacity_label"] == "Overextended").sum(), LABEL_COLORS["Overextended"]),
        ("No baseline",    (fdf["capacity_label"] == "No baseline").sum(), LABEL_COLORS["No baseline"]),
    ]
    for col, (label, val, color) in zip([k1, k2, k3, k4, k5, k6], kpi_cfg):
        col.markdown(
            f"<div class='kpi-wrap'>"
            f"  <div class='kpi-body'>"
            f"    <div class='kpi-value' style='color:{color}'>{val}</div>"
            f"    <div class='kpi-label'>{label}</div>"
            f"  </div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Score explanation ─────────────────────────────────────────────────────
    with st.expander("How is the Relative Load calculated?", expanded=False):
        st.markdown(
            """
**Relative Load** = `current_load / historical_avg_load`

| Relative load range | Label | Meaning |
|---|---|---|
| ≤ 0.85x | **Available** | Director is below their historical workload norm |
| > 0.85x and < 1.25x | **Near Historical Norm** | Director is close to their historical workload norm |
| ≥ 1.25x and < 2.00x | **High Load** | Director is materially above historical norm |
| ≥ 2.00x | **Overextended** | Director is carrying at least double historical norm |
| missing baseline | **No baseline** | Director has no usable historical denominator |

**Current Load** combines two components:
- *Sales load* — active open opportunities weighted by sales stage, win probability, estimated revenue, and project duration
- *Delivery load* — active won delivery commitments based on revenue start date, close date fallback, project duration, and monthly revenue

**Historical Average Load** = mean quarterly load across the director's full
selected owner/territory history. Row-level filters such as status, sales stage,
opportunity type, sales model, and created date change the current workload
being viewed; they do not redefine the historical baseline.

Workload score uses logarithmic revenue terms so very large opportunities affect
load without fully dominating the scale:

`current_load = sales_load + delivery_load`

`sales_load = stage_weight × probability × log1p(revenue) × duration_weight`

`duration_weight = log1p(duration_months) / log1p(12)`

`delivery_load = log1p(revenue / duration_months)` for active won deliveries

These label bands are a temporary project calibration based on the current
director-level distribution and business interpretation of load vs historical
norm. They should be reviewed and adjusted with CGI judgment.

> Scores are based on anonymized CRM opportunity records. Missing revenue, dates, or
> probability fields are handled using documented fallback assumptions.
""",
            unsafe_allow_html=False,
        )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Row 1: Relative load bars  |  Label donut ────────────────────────────
    col_bars, col_donut = st.columns([3, 1.1])

    with col_bars:
        st.markdown('<div class="sec-head">Relative Load by Director</div>', unsafe_allow_html=True)

        sdf = fdf.sort_values("relative_load", ascending=True, na_position="first")

        rel_display = sdf["relative_load"].fillna(0).values
        text_display = [
            "  No baseline" if pd.isna(v) else f"  {v:.2f}x"
            for v in sdf["relative_load"]
        ]
        max_rel = pd.to_numeric(sdf["relative_load"], errors="coerce").max()
        x_max = max(2.25, float(max_rel) * 1.08) if pd.notna(max_rel) else 2.25

        fig_bar = go.Figure()
        customdata = np.column_stack([
            rel_display,
            sdf["current_load"].fillna(0).values,
            sdf["historical_avg_load"].fillna(0).values,
            sdf["capacity_label"].values,
        ])

        fig_bar.add_trace(go.Bar(
            y=sdf["opportunity_owner"],
            x=rel_display,
            orientation="h",
            marker_color=[LABEL_COLORS.get(l, LABEL_NEUTRAL) for l in sdf["capacity_label"]],
            marker_line_width=0,
            text=text_display,
            textposition="outside",
            textfont=dict(size=11, color="#57534E", family="Inter"),
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Relative Load: %{customdata[0]:.2f}x<br>"
                "Current Load: %{customdata[1]:.2f}<br>"
                "Historical Avg: %{customdata[2]:.2f}<br>"
                "Label: %{customdata[3]}<extra></extra>"
            ),
        ))

        n_owners = len(sdf)
        bar_height = max(260, n_owners * 25 + 32)

        fig_bar.update_layout(
            height=bar_height,
            margin=dict(l=0, r=80, t=8, b=14),
            paper_bgcolor=_CHART_PAPER,
            plot_bgcolor=_CHART_PLOT,
            xaxis=dict(
                title=dict(
                    text="Relative Load",
                    font=dict(size=11, color="#78716C"),
                    standoff=4,
                ),
                tickformat=".1f",
                ticksuffix="x",
                range=[0, x_max],
                gridcolor=_GRID_COLOR,
                showgrid=True,
                zeroline=False,
                showline=False,
                tickfont=dict(size=10, color="#78716C"),
            ),
            yaxis=dict(title="", tickfont=dict(size=11, color="#1C1917"), showgrid=False),
            font=_CHART_FONT,
            hoverlabel=_HOVER,
            showlegend=False,
        )
        st.plotly_chart(fig_bar, width="stretch", config={"displayModeBar": False})

    with col_donut:
        st.markdown('<div class="sec-head">Label Mix</div>', unsafe_allow_html=True)

        lc = fdf["capacity_label"].value_counts().reset_index()
        lc.columns = ["label", "count"]
        total_dirs = int(lc["count"].sum())

        fig_donut = go.Figure(go.Pie(
            labels=lc["label"],
            values=lc["count"],
            hole=0.66,
            marker=dict(
                colors=[LABEL_COLORS.get(l, "#aaa") for l in lc["label"]],
                line=dict(color=APP_BG, width=3),
            ),
            textinfo="none",
            texttemplate="%{value}",
            textposition="inside",
            insidetextorientation="horizontal",
            textfont=dict(size=13, color="#FFFFFF", family="Inter"),
            hovertemplate="<b>%{label}</b><br>%{value} directors (%{percent})<extra></extra>",
            sort=False,
            direction="clockwise",
        ))

        fig_donut.add_annotation(
            text=(f"<b style='font-size:24px;color:#222222'>{total_dirs}</b><br>"
                  "<span style='font-size:9px;color:#78716C;letter-spacing:1.5px'>"
                  "DIRECTORS</span>"),
            x=0.5, y=0.5, showarrow=False, align="center",
        )

        fig_donut.update_layout(
            height=bar_height,
            margin=dict(l=0, r=0, t=8, b=8),
            paper_bgcolor=_CHART_PAPER,
            showlegend=False,
            font=_CHART_FONT,
            hoverlabel=_HOVER,
            uniformtext=dict(minsize=12, mode="show"),
        )
        st.plotly_chart(fig_donut, width="stretch", config={"displayModeBar": False})

    # ── Row 2: Current load vs historical average ─────────────────────────────
    st.markdown('<div class="sec-head">Current Load vs Historical Average</div>', unsafe_allow_html=True)

    ldf = fdf.sort_values("relative_load", ascending=False, na_position="last").reset_index(drop=True)
    load_floor = 0.01
    ldf["_current_load_display"] = (
        pd.to_numeric(ldf["current_load"], errors="coerce")
        .clip(lower=load_floor)
    )
    ldf["_historical_avg_display"] = (
        pd.to_numeric(ldf["historical_avg_load"], errors="coerce")
        .clip(lower=load_floor)
    )
    fig_load = go.Figure()
    fig_load.add_trace(go.Bar(
        name="Current Load",
        x=ldf["opportunity_owner"],
        y=ldf["_current_load_display"],
        marker_color=[LABEL_COLORS.get(l, LABEL_NEUTRAL) for l in ldf["capacity_label"]],
        marker_line_width=0,
        customdata=np.column_stack([
            ldf["current_load"].fillna(0),
            ldf["historical_avg_load"].fillna(0),
            ldf["relative_load"].fillna(0),
            ldf["capacity_label"],
        ]),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Current Load: %{customdata[0]:.4f}<br>"
            "Historical Avg: %{customdata[1]:.4f}<br>"
            "Relative Load: %{customdata[2]:.2f}x<br>"
            "Label: %{customdata[3]}<extra></extra>"
        ),
    ))

    _AVG_INK = "#44403C"
    avg_marker_df = ldf[ldf["historical_avg_load"].notna()].copy()
    fig_load.add_trace(go.Scatter(
        x=avg_marker_df["opportunity_owner"],
        y=avg_marker_df["_historical_avg_display"],
        mode="markers",
        marker=dict(
            symbol="line-ew",
            size=28,
            color=_AVG_INK,
            line=dict(color=_AVG_INK, width=3),
        ),
        name="Historical Avg",
        customdata=np.column_stack([
            avg_marker_df["current_load"].fillna(0),
            avg_marker_df["historical_avg_load"].fillna(0),
            avg_marker_df["relative_load"].fillna(0),
        ]),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Current Load: %{customdata[0]:.4f}<br>"
            "Historical Avg: %{customdata[1]:.4f}<br>"
            "Relative Load: %{customdata[2]:.2f}x<extra></extra>"
        ),
    ))

    fig_load.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=8, b=60),
        paper_bgcolor=_CHART_PAPER,
        plot_bgcolor=_CHART_PLOT,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=11, color="#57534E"), bgcolor="rgba(0,0,0,0)",
        ),
        yaxis=dict(
            title=dict(text="Workload Score (log scale)", font=dict(size=11, color="#78716C")),
            type="log",
            gridcolor=_GRID_COLOR, zeroline=False, showline=False,
            tickfont=dict(size=10, color="#78716C"),
        ),
        xaxis=dict(
            title="",
            showgrid=False,
            tickfont=dict(size=11, color="#1C1917"),
            tickangle=0 if len(ldf) <= 6 else -35,
        ),
        font=_CHART_FONT,
        bargap=0.42,
        hoverlabel=_HOVER,
    )
    st.plotly_chart(fig_load, width="stretch", config={"displayModeBar": False})

    # ── Row 3: Trend  |  Director table ──────────────────────────────────────
    col_trend, col_table = st.columns([1.6, 2.4])

    with col_trend:
        st.markdown('<div class="sec-head">Workload Trend — Last 8 Quarters</div>', unsafe_allow_html=True)

        trend_owners = (
            [sel_owner] if sel_owner != "All"
            else fdf["opportunity_owner"].tolist()
        )
        tdf = (
            active_trend_df[active_trend_df["opportunity_owner"].isin(trend_owners)]
            .sort_values("quarter_sort")
        )

        fig_trend = go.Figure()
        for idx, owner in enumerate(trend_owners):
            odf = tdf[tdf["opportunity_owner"] == owner]
            if odf.empty:
                continue
            color = BRAND_PALETTE[idx % len(BRAND_PALETTE)]
            trend_display = (
                pd.to_numeric(odf["current_load"], errors="coerce")
                .clip(lower=load_floor)
            )
            fig_trend.add_trace(go.Scatter(
                x=odf["quarter_label"],
                y=trend_display,
                name=owner,
                mode="lines+markers",
                line=dict(color=color, width=2.5, shape="spline", smoothing=1.1),
                marker=dict(size=6, color=color, line=dict(color=APP_BG, width=1.5)),
                customdata=odf["current_load"],
                hovertemplate=f"<b>{owner}</b><br>%{{x}}: %{{customdata:.2f}}<extra></extra>",
            ))

        if not fig_trend.data:
            fig_trend.add_annotation(
                x=0.5, y=0.5, xref="paper", yref="paper",
                text="No trend data for selected owner",
                showarrow=False,
                font=dict(size=13, color="#94A3B8"),
            )

        fig_trend.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=8, b=10),
            paper_bgcolor=_CHART_PAPER,
            plot_bgcolor=_CHART_PLOT,
            legend=dict(
                font=dict(size=9, color="#57534E"),
                bgcolor="rgba(0,0,0,0)",
                borderwidth=0,
            ),
            yaxis=dict(
                title=dict(text="Workload Score (log scale)", font=dict(size=11, color="#78716C")),
                type="log",
                gridcolor=_GRID_COLOR, zeroline=False, showline=False,
                tickfont=dict(size=10, color="#78716C"),
            ),
            xaxis=dict(
                title="", tickangle=-35,
                tickfont=dict(size=10, color="#78716C"), showgrid=False,
            ),
            font=_CHART_FONT,
            hoverlabel=_HOVER,
        )
        st.plotly_chart(fig_trend, width="stretch", config={"displayModeBar": False})

    with col_table:
        st.markdown('<div class="sec-head">Director Summary</div>', unsafe_allow_html=True)

        display = fdf[[
            "opportunity_owner", "territory", "capacity_label", "relative_load",
            "open_deal_count", "late_stage_deal_count",
            "weighted_pipeline_revenue", "inferred_delivery_commitments",
            "baseline_reliability",
        ]].copy()

        # relative_load: show as "2.3x" — reveals overextension severity when score = 0
        display["relative_load"] = display["relative_load"].apply(
            lambda x: f"{x:.1f}x" if pd.notna(x) else "—"
        )
        display["territory"] = display["territory"].fillna("Unknown")
        display["weighted_pipeline_revenue"] = display["weighted_pipeline_revenue"].apply(
            lambda x: f"${x / 1_000_000:.1f}M" if pd.notna(x) else "—"
        )
        display.columns = [
            "Director", "Territory", "Label", "Rel. Load",
            "Open Deals", "Late-Stage", "Pipeline (CAD)",
            "Active Deliveries", "Baseline",
        ]
        st.markdown(
            f"<div class='table-wrap'>{display.to_html(index=False, escape=True)}</div>",
            unsafe_allow_html=True,
        )


# ==============================================================================
#  PAGE 2 – RFP Assignment Tool
# ==============================================================================
elif page == "RFP Assignment Tool":
    rfp_capacity_source_label = {
        "real": "Live CRM capacity data",
        "prebuilt": "Pre-built director_capacity_df.csv",
        "mock": "Synthetic mock capacity data",
    }.get(_data_source, "Unknown capacity data source")

    st.markdown(
        "<div style='background:#F5F2EC;border:1px solid #E7E2D8;border-radius:8px;"
        "padding:0.75rem 1.1rem;margin-bottom:1.2rem;font-size:0.82rem;color:#57534E'>"
        "<b>Week 4 Final Prototype — RFP Assignment Tool</b><br>"
        "<span style='color:#92400E'>Retrieval:</span> active mode is shown after "
        "analysis (Azure/Chroma when available, local fallback otherwise). &nbsp;"
        "<span style='color:#065F46'>Capacity data:</span> real director capacity scores when available. &nbsp;"
        "<span style='color:#57534E'>Recommendations:</span> prototype guidance only — "
        "not final CGI assignment decisions."
        "</div>",
        unsafe_allow_html=True,
    )

    col_input, col_results = st.columns([1, 1.5], gap="large")

    with col_input:
        st.markdown('<div class="sec-head">RFP Input</div>', unsafe_allow_html=True)

        uploaded_rfp_file = st.file_uploader(
            "Upload RFP document",
            type=["pdf", "docx", "txt"],
            help="Upload a TXT, DOCX, or text-based PDF. You can still paste RFP text directly below.",
        )
        if uploaded_rfp_file is not None:
            uploaded_bytes = uploaded_rfp_file.getvalue()
            upload_signature = (
                f"{uploaded_rfp_file.name}:"
                f"{hashlib.sha256(uploaded_bytes).hexdigest()}"
            )
            if st.session_state.get("rfp_uploaded_file_signature") != upload_signature:
                extracted_text, upload_error = _extract_uploaded_rfp_text(uploaded_rfp_file)
                st.session_state["rfp_uploaded_file_signature"] = upload_signature
                if upload_error:
                    st.session_state["rfp_upload_error"] = upload_error
                    st.session_state.pop("rfp_upload_success", None)
                else:
                    st.session_state["rfp_input_text"] = extracted_text
                    st.session_state["rfp_upload_success"] = (
                        f"Loaded text from {uploaded_rfp_file.name}."
                    )
                    st.session_state.pop("rfp_upload_error", None)

        if st.session_state.get("rfp_upload_success"):
            st.success(st.session_state["rfp_upload_success"])
        if st.session_state.get("rfp_upload_error"):
            st.warning(st.session_state["rfp_upload_error"])
        st.caption("Upload a supported document or paste RFP text directly below.")

        rfp_text = st.text_area(
            "RFP text",
            height=220,
            label_visibility="collapsed",
            placeholder="Paste the full RFP text here…",
            key="rfp_input_text",
        )

        fc1, fc2 = st.columns(2)
        with fc1:
            st.selectbox("Territory", ["Any", "Atlantic", "Media Atlantic"])
        with fc2:
            st.selectbox("Service Domain", [
                "Any", "IT Consulting", "Managed Services",
                "Data & Analytics", "Cloud & Infrastructure", "Application Services",
            ])

        st.caption("Territory and service domain are UI context only for now; backend scoring does not use them yet.")

        analyze_clicked = st.button("Analyze RFP", type="primary", width="stretch")
        if analyze_clicked:
            rfp_text = st.session_state.get("rfp_input_text", "")
            if not rfp_text.strip():
                st.session_state.pop("rfp_assignment_context", None)
                st.session_state.pop("rfp_assignment_input", None)
                st.session_state.pop("rfp_capacity_data_source", None)
                st.warning("Please paste RFP text before running the analysis.")
            else:
                try:
                    # Pass the same capacity table used by the dashboard so
                    # RFP recommendations use real/local capacity signals when available.
                    st.session_state["rfp_assignment_context"] = generate_assignment_context(
                        rfp_text,
                        director_df=capacity_df,
                    )
                    st.session_state["rfp_assignment_input"] = rfp_text
                    st.session_state["rfp_capacity_data_source"] = {
                        "source": _data_source,
                        "label": rfp_capacity_source_label,
                        "is_mock": _data_source == "mock",
                    }
                    st.session_state.pop("rfp_assignment_error", None)
                except Exception as exc:
                    st.session_state["rfp_assignment_error"] = str(exc)
                    st.session_state.pop("rfp_assignment_context", None)

    with col_results:
        _ph = (
            f"background:{APP_BG};border:1.5px dashed #D6CFC8;border-radius:8px;"
            "padding:1.5rem 1.25rem;margin-bottom:0.75rem;text-align:center;"
            "color:#A8A29E;font-size:0.82rem;"
        )
        context = st.session_state.get("rfp_assignment_context")
        _engine_error = st.session_state.get("rfp_assignment_error")

        if _engine_error:
            st.error(
                f"The RFP assignment pipeline encountered an error: {_engine_error}\n\n"
                "The local fallback path should not fail under normal conditions. "
                "Check that the project dependencies are installed and try again."
            )

        if not context:
            st.markdown('<div class="sec-head">Estimated Effort</div>', unsafe_allow_html=True)
            st.markdown(
                f"<div style='{_ph}'>Effort level and estimated duration will appear here<br>"
                "<span style='font-size:0.72rem'>"
                "Source: <code>generate_assignment_context()</code> → <code>effort</code></span></div>",
                unsafe_allow_html=True,
            )

            st.markdown('<div class="sec-head">Similar Historical RFPs</div>', unsafe_allow_html=True)
            st.markdown(
                f"<div style='{_ph}'>Retrieved RFP chunks and their retrieval mode will appear here<br>"
                "<span style='font-size:0.72rem'>"
                "Source: <code>generate_assignment_context()</code> → <code>retrieved_examples</code></span></div>",
                unsafe_allow_html=True,
            )

            st.markdown('<div class="sec-head">Recommended Directors</div>', unsafe_allow_html=True)
            st.markdown(
                f"<div style='{_ph}'>Ranked director recommendations with capacity, experience,<br>"
                "and assignment scores will appear here<br>"
                "<span style='font-size:0.72rem'>"
                "Source: <code>generate_assignment_context()</code> → <code>recommended_directors</code></span></div>",
                unsafe_allow_html=True,
            )

            st.markdown('<div class="sec-head">Risk Flags</div>', unsafe_allow_html=True)
            st.markdown(
                f"<div style='{_ph}'>Low-confidence matches, capacity conflicts, or data-quality warnings will appear here<br>"
                "<span style='font-size:0.72rem'>"
                "Source: <code>generate_assignment_context()</code> → <code>risk_flags</code></span></div>",
                unsafe_allow_html=True,
            )
        else:
            capacity_source = st.session_state.get("rfp_capacity_data_source") or {
                "source": _data_source,
                "label": rfp_capacity_source_label,
                "is_mock": _data_source == "mock",
            }
            capacity_source_label = str(capacity_source.get("label") or rfp_capacity_source_label)
            retrieval_mode = str(context.get("retrieval_mode") or "unknown")
            retrieval_mode_label = {
                "azure_chroma": "Azure/Chroma retrieval active",
                "local_fallback": "Local fallback retrieval active",
            }.get(retrieval_mode, "Retrieval mode unavailable")
            _retrieval_note = f"Retrieval: {retrieval_mode_label}."
            st.info(f"**Retrieval mode** — {retrieval_mode_label}.")
            if capacity_source.get("is_mock"):
                st.warning(
                    f"**Prototype output — heuristic recommendations using synthetic mock capacity data.** "
                    f"Do not treat as final CGI assignment guidance. {_retrieval_note}"
                )
            else:
                st.info(
                    f"**Prototype output** — capacity-aware recommendations using {capacity_source_label}. "
                    f"{_retrieval_note}"
                )
            retrieval_status = context.get("retrieval_status") or {}
            if isinstance(retrieval_status, dict):
                if retrieval_status.get("chroma_build_skipped"):
                    st.caption(
                        "Azure/Chroma rebuild skipped for this full-corpus dashboard request; "
                        "using local retrieval over the same corpus."
                    )
                elif retrieval_status.get("preferred_path_error"):
                    st.caption(
                        "Preferred retrieval path fell back after an error: "
                        f"{retrieval_status.get('preferred_path_error')}"
                    )
                elif retrieval_mode == "azure_chroma":
                    st.caption("Azure/Chroma retrieval is active for this result.")
                corpus_source = str(retrieval_status.get("corpus_source") or "")
                corpus_label = {
                    "proposal_corpus": "local proposals_responses.json corpus",
                    "provided_chunks": "provided historical chunk corpus",
                    "sample_corpus": "default sample historical corpus",
                }.get(corpus_source)
                if corpus_label:
                    st.caption(
                        "Retrieval corpus: "
                        f"{corpus_label}; "
                        f"{retrieval_status.get('corpus_chunk_count', 'n/a')} corpus chunks; "
                        f"{retrieval_status.get('query_chunk_count', 'n/a')} pasted-RFP query chunks."
                    )
                if retrieval_status.get("retrieval_has_director_linkage") is False:
                    st.caption(
                        "Retrieved chunks do not include reliable opportunity_owner/opportunity_id "
                        "linkage, so they are semantic evidence rather than proof of director experience."
                    )

            st.markdown('<div class="sec-head">RFP Summary</div>', unsafe_allow_html=True)
            st.write(context.get("rfp_summary") or "No summary returned.")

            effort = context.get("effort") or {}
            if not isinstance(effort, dict):
                effort = {}
            effort_level = str(effort.get("level") or "Unknown")
            effort_class = f"effort-{effort_level.lower()}" if effort_level in {"Low", "Medium", "High"} else "badge"

            st.markdown('<div class="sec-head">Estimated Effort</div>', unsafe_allow_html=True)
            st.markdown(
                f"<span class='{effort_class}'>{html.escape(effort_level)}</span>",
                unsafe_allow_html=True,
            )
            if effort.get("estimated_duration"):
                st.caption(f"Estimated duration: {effort.get('estimated_duration')}")
            effort_reason = effort.get("reason") or effort.get("rationale")
            st.write(effort_reason or "No effort reason returned.")

            retrieved_examples = context.get("retrieved_examples") or []
            st.markdown('<div class="sec-head">Similar Historical RFPs</div>', unsafe_allow_html=True)
            if not isinstance(retrieved_examples, list) or not retrieved_examples:
                st.info("No retrieved examples returned.")
            else:
                for index, example in enumerate(retrieved_examples, start=1):
                    if not isinstance(example, dict):
                        continue
                    supporting_text = str(example.get("supporting_text") or "")
                    preview = supporting_text[:320].rstrip()
                    if len(supporting_text) > 320:
                        preview = f"{preview}..."
                    raw_score = example.get("similarity_score")
                    try:
                        score_str = f"{float(raw_score):.2f}"
                    except (TypeError, ValueError):
                        score_str = str(raw_score) if raw_score not in (None, "") else "n/a"
                    st.markdown(
                        f"**{index}. {example.get('proposal_id', 'Unknown proposal')}**  \n"
                        f"`chunk_id`: `{example.get('chunk_id', 'unknown')}`  \n"
                        f"`similarity_score`: `{score_str}`"
                    )
                    st.write(preview or "No supporting text returned.")

            recommended_directors = context.get("recommended_directors") or []
            st.markdown('<div class="sec-head">Recommended Directors</div>', unsafe_allow_html=True)
            if not isinstance(recommended_directors, list) or not recommended_directors:
                st.info("No recommended directors returned.")
            else:
                for index, director in enumerate(recommended_directors, start=1):
                    if not isinstance(director, dict):
                        continue
                    with st.expander(
                        f"{index}. {director.get('director_name', 'Unnamed director')}",
                        expanded=index == 1,
                    ):
                        st.markdown(
                            f"**Capacity:** {director.get('capacity_label', 'Unknown')}  \n"
                            f"**Capacity score:** {director.get('capacity_score', 'n/a')}  \n"
                            f"**Relative load:** {director.get('relative_load', 'n/a')}  \n"
                            f"**Assignment score:** {director.get('assignment_score', 'n/a')}"
                        )
                        if director.get("match_reason"):
                            st.write(director.get("match_reason"))
                        if director.get("capacity_explanation"):
                            st.markdown("**Capacity explanation**")
                            st.write(director.get("capacity_explanation"))
                        if director.get("experience_match_explanation"):
                            st.markdown("**Experience match explanation**")
                            st.write(director.get("experience_match_explanation"))
                        supporting_chunks = director.get("supporting_chunks") or []
                        if supporting_chunks:
                            st.caption(
                                "Supporting chunks: "
                                + ", ".join(str(chunk_id) for chunk_id in supporting_chunks)
                            )

            risk_flags = context.get("risk_flags") or []
            st.markdown('<div class="sec-head">Risk Flags</div>', unsafe_allow_html=True)
            if not isinstance(risk_flags, list) or not risk_flags:
                st.info("No risk flags returned.")
            else:
                for flag in risk_flags:
                    if isinstance(flag, dict):
                        level = str(flag.get("level", "Info")).strip()
                        message = flag.get("message", "")
                        display_text = f"**{level}:** {message}" if message else f"**{level}**"
                        if level == "High":
                            st.error(display_text)
                        elif level == "Medium":
                            st.warning(display_text)
                        else:
                            st.info(display_text)
                    else:
                        st.warning(str(flag))

            if context.get("notes"):
                st.markdown('<div class="sec-head">Notes</div>', unsafe_allow_html=True)
                st.caption(str(context.get("notes")))

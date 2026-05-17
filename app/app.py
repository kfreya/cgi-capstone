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

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Allow imports from both app/ and src/
_APP_DIR = Path(__file__).parent
_PROJECT_ROOT = _APP_DIR.parent
sys.path.insert(0, str(_APP_DIR))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from mock_data import make_director_capacity_df, make_trend_df

try:
    from capacity_engine import (
        build_director_capacity_df,
        compute_quarterly_workload_by_owner,
    )
    from opportunity_cleaner import clean_opportunity_df
    _ENGINE_AVAILABLE = True
except ImportError:
    _ENGINE_AVAILABLE = False

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
    "Available":    "#7DA0B1",
    "At Capacity":  "#581C87",
    "Overextended": "#991B1B",
}

LABEL_TINTS = {
    "Available":    "#EAF2F6",
    "At Capacity":  "#F1E7F8",
    "Overextended": "#F8E7E7",
}

LABEL_INK = {
    "Available":    "#476A7C",
    "At Capacity":  "#4C1D75",
    "Overextended": "#7F1D1D",
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
  .badge-available    {{ background: {LABEL_TINTS['Available']};    color: {LABEL_INK['Available']}; }}
  .badge-atcapacity   {{ background: {LABEL_TINTS['At Capacity']};  color: {LABEL_INK['At Capacity']}; }}
  .badge-overextended {{ background: {LABEL_TINTS['Overextended']}; color: {LABEL_INK['Overextended']}; }}

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


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, str, str | None]:
    """Load capacity data. Returns (capacity_df, trend_df, source_label, warning).

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
                opp_df = pd.read_csv(cleaned_path)
            else:
                opp_df = clean_opportunity_df(pd.read_csv(opp_path))
            cap_df = build_director_capacity_df(
                opp_df,
                current_date=as_of_date,
            )
            trd_df = _build_trend_from_opportunity_df(
                opp_df,
                as_of_date=as_of_date,
            )
            return cap_df, trd_df, "real", None
        except Exception as exc:
            _live_err = f"Live scoring failed ({type(exc).__name__}: {exc})"
    else:
        _live_err = None

    # Option 2: pre-built CSV
    if prebuilt.exists():
        try:
            as_of_date = pd.Timestamp.today().normalize()
            cap_df = pd.read_csv(prebuilt)
            if _ENGINE_AVAILABLE and (cleaned_path.exists() or opp_path.exists()):
                if cleaned_path.exists():
                    opp_df = pd.read_csv(cleaned_path)
                else:
                    opp_df = clean_opportunity_df(pd.read_csv(opp_path))
                trd_df = _build_trend_from_opportunity_df(
                    opp_df,
                    as_of_date=as_of_date,
                )
            else:
                trd_df = make_trend_df()
            warning = _live_err  # surface live-scoring error even though we recovered
            return cap_df, trd_df, "prebuilt", warning
        except Exception as exc:
            _prebuilt_err = f"Pre-built CSV failed ({type(exc).__name__}: {exc})"
    else:
        _prebuilt_err = None

    # Option 3: mock — build a combined warning so the operator can diagnose
    parts = [e for e in [_live_err, _prebuilt_err] if e]
    warning = "; ".join(parts) if parts else "Real data unavailable — mock data shown."
    return make_director_capacity_df(), make_trend_df(), "mock", warning


capacity_df, trend_df, _data_source, _load_warning = load_data()

# Normalise baseline_reliability: bool True/False → "Reliable"/"Limited"
if capacity_df["baseline_reliability"].dtype == bool or capacity_df["baseline_reliability"].isin([True, False]).all():
    capacity_df["baseline_reliability"] = capacity_df["baseline_reliability"].map(
        {True: "Reliable", False: "Limited"}
    ).fillna("Limited")

# ── Sidebar ───────────────────────────────────────────────────────────────────
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
        ["Director Capacity Dashboard", "RFP Assignment Tool"],
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
        <div class="cgi-page-sub">CGI Atlantic · Media Atlantic Business Unit · Week 2 Prototype</div>
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

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("Filters", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            territory_vals = sorted(capacity_df["territory"].dropna().unique())
            territories = ["All"] + territory_vals
            sel_territory = st.selectbox("Territory", territories)
        with fc2:
            owners = ["All"] + sorted(capacity_df["opportunity_owner"].dropna().unique())
            sel_owner = st.selectbox("Opportunity Owner", owners)
        with fc3:
            labels = ["All", "Available", "At Capacity", "Overextended"]
            sel_label = st.selectbox("Capacity Label", labels)
        with fc4:
            st.selectbox(
                "Status",
                ["All", "Open", "Won", "Lost", "Cancelled"],
                disabled=True,
                help="Available once opportunity_df filtering is connected",
            )

        fc5, fc6, fc7, fc8 = st.columns(4)
        with fc5:
            st.selectbox(
                "Sales Stage",
                ["All", "0-Lead/Suspect", "1-Identification", "2-Qualification",
                 "3-Bid Planning", "4-Proposal", "5-Client Decision", "6-Negotiation&Signature"],
                disabled=True,
                help="Available once opportunity_df filtering is connected",
            )
        with fc6:
            st.date_input(
                "Date Range",
                value=[],
                disabled=True,
                help="Available once opportunity_df filtering is connected",
            )
        with fc7:
            st.selectbox(
                "Opportunity Type",
                ["All", "New Business", "Extension", "Renewal", "Change Request"],
                disabled=True,
                help="Available once opportunity_df filtering is connected",
            )
        with fc8:
            st.selectbox(
                "Sales Model",
                ["All", "Direct", "Partner", "Framework", "Public Sector Tender"],
                disabled=True,
                help="Available once opportunity_df filtering is connected",
            )

    fdf = capacity_df.copy()
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
    k1, k2, k3, k4 = st.columns(4)
    kpi_cfg = [
        ("Directors",    len(fdf),                                        "#222222"),
        ("Available",    (fdf["capacity_label"] == "Available").sum(),    LABEL_COLORS["Available"]),
        ("At Capacity",  (fdf["capacity_label"] == "At Capacity").sum(),  LABEL_COLORS["At Capacity"]),
        ("Overextended", (fdf["capacity_label"] == "Overextended").sum(), LABEL_COLORS["Overextended"]),
    ]
    for col, (label, val, color) in zip([k1, k2, k3, k4], kpi_cfg):
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
    with st.expander("How is the Capacity Score calculated?", expanded=False):
        st.markdown(
            """
**Capacity Score** = `max(0, 1 − min(relative_load, 1))`

| Score range | Label | Meaning |
|---|---|---|
| ≥ 0.35 | **Available** | Director has meaningful room for new work |
| 0.15 – 0.34 | **At Capacity** | Director is near their historical average load |
| < 0.15 | **Overextended** | Director's current load exceeds their historical norm |

**Relative Load** = `current_load / historical_avg_load`

**Current Load** combines two components:
- *Sales load* — weighted by sales stage, win probability, estimated revenue, and project duration
- *Delivery load* — active inferred deliveries based on revenue start date and project duration

**Historical Average Load** = mean quarterly load across all quarters in the CRM data.

> Scores are based on anonymized CRM opportunity records. Missing revenue, dates, or
> probability fields are handled using documented fallback assumptions.
""",
            unsafe_allow_html=False,
        )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Row 1: Capacity score bars  |  Label donut ───────────────────────────
    col_bars, col_donut = st.columns([3, 1.1])

    with col_bars:
        st.markdown('<div class="sec-head">Capacity Score by Director</div>', unsafe_allow_html=True)

        sdf = fdf.sort_values("capacity_score", na_position="first")

        # Safe display values — NaN scores shown as 0 in chart (labeled At Capacity by engine)
        score_display = sdf["capacity_score"].fillna(0).values
        rel_display   = sdf["relative_load"].fillna(0).values

        fig_bar = go.Figure()
        customdata = np.column_stack([
            score_display,
            rel_display,
            sdf["capacity_label"].values,
        ])

        fig_bar.add_trace(go.Bar(
            y=sdf["opportunity_owner"],
            x=score_display,
            orientation="h",
            marker_color=[LABEL_COLORS.get(l, LABEL_COLORS["At Capacity"]) for l in sdf["capacity_label"]],
            marker_line_width=0,
            text=[f"  {v:.0%}" for v in score_display],
            textposition="outside",
            textfont=dict(size=11, color="#57534E", family="Inter"),
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Capacity Score: %{customdata[0]:.0%}<br>"
                "Relative Load: %{customdata[1]:.0%}<br>"
                "Label: %{customdata[2]}<extra></extra>"
            ),
        ))

        zero_sdf = sdf[sdf["capacity_score"].fillna(0) == 0]
        if not zero_sdf.empty:
            zero_customdata = np.column_stack([
                zero_sdf["capacity_score"].fillna(0).values,
                zero_sdf["relative_load"].fillna(0).values,
                zero_sdf["capacity_label"].values,
            ])
            fig_bar.add_trace(go.Scatter(
                y=zero_sdf["opportunity_owner"],
                x=[0] * len(zero_sdf),
                mode="markers",
                marker=dict(opacity=0, size=16),
                customdata=zero_customdata,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Capacity Score: %{customdata[0]:.0%}<br>"
                    "Relative Load: %{customdata[1]:.0%}<br>"
                    "Label: %{customdata[2]}<extra></extra>"
                ),
                showlegend=False,
            ))

        for x_val, color in [(0.35, LABEL_COLORS["Available"]),
                             (0.15, LABEL_COLORS["Overextended"])]:
            fig_bar.add_shape(
                type="line",
                x0=x_val, x1=x_val, y0=0, y1=1, yref="paper",
                line=dict(dash="2,4", color=color, width=1),
            )

        fig_bar.add_annotation(
            x=0.36, xref="x", y=0.04, yref="paper",
            text="Available ≥ 35%",
            showarrow=False, xanchor="left", yanchor="bottom",
            font=dict(size=9, color=LABEL_COLORS["Available"], family="Inter"),
            bgcolor="rgba(248,250,252,0.90)",
            borderpad=3, borderwidth=0,
        )
        fig_bar.add_annotation(
            x=0.16, xref="x", y=0.12, yref="paper",
            text="Overextended < 15%",
            showarrow=False, xanchor="left", yanchor="bottom",
            font=dict(size=9, color=LABEL_COLORS["Overextended"], family="Inter"),
            bgcolor="rgba(248,250,252,0.90)",
            borderpad=4, borderwidth=0,
        )

        n_owners = len(sdf)
        bar_height = max(260, n_owners * 25 + 32)

        fig_bar.update_layout(
            height=bar_height,
            margin=dict(l=0, r=80, t=8, b=14),
            paper_bgcolor=_CHART_PAPER,
            plot_bgcolor=_CHART_PLOT,
            xaxis=dict(
                title=dict(
                    text="Capacity Score",
                    font=dict(size=11, color="#78716C"),
                    standoff=4,
                ),
                tickformat=".0%",
                range=[0, 1.05],
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
            textinfo="value",
            textposition="outside",
            textfont=dict(size=11, color="#44403C", family="Inter"),
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
        )
        st.plotly_chart(fig_donut, width="stretch", config={"displayModeBar": False})

    # ── Row 2: Current load vs historical average ─────────────────────────────
    st.markdown('<div class="sec-head">Current Load vs Historical Average</div>', unsafe_allow_html=True)

    ldf = fdf.sort_values("current_load", ascending=False).reset_index(drop=True)
    fig_load = go.Figure()
    fig_load.add_trace(go.Bar(
        name="Current Load",
        x=ldf["opportunity_owner"],
        y=ldf["current_load"],
        marker_color=[LABEL_COLORS.get(l, LABEL_COLORS["At Capacity"]) for l in ldf["capacity_label"]],
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Current Load: %{y:.1f}<extra></extra>",
    ))

    _AVG_INK = "#44403C"
    for xi, row in ldf.iterrows():
        fig_load.add_shape(
            type="line",
            x0=xi - 0.32, x1=xi + 0.32,
            y0=row["historical_avg_load"], y1=row["historical_avg_load"],
            line=dict(color=_AVG_INK, width=2.5),
        )
    fig_load.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color=_AVG_INK, width=2.5),
        name="Historical Avg",
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
            title=dict(text="Workload Score", font=dict(size=11, color="#78716C")),
            gridcolor=_GRID_COLOR, zeroline=False, showline=False,
            tickfont=dict(size=10, color="#78716C"),
        ),
        xaxis=dict(title="", showgrid=False, tickfont=dict(size=11, color="#1C1917"), tickangle=-35),
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
            trend_df[trend_df["opportunity_owner"].isin(trend_owners)]
            .sort_values("quarter_sort")
        )

        fig_trend = go.Figure()
        for idx, owner in enumerate(trend_owners):
            odf = tdf[tdf["opportunity_owner"] == owner]
            if odf.empty:
                continue
            color = BRAND_PALETTE[idx % len(BRAND_PALETTE)]
            fig_trend.add_trace(go.Scatter(
                x=odf["quarter_label"],
                y=odf["current_load"],
                name=owner,
                mode="lines+markers",
                line=dict(color=color, width=2.5, shape="spline", smoothing=1.1),
                marker=dict(size=6, color=color, line=dict(color=APP_BG, width=1.5)),
                hovertemplate=f"<b>{owner}</b><br>%{{x}}: %{{y:.1f}}<extra></extra>",
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
                title=dict(text="Workload Score", font=dict(size=11, color="#78716C")),
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
            "opportunity_owner", "territory", "capacity_label", "capacity_score",
            "relative_load",
            "open_deal_count", "late_stage_deal_count",
            "weighted_pipeline_revenue", "inferred_delivery_commitments",
            "baseline_reliability",
        ]].copy()

        display["capacity_score"] = display["capacity_score"].fillna(0)
        display["capacity_score"] = (display["capacity_score"] * 100).round(1)
        # relative_load: show as "2.3x" — reveals overextension severity when score = 0
        display["relative_load"] = display["relative_load"].apply(
            lambda x: f"{x:.1f}x" if pd.notna(x) else "—"
        )
        display["territory"] = display["territory"].fillna("Unknown")
        display["weighted_pipeline_revenue"] = display["weighted_pipeline_revenue"].apply(
            lambda x: f"${x / 1_000_000:.1f}M" if pd.notna(x) else "—"
        )
        display.columns = [
            "Director", "Territory", "Label", "Score (%)", "Rel. Load",
            "Open Deals", "Late-Stage", "Pipeline (CAD)",
            "Active Deliveries", "Baseline",
        ]
        tbl_height = max(290, min(len(display) * 35 + 40, 600))
        st.dataframe(display, width="stretch", hide_index=True, height=tbl_height)


# ==============================================================================
#  PAGE 2 – RFP Assignment Tool  (UI shell — backend owned by Jai / Role 5)
# ==============================================================================
elif page == "RFP Assignment Tool":

    st.markdown(
        "<div style='background:#F5F2EC;border:1px solid #E7E2D8;border-radius:8px;"
        "padding:0.75rem 1.1rem;margin-bottom:1.2rem;font-size:0.82rem;color:#57534E'>"
        "This page is the <b>UI shell</b> for the RFP Assignment Tool. "
        "The backend pipeline (chunking, embeddings, retrieval, director ranking) "
        "is being built by <b>Jai (Role 5)</b> in "
        "<code>src/rfp_preprocessor.py</code> and <code>src/vector_store.py</code>. "
        "Jai's <code>generate_assignment_context()</code> output will plug into the results panel below."
        "</div>",
        unsafe_allow_html=True,
    )

    col_input, col_results = st.columns([1, 1.5], gap="large")

    with col_input:
        st.markdown('<div class="sec-head">RFP Input</div>', unsafe_allow_html=True)

        st.file_uploader(
            "Upload RFP document",
            type=["pdf", "docx", "txt"],
            disabled=True,
            help="Available once RFP document parsing is connected (Role 5)",
        )

        st.text_area(
            "RFP text",
            height=220,
            label_visibility="collapsed",
            placeholder="Paste the full RFP text here…",
        )

        fc1, fc2 = st.columns(2)
        with fc1:
            st.selectbox("Territory", ["Any", "Atlantic", "Media Atlantic"])
        with fc2:
            st.selectbox("Service Domain", [
                "Any", "IT Consulting", "Managed Services",
                "Data & Analytics", "Cloud & Infrastructure", "Application Services",
            ])

        st.button("Analyze RFP", type="primary", width="stretch", disabled=True)
        st.caption("Backend not connected — enable once Jai's pipeline is integrated.")

    with col_results:
        _ph = (
            f"background:{APP_BG};border:1.5px dashed #D6CFC8;border-radius:8px;"
            "padding:1.5rem 1.25rem;margin-bottom:0.75rem;text-align:center;"
            "color:#A8A29E;font-size:0.82rem;"
        )

        st.markdown('<div class="sec-head">Estimated Effort</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Effort level and estimated duration will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: <code>generate_assignment_context()</code> → <code>effort</code></span></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-head">Similar Historical RFPs</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Retrieved RFP chunks ranked by semantic similarity will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: <code>retrieve_relevant_chunks()</code> → <code>retrieved_examples</code></span></div>",
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

        st.markdown('<div class="sec-head">Capacity Explanation</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Capacity rationale for each recommended director will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: <code>recommended_directors[].capacity_label</code> + score</span></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-head">Experience Match Explanation</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Relevant past work, similarity evidence, and fit rationale will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: <code>recommended_directors[].match_reason</code> + supporting chunks</span></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-head">Risk Flags</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Low-confidence matches, capacity conflicts, or data-quality warnings will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: <code>generate_assignment_context()</code> → <code>risk_flags</code></span></div>",
            unsafe_allow_html=True,
        )

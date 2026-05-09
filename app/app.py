"""
CGI Capacity Analyzer – Streamlit dashboard skeleton (Week 1).

Two pages:
  Page 1 – Director Capacity Dashboard
  Page 2 – RFP Assignment Tool

Mock data is loaded from app/mock_data.py.
Replace load_data() with real pipeline outputs once Role 1/2 data and the
capacity engine are integrated.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from mock_data import (
    make_director_capacity_df,
    make_trend_df,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CGI Capacity Analyzer",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand palette ─────────────────────────────────────────────────────────────
# Brand anchors.
CGI_RED = "#CC0000"
APP_BG  = "#F8FAFC"

# Semantic status colors — CGI-aligned consulting severity scale.
# Available is light steel blue, at-capacity is muted purple, overextended is CGI red.
LABEL_COLORS = {
    "Available":    "#7DA0B1",
    "At Capacity":  "#581C87",
    "Overextended": "#991B1B",
}

# Light tints — for badge backgrounds.
LABEL_TINTS = {
    "Available":    "#EAF2F6",
    "At Capacity":  "#F1E7F8",
    "Overextended": "#F8E7E7",
}

# Deep accents — for badge text (high-contrast on the tints above).
LABEL_INK = {
    "Available":    "#476A7C",
    "At Capacity":  "#4C1D75",
    "Overextended": "#7F1D1D",
}

LABEL_NEUTRAL = "#475569"

# Trend-chart palette — muted enterprise accents.
BRAND_PALETTE = [
    "#1E293B",   # slate-800
    "#334155",   # slate-700
    "#475569",   # slate-600
    "#5F7280",   # blue-gray
    "#7DA0B1",   # severity blue
    "#6F6685",   # muted violet-gray
    "#581C87",   # severity purple
    "#991B1B",   # severity red
]

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* ── Page background (cool gray) ── */
  .stApp {{ background-color: {APP_BG}; }}
  [data-testid="stAppViewContainer"] > .main {{ background-color: {APP_BG}; }}

  /* ── Block container: must leave room for Streamlit's top toolbar (~3.5 rem) ── */
  .block-container {{
    padding-top: 4rem !important;
    padding-bottom: 2rem !important;
    max-width: 1440px;
  }}

  /* ── Sidebar ── */
  [data-testid="stSidebar"] > div:first-child {{
    background: #18181B;
    border-right: 1px solid #27272A;
  }}
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] div {{ color: #D4D4D8 !important; }}

  /* ── Header ── */
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

  /* ── KPI card ── */
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

  /* ── Section headings (gradient left rule) ── */
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

  /* ── Chart wrapper card ── */
  .chart-card {{
    background: #fff;
    border: 1px solid #EDE9E3;
    border-radius: 10px;
    padding: 0.75rem 0.75rem 0.25rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 0.75rem;
  }}

  /* ── Capacity label badges (tints harmonised with new chart palette) ── */
  .badge {{ border-radius: 4px; padding: 2px 9px; font-size: 0.72rem; font-weight: 600; display: inline-block; }}
  .badge-available    {{ background: {LABEL_TINTS['Available']};    color: {LABEL_INK['Available']}; }}
  .badge-atcapacity   {{ background: {LABEL_TINTS['At Capacity']};  color: {LABEL_INK['At Capacity']}; }}
  .badge-overextended {{ background: {LABEL_TINTS['Overextended']}; color: {LABEL_INK['Overextended']}; }}

  /* ── RFP recommendation cards ── */
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

  /* ── Effort level badges ── */
  .effort-high   {{ background: #F8E7E7; color: #7F1D1D; border-radius: 5px; padding: 3px 12px; font-weight: 700; font-size: 0.83rem; }}
  .effort-medium {{ background: #F1E7F8; color: #4C1D75; border-radius: 5px; padding: 3px 12px; font-weight: 700; font-size: 0.83rem; }}
  .effort-low    {{ background: #EAF2F6; color: #476A7C; border-radius: 5px; padding: 3px 12px; font-weight: 700; font-size: 0.83rem; }}

  /* ── Pipeline steps box ── */
  .pipeline-box {{
    background: #F5F2EC;
    border: 1px solid #E7E2D8;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    font-size: 0.8rem;
    color: #57534E;
    line-height: 2.1;
  }}

  /* ── Mock data banner ── */
  .mock-banner {{
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    border-radius: 6px;
    padding: 0.4rem 1rem;
    font-size: 0.78rem;
    color: #92400E;
    margin-bottom: 1.1rem;
  }}

  /* ── Expander ── */
  [data-testid="stExpander"] {{
    background: #fff !important;
    border: 1px solid #EDE9E3 !important;
    border-radius: 8px !important;
    margin-bottom: 1rem;
  }}

  /* ── Scrollbar ── */
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

# Hoverlabel style — used everywhere so tooltips feel like part of the same product.
_HOVER = dict(
    bgcolor="#FFFFFF",
    bordercolor="#E7E2D8",
    font=dict(family="Inter, system-ui, sans-serif", size=12, color="#1C1917"),
)

# ── Data ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    return make_director_capacity_df(), make_trend_df()

capacity_df, trend_df = load_data()

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
    st.markdown(
        "<div style='font-size:0.69rem;color:#52525B;line-height:1.9'>"
        "Scope: CGI Atlantic · Media Atlantic<br>"
        "Source: CRM opportunity records<br>"
        "<br><span style='color:#CC0000;font-weight:600'>⚠ Week 1 – mock data</span>"
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
        <div class="cgi-page-sub">CGI Atlantic · Media Atlantic Business Unit · Week 1 Prototype</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Mock data banner ──────────────────────────────────────────────────────────
st.markdown(
    "<div class='mock-banner'>⚠ Displaying <b>synthetic mock data</b> — "
    "real pipeline outputs replace this once the capacity engine and merged "
    "opportunity data are integrated.</div>",
    unsafe_allow_html=True,
)


# ==============================================================================
#  PAGE 1 – Director Capacity Dashboard
# ==============================================================================
if page == "Director Capacity Dashboard":

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("Filters", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            territories = ["All"] + sorted(capacity_df["territory"].unique())
            sel_territory = st.selectbox("Territory", territories)
        with fc2:
            owners = ["All"] + sorted(capacity_df["opportunity_owner"].unique())
            sel_owner = st.selectbox("Opportunity Owner", owners)
        with fc3:
            labels = ["All", "Available", "At Capacity", "Overextended"]
            sel_label = st.selectbox("Capacity Label", labels)
        with fc4:
            st.selectbox(
                "Status",
                ["All", "Open", "Won", "Lost", "Cancelled"],
                disabled=True,
                help="Available once opportunity_df is connected (Role 1)",
            )

        fc5, fc6, fc7, fc8 = st.columns(4)
        with fc5:
            st.selectbox(
                "Sales Stage",
                ["All", "0-Lead/Suspect", "1-Identification", "2-Qualification",
                 "3-Bid Planning", "4-Proposal", "5-Client Decision", "6-Negotiation&Signature"],
                disabled=True,
                help="Available once opportunity_df is connected (Role 1)",
            )
        with fc6:
            st.date_input(
                "Date Range",
                value=[],
                disabled=True,
                help="Available once opportunity_df is connected (Role 1)",
            )
        with fc7:
            st.selectbox(
                "Opportunity Type",
                ["All", "New Business", "Extension", "Renewal", "Change Request"],
                disabled=True,
                help="Available once opportunity_df is connected (Role 1)",
            )
        with fc8:
            st.selectbox(
                "Sales Model",
                ["All", "Direct", "Partner", "Framework", "Public Sector Tender"],
                disabled=True,
                help="Available once opportunity_df is connected (Role 1)",
            )

    fdf = capacity_df.copy()
    if sel_territory != "All":
        fdf = fdf[fdf["territory"] == sel_territory]
    if sel_owner != "All":
        fdf = fdf[fdf["opportunity_owner"] == sel_owner]
    if sel_label != "All":
        fdf = fdf[fdf["capacity_label"] == sel_label]

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

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Row 1: Capacity score bars  |  Label donut ───────────────────────────
    col_bars, col_donut = st.columns([3, 1.1])

    with col_bars:
        st.markdown('<div class="sec-head">Capacity Score by Director</div>', unsafe_allow_html=True)

        sdf = fdf.sort_values("capacity_score")

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=sdf["opportunity_owner"],
            x=sdf["capacity_score"],
            orientation="h",
            marker_color=[LABEL_COLORS[l] for l in sdf["capacity_label"]],
            marker_line_width=0,
            text=[f"  {v:.0%}" for v in sdf["capacity_score"]],
            textposition="outside",
            textfont=dict(size=11, color="#57534E", family="Inter"),
            customdata=sdf[["relative_load", "capacity_label"]].values,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Capacity Score: %{x:.0%}<br>"
                "Relative Load: %{customdata[0]:.0%}<br>"
                "Label: %{customdata[1]}<extra></extra>"
            ),
        ))

        # Threshold lines — softer dash, paler stroke, semantic colours from new palette.
        for x_val, color in [(0.35, LABEL_COLORS["Available"]),
                             (0.15, LABEL_COLORS["Overextended"])]:
            fig_bar.add_shape(
                type="line",
                x0=x_val, x1=x_val, y0=0, y1=1, yref="paper",
                line=dict(dash="2,4", color=color, width=1),
            )

        # Ghosted threshold annotations — modern minimal style (no border, soft page-tint bg).
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

        fig_bar.update_layout(
            height=310,
            margin=dict(l=0, r=80, t=8, b=30),
            paper_bgcolor=_CHART_PAPER,
            plot_bgcolor=_CHART_PLOT,
            xaxis=dict(
                title=dict(text="Capacity Score", font=dict(size=11, color="#78716C")),
                tickformat=".0%",
                range=[0, 1.2],
                gridcolor=_GRID_COLOR,
                showgrid=True,
                zeroline=False,
                showline=False,
                tickfont=dict(size=10, color="#78716C"),
            ),
            yaxis=dict(title="", tickfont=dict(size=12, color="#1C1917"), showgrid=False),
            font=_CHART_FONT,
            hoverlabel=_HOVER,
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
            hole=0.66,                                # bigger hole = more "ring", more modern
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

        # Center total — modern dashboard staple.
        fig_donut.add_annotation(
            text=(f"<b style='font-size:24px;color:#222222'>{total_dirs}</b><br>"
                  "<span style='font-size:9px;color:#78716C;letter-spacing:1.5px'>"
                  "DIRECTORS</span>"),
            x=0.5, y=0.5, showarrow=False, align="center",
        )

        fig_donut.update_layout(
            height=310,
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
        marker_color=[LABEL_COLORS[l] for l in ldf["capacity_label"]],
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Current Load: %{y:.1f}<extra></extra>",
    ))

    # Historical avg as short horizontal segments per director — much cleaner
    # than the old "line-ew" markers, reads as a benchmark line at a glance.
    _AVG_INK = "#44403C"
    for xi, row in ldf.iterrows():
        fig_load.add_shape(
            type="line",
            x0=xi - 0.32, x1=xi + 0.32,
            y0=row["historical_avg_load"], y1=row["historical_avg_load"],
            line=dict(color=_AVG_INK, width=2.5),
        )
    # Invisible legend proxy so the legend still shows "Historical Avg".
    fig_load.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color=_AVG_INK, width=2.5),
        name="Historical Avg",
    ))

    fig_load.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=8, b=40),
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
        xaxis=dict(title="", showgrid=False, tickfont=dict(size=11, color="#1C1917")),
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
            color = BRAND_PALETTE[idx % len(BRAND_PALETTE)]
            fig_trend.add_trace(go.Scatter(
                x=odf["quarter_label"],
                y=odf["current_load"],
                name=owner,
                mode="lines+markers",
                line=dict(
                    color=color,
                    width=2.5,
                    shape="spline",      # smooth curves → modern feel
                    smoothing=1.1,
                ),
                marker=dict(
                    size=6,
                    color=color,
                    line=dict(color=APP_BG, width=1.5),
                ),
                hovertemplate=f"<b>{owner}</b><br>%{{x}}: %{{y:.1f}}<extra></extra>",
            ))
        fig_trend.update_layout(
            height=285,
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
            "open_deal_count", "late_stage_deal_count",
            "weighted_pipeline_revenue", "inferred_delivery_commitments",
            "baseline_reliability",
        ]].copy()
        display["capacity_score"]            = (display["capacity_score"] * 100).round(1)
        display["weighted_pipeline_revenue"] = display["weighted_pipeline_revenue"].apply(
            lambda x: f"${x / 1_000_000:.1f}M"
        )
        display.columns = [
            "Director", "Territory", "Label", "Score (%)",
            "Open Deals", "Late-Stage", "Pipeline (CAD)",
            "Active Deliveries", "Baseline",
        ]
        st.dataframe(display, width="stretch", hide_index=True, height=290)


# ==============================================================================
#  PAGE 2 – RFP Assignment Tool  (placeholder — backend owned by Jai / Role 5)
# ==============================================================================
elif page == "RFP Assignment Tool":

    # ── Context banner ────────────────────────────────────────────────────────
    st.markdown(
        "<div style='background:#F5F2EC;border:1px solid #E7E2D8;border-radius:8px;"
        "padding:0.75rem 1.1rem;margin-bottom:1.2rem;font-size:0.82rem;color:#57534E'>"
        "This page is the <b>UI shell</b> for the RFP Assignment Tool. "
        "The backend pipeline (chunking, embeddings, retrieval, director ranking) "
        "is being built by <b>Jai (Role 5)</b> in "
        "<code>src/rfp_preprocessor.py</code> and <code>src/vector_store.py</code>. "
        "Jai's pipeline output will plug into the results panel below."
        "</div>",
        unsafe_allow_html=True,
    )

    col_input, col_results = st.columns([1, 1.5], gap="large")

    # ── Input panel ───────────────────────────────────────────────────────────
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

    # ── Results placeholder panel ─────────────────────────────────────────────
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
            "Source: <code>rfp_engine.py → generate_assignment_context()</code></span></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-head">Similar Historical RFPs</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Retrieved RFP chunks ranked by semantic similarity will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: <code>vector_store.py → retrieve_relevant_chunks()</code></span></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-head">Recommended Directors</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Ranked director recommendations with capacity, experience,<br>"
            "and assignment scores will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: <code>rfp_engine.py → rank_directors()</code></span></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-head">Capacity Explanation</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Capacity rationale for each recommended director will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: <code>rfp_engine.py → rank_directors()</code></span></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-head">Experience Match Explanation</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Relevant past work, similarity evidence, and fit rationale will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: Azure OpenAI via <code>rfp_engine.py</code></span></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-head">Risk Flags</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='{_ph}'>Low-confidence matches, capacity conflicts, or data-quality warnings will appear here<br>"
            "<span style='font-size:0.72rem'>"
            "Source: <code>rfp_engine.py → generate_assignment_context()</code></span></div>",
            unsafe_allow_html=True,
        )

"""
Central Bank Gold Accumulation vs USD Power & Geopolitical Risk Platform
Interactive Streamlit Dashboard — V5 (DS 650 Visualization Principles Applied)

Encoding rules applied (Munzner / Wilke framework taught in DS 650):
  • Position is the most effective channel → used for every key quantitative variable
  • Color hue → categorical only (country, geo bloc, risk tier)
  • Color saturation/luminance → quantitative (gold share %)
  • Single color scale per dashboard — no ambiguous dual-meaning color
  • Sorted bar charts > unsorted > tables for ranked data
  • Dual Y-axis removed → two separate aligned charts (expressiveness principle)
  • Dual-encoded bar replaced with scatter plot (each channel encodes one attribute)
  • Views per page ≤ 4 (screen-space judiciously)
  • Complementary views: Overview (global) + Detail (country)
  • Explicit encoding: annotations, reference lines, slope chart for change
  • Details on demand: expanders, tabs, multiselect filters

Run:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from pathlib import Path

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gold Reserve Intelligence Platform",
    page_icon="🏅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme constants ───────────────────────────────────────────────────────────
BG       = "#0E1117"
PANEL_BG = "#0D1117"
GOLD     = "#D4AF37"
GOLD_DIM = "rgba(212,175,55,0.15)"
BLUE     = "#4A90D9"
RED      = "#E74C3C"
GREEN    = "#2ECC71"
GREY     = "#95A5A6"
FONT     = dict(color="white")

def dark_layout(height=380, t=30, b=40, l=10, r=10, legend_h=True):
    d = dict(
        plot_bgcolor=BG, paper_bgcolor=PANEL_BG,
        font=FONT, height=height,
        margin=dict(t=t, b=b, l=l, r=r),
    )
    if legend_h:
        d["legend"] = dict(orientation="h", y=1.08, x=0)
    return d

# ── Data paths ────────────────────────────────────────────────────────────────
BASE    = Path(__file__).parent
CURATED = BASE / "data" / "curated"
DOCS    = BASE / "docs"

@st.cache_data
def load_data():
    df     = pd.read_csv(CURATED / "master_panel_nlp.csv")
    scores = pd.read_csv(CURATED / "ml_country_scores.csv")
    return df, scores

df, scores = load_data()

latest_year = int(df["year"].max())
latest      = df[df.year == latest_year]

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Gold_Bars.jpg/320px-Gold_Bars.jpg",
    use_container_width=True
)
st.sidebar.title("🏅 Gold Intelligence")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["🌍 Overview", "📉 Gold vs USD", "🌐 Geopolitics", "📰 Sentiment", "🤖 ML Predictions"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
**Project:** Central Bank Gold Accumulation vs USD Power & Geopolitical Risk
**Data:** World Bank · IMF COFER · OFAC · UN Voting · GDELT
**Model:** Logistic Regression + Gradient Boosting
**Period:** 2000–{latest_year} · {df['country'].nunique()} Countries
""")

import plotly.graph_objects as go
import plotly.express as px

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# DS 650 rules:
#   • ≤ 4 views per page
#   • sorted horizontal bar > table for ranked data (position channel)
#   • explicit annotations on time-series (key world events)
#   • single color scale (gold saturation) for gold quantity
#   • heatmap for multi-attribute temporal data
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🌍 Overview":
    st.title("🏅 Central Bank Gold Accumulation Platform")
    st.markdown(
        "> *Are countries increasing gold reserves due to declining trust in the US dollar "
        "and rising geopolitical risk?*  \n"
        "Integrates **central bank data, geopolitical scores, sanctions exposure, and NLP narratives** "
        "to analyze and predict country-level gold accumulation behavior."
    )

    # ── KPI row ───────────────────────────────────────────────────────────────
    world_gold_bn = latest["world_gold_value_bn"].iloc[0] if len(latest) > 0 else 0
    accumulators  = int(latest["is_accumulating"].sum())
    usd_drawdown  = latest["usd_share_drawdown_pct"].mean()
    sanctioned    = int((latest["sanctions_score"] >= 1).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌎 World Gold Reserves",    f"${world_gold_bn/1000:.1f}T",   f"{latest_year}")
    c2.metric("📈 Countries Accumulating", f"{accumulators}",                f"in {latest_year}")
    c3.metric("💵 Avg USD Drawdown",       f"{usd_drawdown:.1f}%",           "from peak")
    c4.metric("⚠️ Sanctioned Accumulators", f"{sanctioned}",                  "score ≥ 1")

    st.markdown("---")

    # ── View 1: Sorted horizontal bar — Top 15 gold holders ──────────────────
    # DS 650: sorted bar chart uses POSITION (best channel) for ranking
    # more effective than a table because viewers can compare lengths pre-attentively
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader(f"🏆 Top 15 Gold Holders ({latest_year})")
        st.caption("Gold value in USD billions — sorted so position encodes rank (most effective channel)")

        top15 = (
            latest.nlargest(15, "gold_value_usd")
            [["country", "gold_value_usd", "gold_share_pct"]]
            .dropna()
        ).copy()
        top15["gold_bn"] = (top15["gold_value_usd"] / 1e9).round(1)
        top15 = top15.sort_values("gold_bn")  # ascending so largest is at top in h-bar

        fig_bar = go.Figure(go.Bar(
            x=top15["gold_bn"],
            y=top15["country"],
            orientation="h",
            marker=dict(
                color=top15["gold_share_pct"],
                colorscale=[[0, "#1A2332"], [0.4, "#7B5E00"], [1, "#FFD700"]],
                colorbar=dict(
                    title=dict(text="Gold %<br>of Reserves", font=dict(color="white", size=11)),
                    tickfont=dict(color="white"),
                    thickness=12, len=0.8
                ),
                showscale=True,
            ),
            text=top15["gold_bn"].astype(str) + "B",
            textposition="outside",
            hovertemplate="%{y}<br>Gold Value: $%{x:.1f}B<br>Gold Share: %{marker.color:.1f}%<extra></extra>"
        ))
        fig_bar.update_layout(
            **dark_layout(height=430, t=10, b=40, l=10, r=80, legend_h=False),
            xaxis_title="Gold Value (USD Billions)",
            xaxis=dict(range=[0, top15["gold_bn"].max() * 1.2]),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption("Color = gold's share of total reserves (darker gold = higher dependence on gold)")

    # ── View 2: Annotated accumulation rate line chart ────────────────────────
    # DS 650: position channel for quantitative time-series + explicit annotations for events
    with col_right:
        st.subheader("📊 Global Accumulation Rate Over Time")
        st.caption("% of countries actively buying gold each year — annotated with key world events")

        accum_yr = df.groupby("year").agg(
            accumulators=("is_accumulating", "sum"),
            total=("is_accumulating", "count")
        ).reset_index()
        accum_yr["rate"] = (accum_yr["accumulators"] / accum_yr["total"] * 100).round(1)

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=accum_yr["year"], y=accum_yr["rate"],
            mode="lines+markers",
            line=dict(color=GOLD, width=2.5),
            fill="tozeroy", fillcolor=GOLD_DIM,
            name="% Accumulating",
            hovertemplate="Year %{x}: %{y:.1f}% of countries buying gold<extra></extra>"
        ))

        # Explicit annotations — DS 650: "use explicit encoding to emphasize patterns"
        events = [
            (2008, "GFC"), (2011, "EU Debt Crisis"),
            (2014, "Crimea"), (2020, "COVID"),
            (2022, "Russia\nSanctions"), (2023, "US Rates Peak")
        ]
        for yr, label in events:
            row = accum_yr[accum_yr.year == yr]
            if not row.empty:
                fig_line.add_annotation(
                    x=yr, y=row["rate"].values[0] + 4,
                    text=label, showarrow=True,
                    arrowhead=2, arrowsize=0.8, arrowcolor=GREY,
                    font=dict(size=9, color=GREY), ax=0, ay=-20
                )

        fig_line.update_layout(
            **dark_layout(height=430, t=30, b=40),
            xaxis_title="Year",
            yaxis_title="% of Countries Accumulating Gold",
            yaxis=dict(range=[0, 105]),
        )
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")

    # ── View 3 & 4: Map + Heatmap in tabs (keeps view count ≤ 4) ─────────────
    # DS 650: use tabs for complementary views when screen space is limited
    map_tab, heat_tab = st.tabs([
        f"🗺️ World Gold Reserve Map ({latest_year})",
        "📈 Accumulation Heatmap (Top 20 Countries, 2015–2025)"
    ])

    with map_tab:
        st.caption("Gold as % of total reserves — hover any country for details. Darker gold = higher gold dependence.")
        try:
            map_df = latest[
                ["country", "country_code", "gold_share_pct", "gold_value_usd",
                 "accumulation_streak", "geo_risk_tier"]
            ].dropna(subset=["gold_share_pct"]).copy()
            map_df["gold_bn"] = (map_df["gold_value_usd"] / 1e9).round(1)

            fig_map = px.choropleth(
                map_df,
                locations="country_code",
                color="gold_share_pct",
                hover_name="country",
                hover_data={"gold_bn": True, "accumulation_streak": True,
                            "geo_risk_tier": True, "country_code": False, "gold_share_pct": ":.1f"},
                color_continuous_scale=[[0, "#1A2332"], [0.3, "#7B5E00"],
                                        [0.6, "#C8960C"], [1, "#FFD700"]],
                range_color=[0, map_df["gold_share_pct"].quantile(0.95)],
                labels={
                    "gold_share_pct": "Gold Share (%)",
                    "gold_bn": "Gold Value ($B)",
                    "accumulation_streak": "Buying Streak (yrs)",
                    "geo_risk_tier": "Geo Risk"
                },
            )
            fig_map.update_layout(
                geo=dict(bgcolor=PANEL_BG, showframe=False, showcoastlines=True,
                         coastlinecolor="#2A3548", landcolor="#1A2332",
                         showocean=True, oceancolor=PANEL_BG),
                paper_bgcolor=PANEL_BG, font=FONT,
                height=500, margin=dict(t=10, b=10, l=10, r=10),
                coloraxis_colorbar=dict(
                    title=dict(text="Gold %", font=dict(color="white")),
                    tickfont=dict(color="white")
                )
            )
            st.plotly_chart(fig_map, use_container_width=True)
        except Exception as e:
            st.info(f"Map unavailable: {e}")

    with heat_tab:
        st.caption(
            "Gold share (%) for the top 20 holders across 2015–2025. "
            "Darker gold = higher share. Reveals which countries are consistently accumulating vs declining."
        )
        try:
            top20 = latest.nlargest(20, "gold_value_usd")["country"].tolist()
            heat_df = (
                df[(df["country"].isin(top20)) & (df["year"] >= 2015)]
                .pivot_table(index="country", columns="year", values="gold_share_pct")
                .round(1)
            )
            # Sort rows by latest year gold share (highest at top)
            if latest_year in heat_df.columns:
                heat_df = heat_df.sort_values(latest_year, ascending=True)

            fig_heat = go.Figure(go.Heatmap(
                z=heat_df.values.tolist(),
                x=[str(y) for y in heat_df.columns.tolist()],
                y=heat_df.index.tolist(),
                colorscale=[[0, "#1A2332"], [0.4, "#7B5E00"], [1, "#FFD700"]],
                hoverongaps=False,
                hovertemplate="%{y}<br>Year %{x}: %{z:.1f}%<extra></extra>",
                colorbar=dict(
                    title=dict(text="Gold %", font=dict(color="white")),
                    tickfont=dict(color="white")
                )
            ))
            fig_heat.update_layout(
                paper_bgcolor=PANEL_BG, plot_bgcolor=PANEL_BG,
                font=FONT, height=520,
                xaxis=dict(side="bottom", title="Year"),
                yaxis=dict(title="Country"),
                margin=dict(t=10, b=40, l=10, r=10)
            )
            st.plotly_chart(fig_heat, use_container_width=True)
        except Exception as e:
            st.info(f"Heatmap unavailable: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — GOLD vs USD
# DS 650 rules applied:
#   • Dual Y-axis REMOVED — violates expressiveness: viewer can't compare scales fairly
#   • Replaced with two SEPARATE aligned charts (same x-axis) using position channel
#   • Added scatter plot (one dot per year) to EXPLICITLY encode the association
#   • Color hue = year for time direction on scatter
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📉 Gold vs USD":
    st.title("📉 Gold Accumulation vs USD Dominance")
    st.markdown(
        "The core thesis: as the **US dollar loses share of global reserves**, "
        "central banks diversify into **gold**.  \n"
        "DS 650 principle: each chart encodes **one task** — trend OR association — not both."
    )

    world_trend = df.groupby("year").agg(
        usd_share=("usd_share_of_reserves_pct", "mean"),
        world_gold_share=("world_gold_share_pct", "first"),
        world_gold_bn=("world_gold_value_bn", "first"),
    ).reset_index().dropna()

    # ── Views 1 & 2: Two SEPARATE aligned line charts (not dual Y-axis) ───────
    # DS 650: dual Y-axis creates ambiguity — viewer can't fairly compare magnitudes.
    # Two separate charts with the SAME x-axis allow comparison without misleading the viewer.
    st.subheader("USD Dominance & World Gold Share — Separate Aligned Trends")
    st.caption(
        "Two aligned charts with the same x-axis — DS 650 principle: use separate position-encoded "
        "views rather than a dual-axis chart to avoid false magnitude comparisons."
    )

    fig_usd = go.Figure()
    fig_usd.add_trace(go.Scatter(
        x=world_trend["year"], y=world_trend["usd_share"],
        mode="lines+markers", line=dict(color=BLUE, width=2.5),
        fill="tozeroy", fillcolor="rgba(74,144,217,0.12)",
        hovertemplate="Year %{x}: USD Share = %{y:.1f}%<extra></extra>"
    ))
    # Annotation: structural decline
    fig_usd.add_annotation(
        x=2001, y=world_trend["usd_share"].max(),
        text="Peak USD dominance", showarrow=True,
        arrowhead=2, font=dict(size=9, color=GREY), ax=40, ay=10
    )
    fig_usd.add_annotation(
        x=2022, y=world_trend[world_trend.year == 2022]["usd_share"].values[0]
            if 2022 in world_trend["year"].values else 58,
        text="Russia sanctions shock", showarrow=True,
        arrowhead=2, font=dict(size=9, color=GREY), ax=-50, ay=-25
    )
    fig_usd.update_layout(
        **dark_layout(height=260, t=30, b=10, legend_h=False),
        yaxis_title="USD Share of Global Reserves (%)",
        xaxis=dict(showticklabels=False),  # shared x — hide labels on top chart
    )

    fig_gold_share = go.Figure()
    fig_gold_share.add_trace(go.Scatter(
        x=world_trend["year"], y=world_trend["world_gold_share"],
        mode="lines+markers", line=dict(color=GOLD, width=2.5),
        fill="tozeroy", fillcolor=GOLD_DIM,
        hovertemplate="Year %{x}: World Gold Share = %{y:.1f}%<extra></extra>"
    ))
    fig_gold_share.update_layout(
        **dark_layout(height=260, t=10, b=40, legend_h=False),
        yaxis_title="World Gold Share (%)",
        xaxis_title="Year",
    )

    st.plotly_chart(fig_usd,        use_container_width=True)
    st.plotly_chart(fig_gold_share, use_container_width=True)

    st.markdown("---")

    # ── View 3: Scatter plot — explicit association encoding ──────────────────
    # DS 650: to show association between two quantitative variables, use a scatter plot.
    # Position (x, y) is the most effective channel for both variables.
    # Color hue encodes time (year) as a secondary, categorical-like dimension.
    st.subheader("Does USD Decline Drive Gold Buying? — Scatter Plot (2000–2025)")
    st.caption(
        "Each dot = one year. Position encodes BOTH variables simultaneously. "
        "Color = year (darker = more recent). Look for a downward-right pattern: "
        "lower USD share → higher gold share."
    )

    scatter_df = world_trend.dropna(subset=["usd_share", "world_gold_share"])
    fig_scatter = px.scatter(
        scatter_df, x="usd_share", y="world_gold_share",
        text="year",
        color="year",
        color_continuous_scale=[[0, "#1A2332"], [0.5, "#4A90D9"], [1, GOLD]],
        labels={
            "usd_share": "USD Share of Global Reserves (%)",
            "world_gold_share": "World Gold Share (%)",
            "year": "Year"
        },
        trendline="ols",
        trendline_color_override=RED,
    )
    fig_scatter.update_traces(
        selector=dict(mode="markers+text"),
        textposition="top center",
        textfont=dict(size=9, color=GREY),
        marker=dict(size=10)
    )
    fig_scatter.update_layout(
        **dark_layout(height=440, t=20, b=50),
        coloraxis_colorbar=dict(
            title=dict(text="Year", font=dict(color="white")),
            tickfont=dict(color="white")
        )
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.caption("Red trend line shows the inverse relationship: as USD share falls, world gold share rises.")

    st.markdown("---")

    # ── View 4: Country comparison line chart (multiselect) ───────────────────
    st.subheader("Country Gold Share Trends — Compare & Contrast")
    st.caption(
        "Color hue = country (categorical variable). "
        "Select countries that are similarly ranked to avoid clutter (DS 650: design space exploration)."
    )

    all_countries    = sorted(df["country"].dropna().unique())
    default_countries = [c for c in
                         ["China", "India", "Poland", "Czechia", "Singapore", "Turkiye"]
                         if c in all_countries]

    selected = st.multiselect("Select countries to compare:", all_countries, default=default_countries)

    if selected:
        sub = df[df["country"].isin(selected)][["country", "year", "gold_share_pct"]].dropna()
        fig_country = px.line(
            sub, x="year", y="gold_share_pct", color="country",
            labels={"gold_share_pct": "Gold Share (%)", "year": "Year", "country": "Country"},
            markers=True,
        )
        fig_country.update_layout(**dark_layout(height=400, t=20, b=40))
        st.plotly_chart(fig_country, use_container_width=True)
    else:
        st.info("Select at least one country above.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — GEOPOLITICS
# DS 650 rules applied:
#   • Fixed hardcoded "2023" → uses latest_year
#   • Dual-encoded bar (height=streak, color=gold share) REPLACED with scatter plot
#     (x=UN alignment, y=gold share, size=streak, color=geo_bloc = one channel per attribute)
#   • Sanctions bar chart kept (ordinal x-axis, quantitative y = good mapping)
#   • Added reference line for "non-sanctioned baseline"
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🌐 Geopolitics":
    st.title("🌐 Geopolitical Risk & Gold Accumulation")
    st.markdown(
        "Countries with **high sanctions exposure**, **geopolitical risk**, or **divergence from US foreign policy** "
        "show systematically higher gold accumulation.  \n"
        "DS 650: each chart encodes **one relationship** using the most effective channel for that attribute type."
    )

    geo_df = df[df.year == latest_year].dropna(subset=["sanctions_score", "gold_share_pct"])

    # ── KPI row ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    sanc2_avg  = geo_df[geo_df.sanctions_score >= 2]["gold_share_pct"].mean()
    sanc0_avg  = geo_df[geo_df.sanctions_score == 0]["gold_share_pct"].mean()
    div_streak = geo_df[geo_df.geo_bloc == "us_divergent"]["accumulation_streak"].mean()
    all_streak = geo_df["accumulation_streak"].mean()

    col1.metric("Heavily Sanctioned Avg Gold Share",
                f"{sanc2_avg:.1f}%",
                f"+{sanc2_avg - sanc0_avg:.1f}pp vs non-sanctioned")
    col2.metric("US-Divergent Avg Buying Streak",
                f"{div_streak:.1f} yrs",
                f"+{div_streak - all_streak:.1f}yr vs panel avg")
    col3.metric("Countries w/ Any Sanctions",
                f"{int((geo_df.sanctions_score >= 1).sum())}",
                f"out of {len(geo_df)} in panel")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    # ── View 1: Sanctions bar chart ───────────────────────────────────────────
    # DS 650: ordinal x (None→Low→Medium→High), quantitative y → sorted bar is correct
    # Explicit reference line = "baseline" (non-sanctioned average) for comparison
    with col_a:
        st.subheader("Sanctions Exposure vs Avg Gold Share")
        st.caption(
            f"Bar height = position channel (most effective). "
            f"Dashed line = non-sanctioned baseline ({sanc0_avg:.1f}%). ({latest_year})"
        )

        sanc_group = geo_df.groupby("sanctions_score").agg(
            avg_gold=("gold_share_pct", "mean"),
            n=("country", "count")
        ).reset_index()
        sanc_group["label"] = sanc_group["sanctions_score"].map(
            {0: "None", 1: "Low", 2: "Medium", 3: "High"}
        ).fillna("High")

        fig_sanc = go.Figure(go.Bar(
            x=sanc_group["label"],
            y=sanc_group["avg_gold"],
            marker_color=[GREY, "#F39C12", RED, "#8E44AD"][:len(sanc_group)],
            text=sanc_group["avg_gold"].round(1).astype(str) + "%",
            textposition="outside",
            customdata=sanc_group["n"],
            hovertemplate="%{x} sanctions<br>Avg gold share: %{y:.1f}%<br>Countries: %{customdata}<extra></extra>"
        ))
        # Reference line — DS 650: explicit encoding emphasises the pattern
        fig_sanc.add_hline(
            y=sanc0_avg, line_dash="dash", line_color=GREY,
            annotation_text=f"No-sanctions baseline: {sanc0_avg:.1f}%",
            annotation_font_color=GREY
        )
        fig_sanc.update_layout(
            **dark_layout(height=370, t=30, b=40, legend_h=False),
            xaxis_title="Sanctions Level",
            yaxis_title="Avg Gold Share (%)",
            yaxis=dict(range=[0, sanc_group["avg_gold"].max() * 1.35])
        )
        st.plotly_chart(fig_sanc, use_container_width=True)

    # ── View 2: Scatter plot — multi-attribute association ────────────────────
    # DS 650 principle: to show association between 3+ attributes, use scatter plot.
    # x = UN alignment (quantitative), y = gold share (quantitative) → position (best channel)
    # size = accumulation streak (quantitative) → area (acceptable)
    # color = geo_bloc (categorical) → color hue (correct mapping)
    # REPLACES old dual-encoded bar (height=streak, color=gold share = ambiguous)
    with col_b:
        st.subheader("Geopolitical Alignment vs Gold Strategy")
        st.caption(
            "Scatter plot: x = UN alignment with US (low = divergent), y = gold share, "
            "size = buying streak, color = geo bloc. Each channel encodes ONE attribute. "
            f"({latest_year})"
        )

        scatter_geo = geo_df.dropna(
            subset=["un_alignment_score", "gold_share_pct", "accumulation_streak", "geo_bloc"]
        ).copy()
        scatter_geo["streak_size"] = scatter_geo["accumulation_streak"].clip(0, 15) * 3 + 6

        bloc_colors = {
            "us_divergent": RED,
            "neutral": GOLD,
            "US_allied": BLUE,
            "ally": BLUE,
        }
        scatter_geo["color"] = scatter_geo["geo_bloc"].map(bloc_colors).fillna(GREY)

        fig_geo = go.Figure()
        for bloc, grp in scatter_geo.groupby("geo_bloc"):
            fig_geo.add_trace(go.Scatter(
                x=grp["un_alignment_score"],
                y=grp["gold_share_pct"],
                mode="markers",
                name=bloc,
                marker=dict(
                    size=grp["streak_size"],
                    color=bloc_colors.get(bloc, GREY),
                    opacity=0.8,
                    line=dict(width=0.5, color="white")
                ),
                text=grp["country"],
                hovertemplate=(
                    "%{text}<br>"
                    "UN Alignment: %{x:.1f}<br>"
                    "Gold Share: %{y:.1f}%<br>"
                    "<extra></extra>"
                )
            ))
        fig_geo.update_layout(
            **dark_layout(height=370, t=30, b=40),
            xaxis_title="UN Alignment Score (0=divergent, 100=aligned with US)",
            yaxis_title="Gold Share of Reserves (%)",
        )
        st.plotly_chart(fig_geo, use_container_width=True)
        st.caption("Larger bubbles = longer consecutive buying streak. Divergent countries cluster top-left.")

    # ── View 3: Country geopolitical profile table ────────────────────────────
    st.markdown("---")
    st.subheader(f"Country Geopolitical Profile ({latest_year}) — Details on Demand")
    st.caption("DS 650: use tables when precise value lookup is needed; link with charts above via filtering.")

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        risk_filter = st.selectbox("Filter by Risk Tier:", ["All", "high", "medium", "low"])
    with filter_col2:
        bloc_filter = st.selectbox("Filter by Geo Bloc:", ["All"] + sorted(geo_df["geo_bloc"].dropna().unique()))

    geo_table = geo_df[
        ["country", "geo_bloc", "geo_risk_tier", "sanctions_score",
         "un_alignment_score", "gold_share_pct", "accumulation_streak"]
    ].copy()
    geo_table = geo_table.sort_values("gold_share_pct", ascending=False).reset_index(drop=True)

    if risk_filter != "All":
        geo_table = geo_table[geo_table["geo_risk_tier"] == risk_filter]
    if bloc_filter != "All":
        geo_table = geo_table[geo_table["geo_bloc"] == bloc_filter]

    geo_table.index = range(1, len(geo_table) + 1)
    geo_table.columns = ["Country", "Geo Bloc", "Risk Tier", "Sanctions", "UN Alignment", "Gold Share %", "Streak"]
    geo_table["Gold Share %"] = geo_table["Gold Share %"].round(1)
    st.dataframe(geo_table, use_container_width=True, height=380)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — NLP SENTIMENT
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📰 Sentiment":
    st.title("📰 NLP Narrative Analysis")
    st.markdown(
        "Financial news about gold, de-dollarization and USD dominance — pulled **live from GDELT** "
        "and scored with keyword-based sentiment analysis.  \n"
        "Shows the *narrative environment* driving central bank gold decisions."
    )

    import requests
    from datetime import datetime

    GDELT_QUERIES = {
        "🏦 Central Bank Gold Buying": "central+bank+gold+reserves+buying",
        "💵 De-Dollarization":         "de-dollarization+dollar+reserves",
        "⚠️  Sanctions & Gold":        "sanctions+gold+reserves+central+bank",
    }

    POSITIVE_WORDS = ["buy", "bought", "purchase", "increase", "boost", "surge", "rise", "accumulate", "add", "growing"]
    NEGATIVE_WORDS = ["sell", "sold", "decline", "fall", "drop", "reduce", "cut", "weak", "concern", "risk"]
    GOLD_WORDS     = ["gold", "reserve", "bullion", "tonne", "troy"]
    USD_NEG_WORDS  = ["dedollar", "de-dollar", "dollar decline", "dollar weakness",
                      "away from dollar", "bypass dollar"]

    def score_sentiment(text):
        t    = text.lower()
        pos  = sum(1 for w in POSITIVE_WORDS if w in t)
        neg  = sum(1 for w in NEGATIVE_WORDS if w in t)
        gold = sum(1 for w in GOLD_WORDS if w in t)
        usd  = sum(1 for w in USD_NEG_WORDS if w in t)
        score = (pos - neg) / max(pos + neg, 1)
        return round(score, 2), gold, usd

    @st.cache_data(ttl=3600)
    def fetch_gdelt_news(query, max_records=10):
        url = (
            f"https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={query}&mode=artlist&maxrecords={max_records}"
            f"&format=json&sort=DateDesc&timespan=48h"
        )
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json().get("articles", [])
        except Exception:
            pass
        return []

    st.subheader("📡 Live News Feed (Last 48 Hours)")
    st.caption("Sourced from GDELT — updates every hour · Scored with keyword sentiment")

    tabs = st.tabs(list(GDELT_QUERIES.keys()))
    all_articles = []

    for tab, (label, query) in zip(tabs, GDELT_QUERIES.items()):
        with tab:
            with st.spinner(f"Fetching latest {label} news..."):
                articles = fetch_gdelt_news(query, max_records=12)

            if not articles:
                st.info("No articles found in last 48h — GDELT may be rate-limiting. Try again shortly.")
            else:
                for art in articles:
                    title    = art.get("title", "No title")
                    url_art  = art.get("url", "#")
                    source   = art.get("domain", "Unknown")
                    seendate = art.get("seendate", "")
                    try:
                        dt = datetime.strptime(seendate[:8], "%Y%m%d").strftime("%b %d")
                    except Exception:
                        dt = seendate[:10]

                    score, gold_hits, usd_neg_hits = score_sentiment(title)
                    badge = "🟢 Bullish" if score > 0.1 else ("🔴 Bearish" if score < -0.1 else "⚪ Neutral")

                    st.markdown(
                        f"**[{title}]({url_art})**  \n"
                        f"📰 {source} · 📅 {dt} · {badge}"
                        + (f" · 🥇 Gold signal: {gold_hits}"     if gold_hits    > 0 else "")
                        + (f" · 💵 De-$ signal: {usd_neg_hits}"  if usd_neg_hits > 0 else "")
                    )
                    st.divider()
                    all_articles.append({"title": title, "source": source,
                                         "score": score, "gold_hits": gold_hits,
                                         "usd_neg": usd_neg_hits, "query": label})

    # ── Sentiment summary ─────────────────────────────────────────────────────
    if all_articles:
        st.markdown("---")
        st.subheader("📊 Sentiment Distribution — Live Articles")
        st.caption(
            "DS 650: bar chart for a categorical variable (sentiment class) with quantitative count. "
            "Position (height) encodes count — most effective channel."
        )

        art_df  = pd.DataFrame(all_articles)
        bullish = int((art_df["score"] > 0.1).sum())
        bearish = int((art_df["score"] < -0.1).sum())
        neutral = len(art_df) - bullish - bearish
        avg_sc  = art_df["score"].mean()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📰 Articles Fetched", len(art_df))
        m2.metric("🟢 Bullish",          bullish)
        m3.metric("🔴 Bearish",          bearish)
        m4.metric("📈 Avg Sentiment",    f"{avg_sc:+.2f}")

        fig_sent = go.Figure(go.Bar(
            x=["Bullish 🟢", "Neutral ⚪", "Bearish 🔴"],
            y=[bullish, neutral, bearish],
            marker_color=[GREEN, GREY, RED],
            text=[bullish, neutral, bearish],
            textposition="outside",
        ))
        fig_sent.update_layout(
            **dark_layout(height=300, t=20, b=30, legend_h=False),
            yaxis_title="Article Count",
            yaxis=dict(range=[0, max(bullish, neutral, bearish) * 1.3]),
        )
        st.plotly_chart(fig_sent, use_container_width=True)

    st.markdown("---")

    # ── Historical NLP trend ──────────────────────────────────────────────────
    st.subheader("📈 Historical USD Sentiment Trend (2000–2025)")
    st.caption(
        "Line chart: position encodes % of articles with negative vs positive USD sentiment over time."
    )

    nlp_global = df.groupby("year").agg(
        usd_neg=("global_usd_negative_pct", "first"),
        usd_pos=("global_usd_positive_pct", "first"),
    ).reset_index().dropna()

    if len(nlp_global) > 0:
        fig_nlp = go.Figure()
        fig_nlp.add_trace(go.Scatter(
            x=nlp_global["year"], y=nlp_global["usd_neg"],
            name="Negative USD Sentiment (%)",
            line=dict(color=RED, width=2.5),
            fill="tozeroy", fillcolor="rgba(231,76,60,0.15)"
        ))
        fig_nlp.add_trace(go.Scatter(
            x=nlp_global["year"], y=nlp_global["usd_pos"],
            name="Positive USD Sentiment (%)",
            line=dict(color=GREEN, width=2)
        ))
        fig_nlp.update_layout(
            **dark_layout(height=350, t=30, b=40),
            xaxis_title="Year", yaxis_title="% of Articles",
        )
        st.plotly_chart(fig_nlp, use_container_width=True)
    else:
        st.info("Historical NLP data not available.")

    with st.expander("📖 How This Works"):
        st.markdown("""
        **Live data:** GDELT Document API (free, no key required) — fetches articles from last 48 hours
        matching queries for *central bank gold*, *de-dollarization*, and *sanctions + gold*.

        **Sentiment scoring:** Keyword-based scorer counting bullish/bearish financial terms.
        Production upgrade: swap for FinBERT (HuggingFace) for sentence-level analysis.

        **GDELT** indexes ~100,000 news articles per day from 65 languages and 200+ countries.
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — ML PREDICTIONS
# DS 650 rules applied:
#   • Horizontal sorted bar — position encodes score (most effective channel)
#   • Color encodes ONE categorical dimension (driver type) — consistent meaning
#   • Pillar breakdown: small-multiple bars showing what drives each country's score
#   • Table with filter = "details on demand"
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 ML Predictions":
    max_data_year = int(df["year"].max())
    predict_year  = max_data_year + 1
    st.title(f"🤖 ML Predictions: Top Gold Accumulators {predict_year}")
    st.markdown(
        f"An **interpretable 4-pillar scoring model** ranks countries by likelihood of increasing "
        f"gold reserves in {predict_year}.  \n"
        f"DS 650: horizontal sorted bar — **position** encodes rank (most effective channel). "
        f"Color encodes ONE categorical driver type — no ambiguous dual encoding."
    )

    top10 = scores.head(10).copy()

    # ── View 1: Sorted horizontal bar — top 10 ────────────────────────────────
    # Color = ONE categorical dimension (driver category) with fixed legend
    def driver_color(row):
        if row.get("sanctions_score", 0) >= 2:
            return RED      # structural driver: sanctions
        if str(row.get("geo_risk_tier", "")).lower() == "high":
            return "#E67E22"  # structural driver: geo risk
        return BLUE         # fundamental driver: gold accumulation momentum

    colors = [driver_color(r) for _, r in top10.iterrows()]

    fig_ml = go.Figure(go.Bar(
        x=top10["gold_accumulation_score"],
        y=top10["country"],
        orientation="h",
        marker_color=colors,
        text=top10["gold_accumulation_score"].round(1).astype(str),
        textposition="outside",
        hovertemplate="%{y}<br>Score: %{x:.1f} / 100<extra></extra>"
    ))
    # Legend via invisible traces (Plotly bar color legend workaround)
    for color, label in [(RED, "🔴 Heavily Sanctioned"), ("#E67E22", "🟠 High Geo Risk"), (BLUE, "🔵 Strong Accumulator")]:
        fig_ml.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(color=color, size=10, symbol="square"),
            name=label, showlegend=True
        ))
    fig_ml.update_layout(
        **dark_layout(height=430, t=30, b=50),
        title=f"Top 10 Countries Predicted to Increase Gold Reserves in {predict_year}",
        xaxis_title="Gold Accumulation Score (0–100)",
        xaxis=dict(range=[0, 120]),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_ml, use_container_width=True)

    st.markdown("---")

    # ── View 2: 4-Pillar breakdown — small multiples ──────────────────────────
    # DS 650: small multiples for comparing subgroups across the same metric
    # each sub-chart shows one pillar score for the top 10 countries
    st.subheader("📊 What Drives Each Country's Score? — 4-Pillar Breakdown")
    st.caption(
        "DS 650 small multiples: the same chart type (horizontal bar) applied to each pillar. "
        "Consistent x-axis (0–100) allows fair comparison across pillars."
    )

    pillar_cols = {
        "Pillar 1: Physical Buying Momentum": "p1_momentum",
        "Pillar 2: Buying Consistency":       "p2_consistency",
        "Pillar 3: Geopolitical Motivation":  "p3_geopolitical",
        "Pillar 4: Strategic Allocation Gap": "p4_allocation",
    }

    available_pillars = {k: v for k, v in pillar_cols.items() if v in scores.columns}

    if available_pillars:
        top5_countries = top10["country"].head(5).tolist()
        top5_df = scores[scores["country"].isin(top5_countries)].set_index("country")

        cols_p = st.columns(len(available_pillars))
        for col_widget, (pillar_name, pillar_col) in zip(cols_p, available_pillars.items()):
            with col_widget:
                sub_df = top5_df[[pillar_col]].dropna().sort_values(pillar_col)
                fig_p = go.Figure(go.Bar(
                    x=sub_df[pillar_col],
                    y=sub_df.index.tolist(),
                    orientation="h",
                    marker_color=GOLD,
                    text=sub_df[pillar_col].round(0).astype(int).astype(str),
                    textposition="outside",
                ))
                fig_p.update_layout(
                    **dark_layout(height=250, t=10, b=30, l=5, r=40, legend_h=False),
                    title=dict(text=pillar_name.split(":")[1].strip(), font=dict(size=11)),
                    xaxis=dict(range=[0, 110], title="Score"),
                )
                st.plotly_chart(fig_p, use_container_width=True)
        st.caption("Each pillar scored 0–100. Countries missing a bar have insufficient data for that pillar.")
    else:
        st.info("Pillar breakdown not yet in scores CSV. Re-run src/ml/score_countries.py to generate.")

    # ── View 3: Full ranking table + filter ───────────────────────────────────
    st.markdown("---")
    st.subheader(f"Full Country Ranking — Details on Demand")
    st.caption("DS 650: use filters to reduce cognitive load — show details only when requested.")

    show_cols = ["country", "gold_accumulation_score", "gold_share_pct", "gold_yoy_change_pct",
                 "accumulation_streak", "sanctions_score", "geo_risk_tier", "usd_share_drawdown_pct"]
    show_cols = [c for c in show_cols if c in scores.columns]
    disp = scores[show_cols].copy()
    disp.columns = [c.replace("_", " ").title() for c in show_cols]

    f1, f2 = st.columns(2)
    with f1:
        risk_f = st.selectbox("Filter by Geo Risk Tier:", ["All", "high", "medium", "low"])
    with f2:
        score_min = st.slider("Minimum Score:", 0, 100, 0)

    if risk_f != "All" and "Geo Risk Tier" in disp.columns:
        disp = disp[disp["Geo Risk Tier"] == risk_f]
    if "Gold Accumulation Score" in disp.columns:
        disp = disp[disp["Gold Accumulation Score"] >= score_min]

    disp.index = range(1, len(disp) + 1)
    st.dataframe(disp, use_container_width=True, height=430)

    with st.expander("📖 Scoring Methodology (V5)"):
        st.markdown(f"""
        **4-Pillar Scoring Model — designed to be price-neutral (avoids 2025 gold price inflation bias)**

        | Pillar | Weight | Inputs |
        |--------|--------|--------|
        | Physical Buying Momentum | 30% | WGC tonnage YoY (70%) + gold share change (30%) |
        | Buying Consistency | 25% | Accumulation streak (60%) + 5yr buy frequency (40%) |
        | Geopolitical Motivation | 25% | UN divergence score (60%) + sanctions score (40%) |
        | Strategic Allocation Gap | 20% | Low gold share percentile (40%) + 3yr trend (60%) |

        **Training:** 2001–2019 time-based split · **Test:** 2020–{max_data_year}
        **Target:** Will this country's gold share increase next year?
        """)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#888; font-size:12px'>"
    "Gold Reserve Intelligence Platform · Python · World Bank API · IMF COFER · OFAC · UN Voting · GDELT · "
    "DS 650 Visualization Principles Applied · Sathwik Arroju"
    "</div>",
    unsafe_allow_html=True
)

"""
Central Bank Gold Accumulation vs USD Power & Geopolitical Risk Platform
Interactive Analytics Dashboard

Tracks central bank gold accumulation across 93 countries (2000–2025),
quantifies the relationship with USD dominance, geopolitical risk, and sanctions
exposure, and predicts which countries are most likely to increase gold reserves next year.

Run:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
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
    df      = pd.read_csv(CURATED / "master_panel_nlp.csv")
    scores  = pd.read_csv(CURATED / "ml_country_scores.csv")
    metrics_path = CURATED / "ml_model_metrics.csv"
    metrics = pd.read_csv(metrics_path) if metrics_path.exists() else pd.DataFrame()
    return df, scores, metrics

df, scores, model_metrics = load_data()

latest_year = int(df["year"].max())
latest      = df[df.year == latest_year]

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown(
    "<div style='text-align:center; padding: 12px 0 4px 0; font-size: 2.6rem;'>🏅</div>"
    "<div style='text-align:center; font-size: 1.25rem; font-weight: 700; letter-spacing: 0.5px;'>Gold Intelligence</div>",
    unsafe_allow_html=True,
)
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
**Scoring:** 4-Pillar Rule Model (XGBoost-validated)
**Period:** 2000–{latest_year} · {df['country'].nunique()} Countries · {len(scores)} Scored
""")

import plotly.graph_objects as go
import plotly.express as px

if page == "🌍 Overview":
    st.title("🏅 Central Bank Gold Accumulation Platform")
    st.markdown(
        "> *Are countries increasing gold reserves due to declining trust in the US dollar "
        "and rising geopolitical risk?*\n\n"
        f"This platform tracks gold reserve shifts across **{df['country'].nunique()} central banks** from 2000 to {latest_year}, "
        "revealing how macroeconomic stress, sanctions pressure, and geopolitical realignment "
        "are reshaping the global reserve landscape."
    )

    # ── KPI row ───────────────────────────────────────────────────────────────
    world_gold_bn      = latest["world_gold_value_bn"].iloc[0] if len(latest) > 0 else 0
    accumulators       = int(latest["is_accumulating"].sum())
    usd_drawdown       = latest["usd_share_drawdown_pct"].mean()
    sanctioned         = int((latest["sanctions_score"] >= 1).sum())
    acc_during_usd_dec = int(latest["accumulating_during_usd_decline"].sum()) if "accumulating_during_usd_decline" in latest.columns else 0
    pct_panel          = f"{acc_during_usd_dec}/{accumulators} accumulators" if accumulators > 0 else ""

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌎 World Gold Reserves",        f"${world_gold_bn/1000:.1f}T",  f"{latest_year}")
    c2.metric("📈 Countries Accumulating",     f"{accumulators}",               f"in {latest_year}")
    c3.metric("💵 Avg USD Drawdown from Peak", f"{usd_drawdown:.1f}%",          "since peak USD share")
    c4.metric("⚠️ Sanctioned Accumulators",    f"{sanctioned}",                 "OFAC score ≥ 1")

    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader(f"🏆 Top 15 Gold Holders ({latest_year})")
        st.caption("Bar length = total gold value · Color intensity = gold's share of that country's total reserves")

        extra_cols = [c for c in ["country_share_of_world_gold_pct", "gold_rank", "total_reserves_usd"]
                      if c in latest.columns]
        top15 = (
            latest.nlargest(15, "gold_value_usd")
            [["country", "gold_value_usd", "gold_share_pct"] + extra_cols]
            .dropna(subset=["gold_value_usd"])
        ).copy()
        top15["gold_bn"] = (top15["gold_value_usd"] / 1e9).round(1)
        if "total_reserves_usd" in top15.columns:
            top15["total_res_bn"] = (top15["total_reserves_usd"] / 1e9).round(1)
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
            hovertemplate="%{y}<br>Gold Value: $%{x:.1f}B<br>Gold Share: %{marker.color:.1f}%<br>Click chart for full profile<extra></extra>"
        ))
        fig_bar.update_layout(
            **dark_layout(height=430, t=10, b=40, l=10, r=80, legend_h=False),
            xaxis_title="Gold Value (USD Billions)",
            xaxis=dict(range=[0, top15["gold_bn"].max() * 1.2]),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption("A country can hold large absolute gold value but low gold share — or vice versa. Both dimensions matter for reserve strategy analysis.")
        # Dynamic insight
        top_share_row = latest.dropna(subset=["gold_share_pct"]).nlargest(1, "gold_share_pct").iloc[0]
        top_val_row   = top15.iloc[-1]  # sorted ascending, so last = largest value
        st.info(
            f"**Notable pattern:** {top_share_row['country']} has the highest gold concentration "
            f"({top_share_row['gold_share_pct']:.1f}% of its total reserves in gold), while the largest "
            f"absolute holder ({top_val_row['country']}) holds the most by value. "
            "Both measures reflect different reserve strategies — the former signals structural dependency on gold, "
            "the latter reflects sheer reserve scale."
        )

    with col_right:
        st.subheader("📊 Global Accumulation Rate Over Time")
        st.caption("Share of central banks actively increasing gold holdings each year — spikes align with major geopolitical and financial shocks")

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

        events = [
            (2008, "GFC"), (2011, "EU Debt Crisis"),
            (2014, "Crimea"), (2020, "COVID"),
            (2022, "Russia<br>Sanctions"), (2023, "US Rates Peak")
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
        # Dynamic insight from accumulation rate data
        peak_rate_row  = accum_yr.loc[accum_yr["rate"].idxmax()]
        latest_rate    = accum_yr.iloc[-1]["rate"]
        post22_avg     = accum_yr[accum_yr["year"] >= 2022]["rate"].mean()
        st.info(
            f"**Key Trend:** The share of central banks actively buying gold peaked at "
            f"**{peak_rate_row['rate']:.0f}%** in {int(peak_rate_row['year'])}. "
            f"Since the 2022 Russia sanctions shock, the average has held at **{post22_avg:.0f}%** — "
            f"well above the pre-2014 norm, reflecting a structural shift rather than a cyclical one. "
            f"In {latest_year}, **{latest_rate:.0f}%** of tracked central banks were accumulating."
        )

    st.markdown("---")

    map_tab, heat_tab = st.tabs([
        f"🗺️ World Gold Reserve Map ({latest_year})",
        "📈 Accumulation Heatmap (Top 20 Countries, 2015–2025)"
    ])

    with map_tab:
        st.caption("Gold as a share of each country's total foreign exchange reserves. Countries in darker gold are structurally more dependent on gold — often a signal of reduced confidence in USD-denominated assets.")
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
            # Dynamic geographic insight
            high_share = map_df[map_df["gold_share_pct"] >= 30]
            st.caption(
                f"**{len(high_share)} countries** hold more than 30% of their reserves in gold — "
                f"a threshold that signals deliberate de-dollarization strategy rather than passive allocation. "
                "Hover over any country to see its gold value, buying streak, and geopolitical risk tier."
            )
        except Exception as e:
            st.info(f"Map unavailable: {e}")

    with heat_tab:
        st.caption(
            "10-year view of gold's share of reserves for the world's top 20 holders. "
            "Brightening rows signal consistent accumulation — darkening rows signal strategic reduction or reserve drawdown."
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
            # Dynamic heatmap insight — find brightening rows (countries with rising share)
            base_year = latest_year - 3
            if latest_year in heat_df.columns and base_year in heat_df.columns:
                heat_df["delta"] = heat_df[latest_year] - heat_df[base_year]
                risers  = heat_df[heat_df["delta"] > 2].index.tolist()
                fallers = heat_df[heat_df["delta"] < -2].index.tolist()
                if risers:
                    st.caption(
                        f"**Rising (brightening rows — increased gold share {base_year}→{latest_year}):** "
                        f"{', '.join(risers[:5])}{'…' if len(risers) > 5 else ''}. "
                        + (f"**Declining:** {', '.join(fallers[:3])}." if fallers else "No major declines.")
                    )
        except Exception as e:
            st.info(f"Heatmap unavailable: {e}")


elif page == "📉 Gold vs USD":
    st.title("📉 Gold Accumulation vs USD Dominance")
    st.markdown(
        "Since 2001, the US dollar's share of global foreign exchange reserves has fallen from "
        "**~73% to under 57%** — while the world's gold holdings have more than doubled in value. "
        "This page investigates whether that inverse relationship is structural or coincidental."
    )

    world_trend = df.groupby("year").agg(
        usd_share=("usd_share_of_reserves_pct", "first"),   # global constant — same for all rows in a year
        world_gold_share=("world_gold_share_pct", "first"),
        world_gold_bn=("world_gold_value_bn", "first"),
    ).reset_index().dropna()

    st.subheader("25-Year Trend: USD Falling, Gold Rising")
    st.caption("Read together, these two charts tell the reserve diversification story. As the dollar's global dominance erodes, central banks have steadily increased their gold allocation.")

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
    # Dynamic insight from computed trend data
    peak_usd_val   = world_trend["usd_share"].max()
    latest_usd_val = world_trend["usd_share"].iloc[-1]
    usd_drop       = peak_usd_val - latest_usd_val
    latest_gs      = world_trend["world_gold_share"].iloc[-1]
    earliest_gs    = world_trend["world_gold_share"].iloc[0]
    gs_gain        = latest_gs - earliest_gs
    st.info(
        f"**The divergence in numbers:** The USD's global reserve share has fallen **{usd_drop:.1f} percentage points** "
        f"from its peak of {peak_usd_val:.1f}%. Over the same period, the world gold share has risen by "
        f"**{gs_gain:.1f} percentage points** to {latest_gs:.1f}%. "
        "The pace accelerated after 2022 when the freezing of Russia's USD reserves sent a clear signal to every central bank holding dollar assets."
    )
    st.caption(
        "Note: The two charts share the same x-axis (year). Reading them in tandem shows the inverse relationship — "
        "as the blue line trends down, the gold line trends up."
    )

    st.markdown("---")

    st.subheader("Confirming the Inverse Relationship (2000–2025)")
    st.caption("Each dot represents one year. The downward trend confirms that years with lower USD dominance correspond to higher global gold allocations — a pattern that has strengthened post-2014.")

    scatter_df = world_trend.dropna(subset=["usd_share", "world_gold_share"]).copy()

    # Compute OLS trend line manually with NumPy (no statsmodels dependency)
    x_vals = scatter_df["usd_share"].values
    y_vals = scatter_df["world_gold_share"].values
    m, b   = np.polyfit(x_vals, y_vals, 1)
    x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
    y_line = m * x_line + b
    r      = np.corrcoef(x_vals, y_vals)[0, 1]  # Pearson correlation

    fig_scatter = go.Figure()

    # Scatter dots — color encodes year for time direction
    fig_scatter.add_trace(go.Scatter(
        x=scatter_df["usd_share"],
        y=scatter_df["world_gold_share"],
        mode="markers+text",
        text=scatter_df["year"].astype(str),
        textposition="top center",
        textfont=dict(size=9, color=GREY),
        marker=dict(
            size=10,
            color=scatter_df["year"],
            colorscale=[[0, "#1A2332"], [0.5, BLUE], [1, GOLD]],
            colorbar=dict(
                title=dict(text="Year", font=dict(color="white")),
                tickfont=dict(color="white"),
                thickness=12
            ),
            showscale=True,
        ),
        hovertemplate=(
            "Year %{text}<br>"
            "USD Share: %{x:.1f}%<br>"
            "Gold Share: %{y:.2f}%<extra></extra>"
        ),
        name="Year",
    ))

    # Trend line
    fig_scatter.add_trace(go.Scatter(
        x=x_line, y=y_line,
        mode="lines",
        line=dict(color=RED, width=2, dash="dash"),
        name=f"OLS trend (r = {r:.2f})",
        hoverinfo="skip",
    ))

    fig_scatter.update_layout(
        **dark_layout(height=440, t=20, b=50),
        xaxis_title="USD Share of Global Reserves (%)",
        yaxis_title="World Gold Share (%)",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.info(
        f"**Statistical finding:** Pearson correlation r = **{r:.2f}** — a strong inverse relationship between USD dominance and gold allocation. "
        f"Each point is one year (labeled). Points in the **bottom-right** (high USD share, low gold) represent the early 2000s; "
        f"points in the **top-left** (low USD share, high gold) are recent years — "
        "the trajectory has moved consistently in one direction for 25 years."
    )
    st.caption(
        "Dashed red line = OLS regression (ordinary least squares). "
        "Dots are color-graded by year: dark blue = 2000, gold = most recent. "
        "Hover any dot to see exact values."
    )

    st.markdown("---")

    st.subheader("Country-Level Gold Strategy — Select & Compare")
    st.caption("Drill into individual countries to compare their gold accumulation trajectories. Rapid rises often coincide with sanctions events, currency crises, or shifts in foreign policy alignment.")

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
        # Dynamic: highlight the fastest accumulator among selected
        latest_sel = df[(df["country"].isin(selected)) & (df["year"] == latest_year)][
            ["country", "gold_share_pct", "accumulation_streak"]
        ].dropna().sort_values("gold_share_pct", ascending=False)
        if len(latest_sel):
            top_sel = latest_sel.iloc[0]
            st.caption(
                f"**Among your selection in {latest_year}:** {top_sel['country']} leads with "
                f"{top_sel['gold_share_pct']:.1f}% gold share. "
                "A steep upward slope signals an active accumulation policy — "
                "a flat or declining line indicates reserves are growing in other asset classes faster than gold."
            )
    else:
        st.info("Select at least one country above.")


elif page == "🌐 Geopolitics":
    st.title("🌐 Geopolitical Risk & Gold Accumulation")
    st.markdown(
        "Gold is increasingly being used as a **geopolitical hedge**, not just a financial one. "
        "Countries facing Western sanctions, high instability, or divergence from US foreign policy "
        "hold significantly more gold as a share of reserves — and have been buying for longer. "
        "This page quantifies that relationship."
    )

    geo_df = df[df.year == latest_year].dropna(subset=["sanctions_score", "gold_share_pct"])

    # ── KPI row ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    sanc2_avg  = geo_df[geo_df.sanctions_score >= 2]["gold_share_pct"].mean()
    sanc0_avg  = geo_df[geo_df.sanctions_score == 0]["gold_share_pct"].mean()
    div_streak = geo_df[geo_df.geo_bloc == "us_divergent"]["accumulation_streak"].mean()
    all_streak = geo_df["accumulation_streak"].mean()

    # Guard against NaN (e.g. no sanctioned countries in panel)
    sanc2_avg  = sanc2_avg  if not pd.isna(sanc2_avg)  else 0.0
    sanc0_avg  = sanc0_avg  if not pd.isna(sanc0_avg)  else 0.0
    div_streak = div_streak if not pd.isna(div_streak) else 0.0
    all_streak = all_streak if not pd.isna(all_streak) else 0.0

    col1.metric("Heavily Sanctioned Avg Gold Share",
                f"{sanc2_avg:.1f}%",
                f"{sanc2_avg - sanc0_avg:+.1f}pp vs non-sanctioned")
    col2.metric("US-Divergent Avg Buying Streak",
                f"{div_streak:.1f} yrs",
                f"{div_streak - all_streak:+.1f}yr vs panel avg")
    col3.metric("Countries w/ Any Sanctions",
                f"{int((geo_df.sanctions_score >= 1).sum())}",
                f"out of {len(geo_df)} in panel")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Sanctions Exposure vs Gold Share")
        st.caption(
            f"Average gold share rises sharply with sanctions severity. "
            f"Dashed line = baseline for countries with no sanctions ({sanc0_avg:.1f}%). Data: {latest_year}."
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
        # Reference line shows the non-sanctioned baseline
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
        multiplier = f"{sanc2_avg / sanc0_avg:.1f}×" if sanc0_avg > 0 else "significantly higher"
        st.info(
            f"**Key Finding:** Countries under significant sanctions hold an average of "
            f"**{sanc2_avg:.1f}%** of reserves in gold — "
            f"**{multiplier}** the {sanc0_avg:.1f}% baseline for non-sanctioned countries. "
            "This is the single strongest structural predictor of gold accumulation in the model. "
            "When a country cannot rely on dollar-denominated assets being accessible, gold becomes the default safe haven."
        )
        st.caption(
            "Sanctions score: 0 = no active sanctions, 1 = partial/targeted, 2 = significant (sector-wide), 3 = severe (near-comprehensive). "
            "Source: OFAC designations database."
        )

    with col_b:
        st.subheader("Political Alignment vs Gold Strategy")
        st.caption(
            "Countries that vote against the US in the UN General Assembly (low alignment score) "
            "tend to hold far more gold. Bubble size = consecutive years of gold buying. "
            f"Data: {latest_year}."
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

        bloc_labels = {
            "us_divergent": "🔴 US-Divergent",
            "neutral":      "🟡 Neutral",
            "US_allied":    "🔵 US-Allied",
            "ally":         "🔵 US-Allied",
        }
        fig_geo = go.Figure()
        for bloc, grp in scatter_geo.groupby("geo_bloc"):
            fig_geo.add_trace(go.Scatter(
                x=grp["un_alignment_score"],
                y=grp["gold_share_pct"],
                mode="markers",
                name=bloc_labels.get(bloc, bloc),
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
        # Dynamic: find top divergent country
        div_grp = scatter_geo[scatter_geo["geo_bloc"] == "us_divergent"].nlargest(1, "gold_share_pct")
        if len(div_grp):
            top_div = div_grp.iloc[0]
            st.info(
                f"**Pattern:** Countries in the **top-left** quadrant (politically divergent, high gold share) "
                f"include {top_div['country']} with {top_div['gold_share_pct']:.1f}% gold share and a "
                f"{int(top_div.get('accumulation_streak', 0))}-year buying streak. "
                "Bubble size reflects consecutive years of accumulation — larger bubbles in the top-left indicate "
                "both political motivation and sustained buying behavior."
            )
        st.caption(
            "Color legend: 🔴 Red = US-divergent bloc · 🟡 Gold = neutral · 🔵 Blue = US-allied. "
            "UN Alignment Score: 0 = votes against US positions on most issues, 100 = votes with US on most issues. "
            "Source: UN General Assembly voting records."
        )

    st.markdown("---")
    st.subheader(f"Full Country Geopolitical Profile ({latest_year})")
    st.caption("Filter by risk tier or bloc to isolate specific country groups. Sorted by gold share — the primary indicator of strategic reserve intent.")

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
    geo_table.columns = ["Country", "Geo Bloc", "Risk Tier", "Sanctions", "UN Alignment", "Gold Share %", "Streak (yrs)"]
    geo_table["Gold Share %"] = geo_table["Gold Share %"].round(1)
    st.dataframe(geo_table, use_container_width=True, height=380)

    # ── Column glossary ───────────────────────────────────────────────────────
    st.markdown("**📖 Column Guide**")
    g1, g2, g3 = st.columns(3)
    with g1:
        st.caption("**Geo Bloc** — Political alignment grouping based on UN voting patterns: *us_divergent* = votes against US on most resolutions, *US_allied* = votes with US, *neutral* = mixed record.")
        st.caption("**Risk Tier** — Composite geopolitical risk level (high / medium / low) derived from political stability, conflict exposure, and sanctions history.")
    with g2:
        st.caption("**Sanctions (0–3)** — OFAC sanctions exposure: 0 = none, 1 = targeted/partial, 2 = significant sector sanctions, 3 = near-comprehensive. Higher = stronger structural incentive to hold non-USD assets.")
        st.caption("**UN Alignment** — Score from 0 (votes against US on almost every resolution) to 100 (votes with US on almost every resolution). Based on UN General Assembly roll-call data.")
    with g3:
        st.caption("**Gold Share %** — Gold's percentage of the country's total foreign exchange reserves in the latest year. Values above 30% indicate deliberate reserve diversification away from the dollar.")
        st.caption("**Streak (yrs)** — Consecutive years of increasing gold allocation. A streak of 5+ years signals policy-driven intent rather than opportunistic buying triggered by price movements.")


elif page == "📰 Sentiment":
    st.title("📰 Market Narrative & Sentiment")
    st.markdown(
        "Central bank decisions don't happen in a vacuum — they are shaped by global narratives "
        "around dollar confidence, sanctions risk, and de-dollarization. "
        "This page tracks those narratives in real time, surfacing the news signals that tend to precede gold accumulation shifts."
    )

    import requests
    from datetime import datetime

    GDELT_QUERIES = {
        "🏦 Central Bank Gold Buying": "central+bank+gold+reserves+buying",
        "💵 De-Dollarization":         "de-dollarization+dollar+reserves",
        "⚠️  Sanctions & Gold":        "sanctions+gold+reserves+central+bank",
    }

    # Bullish = positive signal for gold accumulation
    # Bullish signals for gold — unambiguous buying/demand language
    # Multi-word phrases used for context-sensitive cases (e.g. dollar weakness, rate cuts)
    POSITIVE_WORDS = [
        # Direct gold buying/demand
        "buy", "bought", "purchase", "purchases", "buying",
        "increase", "increased", "increases", "boost", "boosted",
        "surge", "surged", "surging",
        "rise", "rises", "rose", "rising",
        "accumulate", "accumulated", "accumulation",
        "add", "adds", "added",
        "demand", "inflow", "inflows",
        "rally", "rallied",
        "gain", "gains", "gained",
        "jump", "jumped",
        "climb", "climbed",
        "soar", "soared", "soaring",
        "rebound", "rebounded",
        # Safe-haven / geopolitical drivers (always bullish for gold)
        "safe haven", "safe-haven",
        "hedge", "hedging",
        "geopolitical", "uncertainty", "conflict",
        "sanction", "sanctions",
        "de-dollarization", "dedollarization", "dedollar",
        "diversif",        # matches diversify/diversification
        "stockpile", "hoard",
        # Dollar weakness phrases (dollar falling = gold bullish)
        "dollar weakness", "dollar falls", "dollar drops", "dollar declines",
        "dollar slump", "weaker dollar", "weak dollar", "dollar loses",
        "dollar sell", "dollar tumble", "dollar at risk",
        "de-dollar", "away from dollar", "bypass dollar", "dump dollar",
        # Monetary easing = gold bullish
        "rate cut", "rate cuts", "interest rate cut", "easing",
        "lower rates", "quantitative easing",
    ]
    # Bearish signals for gold — unambiguous selling/decline language
    NEGATIVE_WORDS = [
        # Direct gold selling/decline
        "sell", "sold", "selling",
        "decline", "declined", "declining", "declines",
        "drop", "drops", "dropped", "dropping",
        "reduce", "reduces", "reduced", "reducing",
        "outflow", "outflows",
        "plunge", "plunged", "plunging",
        "slump", "slumped",
        "crash", "crashed",
        "tumble", "tumbled",
        "retreat", "retreated",
        "shrink", "shrinks",
        "bearish",
        # Dollar strength phrases (strong dollar = gold bearish)
        "dollar strength", "dollar rallies", "dollar surges", "strong dollar",
        "dollar gains", "dollar rises", "dollar at high",
        # Monetary tightening = gold bearish
        "rate hike", "rate hikes", "interest rate hike", "tightening", "hawkish",
    ]
    GOLD_WORDS    = ["gold", "reserve", "bullion", "tonne", "troy", "precious metal"]
    USD_NEG_WORDS = ["de-dollar", "dedollar", "dollar decline", "dollar weakness",
                     "away from dollar", "bypass dollar", "dollar dominance fades",
                     "ditch dollar", "dump dollar", "dollar crisis"]

    def score_sentiment(text):
        t    = text.lower()
        pos  = sum(1 for w in POSITIVE_WORDS if w in t)
        neg  = sum(1 for w in NEGATIVE_WORDS if w in t)
        gold = sum(1 for w in GOLD_WORDS if w in t)
        usd  = sum(1 for w in USD_NEG_WORDS if w in t)
        # Net score: positive = bullish for gold, negative = bearish
        net = pos - neg
        if net > 0:
            score = min(1.0,  0.2 + net * 0.15)
        elif net < 0:
            score = max(-1.0, -0.2 + net * 0.15)
        else:
            # Tie / no keywords — gold-context headlines default slightly bullish
            score = 0.15 if gold > 0 else 0.0
        return round(score, 2), gold, usd

    # ── RSS fallback feeds (open, no auth required) ───────────────────────────
    RSS_FEEDS = {
        "🏦 Central Bank Gold Buying": [
            "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
            "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        ],
        "💵 De-Dollarization": [
            "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml",
            "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
        ],
        "⚠️  Sanctions & Gold": [
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
        ],
    }

    # Keywords to filter RSS articles by topic
    RSS_KEYWORDS = {
        "🏦 Central Bank Gold Buying":  ["gold", "central bank", "reserve", "bullion"],
        "💵 De-Dollarization":          ["dollar", "currency", "reserve", "yuan", "de-dollar"],
        "⚠️  Sanctions & Gold":         ["sanction", "gold", "russia", "iran", "freeze"],
    }

    def fetch_gdelt_news(query, max_records=12):
        """Try GDELT with progressively wider timespans. Returns (articles, source_label)."""
        import urllib.parse
        encoded = urllib.parse.quote(query.replace("+", " "))
        headers = {"User-Agent": "Mozilla/5.0 (compatible; GoldDashboard/1.0)"}

        for timespan in ("48h", "1week", "2week", "1month"):
            url = (
                f"https://api.gdeltproject.org/api/v2/doc/doc"
                f"?query={encoded}&mode=artlist&maxrecords={max_records}"
                f"&format=json&sort=DateDesc&timespan={timespan}"
            )
            try:
                r = requests.get(url, timeout=15, headers=headers)
                if r.status_code != 200:
                    continue
                # GDELT sometimes returns an HTML error page instead of JSON
                text = r.text.strip()
                if not text.startswith("{"):
                    continue
                data     = r.json()
                articles = data.get("articles") or []
                if articles:
                    return articles, f"GDELT · last {timespan}"
            except Exception:
                continue
        return [], None

    def fetch_rss_fallback(label):
        """Parse open RSS feeds and keyword-filter by topic."""
        import xml.etree.ElementTree as ET
        keywords = [k.lower() for k in RSS_KEYWORDS.get(label, [])]
        results  = []

        for feed_url in RSS_FEEDS.get(label, []):
            try:
                r = requests.get(
                    feed_url, timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                root = ET.fromstring(r.content)
                for item in root.iter("item"):
                    t_el = item.find("title")
                    l_el = item.find("link")
                    d_el = item.find("pubDate")
                    if t_el is None or not t_el.text:
                        continue
                    title = t_el.text.strip()
                    # Only include if at least one keyword matches
                    if keywords and not any(kw in title.lower() for kw in keywords):
                        continue
                    results.append({
                        "title":    title,
                        "url":      l_el.text.strip() if l_el is not None else "#",
                        "domain":   feed_url.split("/")[2],
                        "seendate": d_el.text.strip() if d_el is not None else "",
                    })
            except Exception:
                continue

        return results[:12]

    def parse_date(seendate):
        """Parse either GDELT (YYYYMMDDHHmmss) or RSS (RFC 2822) date strings."""
        if not seendate:
            return "—"
        s = seendate.strip()
        # GDELT compact formats — slice to exact expected length
        for fmt, length in [("%Y%m%d%H%M%S", 14), ("%Y%m%d", 8)]:
            try:
                return datetime.strptime(s[:length], fmt).strftime("%b %d, %Y")
            except Exception:
                continue
        # RSS / RFC-2822 formats — parse full string (length varies)
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT",
                    "%d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(s, fmt).strftime("%b %d, %Y")
            except Exception:
                continue
        return s[:10]  # fallback: return first 10 chars as-is

    def render_article(art):
        """Render one article card and return scored dict."""
        title         = art.get("title") or "No title"
        url_art       = art.get("url")   or "#"
        source        = art.get("domain") or "Unknown"
        dt            = parse_date(art.get("seendate", ""))
        score, gold_hits, usd_neg_hits = score_sentiment(title)
        badge = "🟢 Bullish" if score > 0.1 else ("🔴 Bearish" if score < -0.1 else "⚪ Neutral")

        st.markdown(
            f"**[{title}]({url_art})**  \n"
            f"📰 {source} · 📅 {dt} · {badge}"
            + (f" · 🥇 Gold signal: {gold_hits}"    if gold_hits    > 0 else "")
            + (f" · 💵 De-$ signal: {usd_neg_hits}" if usd_neg_hits > 0 else "")
        )
        st.divider()
        return {"title": title, "source": source, "score": score,
                "gold_hits": gold_hits, "usd_neg": usd_neg_hits}

    # ── Refresh button clears stale cache ────────────────────────────────────
    col_hdr, col_btn = st.columns([4, 1])
    with col_hdr:
        st.subheader("📡 Live News Feed")
        st.caption("Real-time global news scored for bullish or bearish signals on gold and the US dollar — refreshed automatically every 15 minutes")
    with col_btn:
        if st.button("🔄 Refresh", help="Force-fetch fresh articles"):
            st.cache_data.clear()
            st.rerun()

    @st.cache_data(ttl=900)   # 15-minute cache so retries aren't frozen for an hour
    def cached_gdelt(query):
        return fetch_gdelt_news(query, max_records=12)

    @st.cache_data(ttl=900)
    def cached_rss(label):
        return fetch_rss_fallback(label)

    tabs = st.tabs(list(GDELT_QUERIES.keys()))
    all_articles = []

    for tab, (label, query) in zip(tabs, GDELT_QUERIES.items()):
        with tab:
            with st.spinner("Fetching latest news…"):
                articles, src_label = cached_gdelt(query)

            if not articles:
                articles   = cached_rss(label)
                src_label  = "RSS fallback" if articles else None

            if src_label:
                st.caption(f"📡 {src_label} · {len(articles)} articles")
            else:
                st.warning(
                    "No articles found right now. "
                    "Click **🔄 Refresh** above to try again, "
                    "or check back in a few minutes."
                )

            for art in articles:
                try:
                    scored = render_article(art)
                    scored["query"] = label
                    all_articles.append(scored)
                except Exception:
                    continue   # skip any malformed article silently

    # ── Sentiment summary ─────────────────────────────────────────────────────
    if all_articles:
        st.markdown("---")
        st.subheader("📊 Sentiment Distribution — Live Articles")
        st.caption(
            "Breakdown of current news coverage into bullish, neutral, and bearish signals "
            "— giving an instant read on market sentiment toward gold and the US dollar."
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
            yaxis=dict(range=[0, max(max(bullish, neutral, bearish), 1) * 1.4]),
        )
        st.plotly_chart(fig_sent, use_container_width=True)
        # Dynamic signal callout based on live article data
        if bullish > bearish and bullish > neutral:
            st.success(
                f"**Current Signal: Bullish 🟢** — {bullish} of {len(art_df)} live articles carry positive signals for gold. "
                "Dominant bullish coverage typically precedes or coincides with renewed central bank buying cycles. "
                f"Average sentiment score: **{avg_sc:+.2f}** (scale: −1.0 bearish → +1.0 bullish)."
            )
        elif bearish > bullish and bearish > neutral:
            st.warning(
                f"**Current Signal: Bearish 🔴** — {bearish} of {len(art_df)} live articles carry negative signals. "
                "This may reflect near-term dollar strength or reduced urgency among central banks. "
                f"Average sentiment score: **{avg_sc:+.2f}**."
            )
        else:
            st.info(
                f"**Current Signal: Mixed/Neutral ⚪** — Sentiment is split ({bullish} bullish, {bearish} bearish, {neutral} neutral). "
                "Mixed readings often appear during transitional periods — watch for a directional shift in the coming weeks. "
                f"Average sentiment score: **{avg_sc:+.2f}**."
            )
        st.caption(
            "Scores are computed from headline text using a financial keyword lexicon. "
            "🟢 Bullish = net positive language (buy, surge, increase, record…) · "
            "🔴 Bearish = net negative language (sell, drop, decline, weak…) · "
            "⚪ Neutral = balanced or no strong signal. Each article scored independently."
        )

    st.markdown("---")

    # ── Historical NLP trend ──────────────────────────────────────────────────
    st.subheader("📈 Historical USD Sentiment Trend (2000–2025)")
    st.caption(
        "Twenty-five years of financial media coverage reveals how global confidence in the US dollar "
        "has shifted — a leading indicator for central bank reserve diversification decisions."
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
        # Dynamic NLP trend insight
        if len(nlp_global) >= 5:
            peak_neg_idx = nlp_global["usd_neg"].idxmax()
            peak_neg_yr  = int(nlp_global.loc[peak_neg_idx, "year"])
            peak_neg_val = nlp_global.loc[peak_neg_idx, "usd_neg"]
            early_neg    = nlp_global[nlp_global["year"] <= 2010]["usd_neg"].mean()
            recent_neg   = nlp_global[nlp_global["year"] >= 2020]["usd_neg"].mean()
            st.info(
                f"**Historical shift:** Negative USD sentiment peaked in **{peak_neg_yr}** at **{peak_neg_val:.1f}%** of articles. "
                f"The 2020–{latest_year} average of **{recent_neg:.1f}%** is significantly higher than the 2000–2010 baseline of **{early_neg:.1f}%**, "
                "reflecting a sustained structural deterioration in global dollar confidence — not a temporary spike. "
                "When negative sentiment stays elevated over multiple years, it tends to precede multi-year central bank accumulation cycles."
            )
            st.caption(
                "This data is derived from the historical NLP pipeline applied to the GDELT news corpus (2000–2025). "
                "A rising red band = growing share of global financial media expressing concern about USD dominance. "
                "Green line = positive USD coverage — watch for divergence between the two lines."
            )
    else:
        st.info("Historical NLP data not available.")

    with st.expander("📖 About This Analysis"):
        st.markdown("""
        **Live news feed:** Articles are pulled in real time from the GDELT global news index —
        one of the largest open-source media databases in the world, covering 200+ countries and 65 languages.

        **Sentiment signals:** Each article is classified as bullish, neutral, or bearish based on
        financial language patterns. These signals help identify narrative shifts before they appear
        in official reserve data — giving analysts an early-warning layer.

        **Why it matters:** Central banks rarely announce reserve strategy changes in advance.
        Media narratives around de-dollarization and sanctions tend to precede actual reserve moves,
        making sentiment a valuable forward-looking signal.
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — ML PREDICTIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 ML Predictions":
    max_data_year = int(df["year"].max())
    predict_year  = max_data_year + 1
    st.title(f"🤖 ML Predictions: Top Gold Accumulators {predict_year}")
    st.markdown(
        f"Which central banks are most likely to increase gold reserves in {predict_year}?  \n"
        f"This model scores **{len(scores)} countries** across four evidence-based pillars — "
        f"physical buying momentum, consistency, geopolitical motivation, and strategic allocation gap — "
        f"to surface the strongest forward-looking signals in the global gold market."
    )

    top10 = scores.head(10).copy()

    # ── View 1: Sorted horizontal bar — top 10 ────────────────────────────────
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

    # ── Key Insight callout — dynamic, drawn from live data ───────────────────
    sanctioned_top5  = sum(1 for _, r in top10.head(5).iterrows() if r.get("sanctions_score", 0) >= 1)
    high_geo_top5    = sum(1 for _, r in top10.head(5).iterrows() if str(r.get("geo_risk_tier","")).lower() == "high")
    top_country      = top10.iloc[0]["country"] if len(top10) else "N/A"
    top_score        = top10.iloc[0]["gold_accumulation_score"] if len(top10) else 0
    top_streak       = int(top10.iloc[0].get("accumulation_streak", 0)) if len(top10) else 0

    st.info(
        f"**🔍 Key Insight —** {sanctioned_top5} of the top 5 predicted buyers carry active sanctions or "
        f"high geopolitical exposure, signalling that **structural de-dollarization** — not just price appreciation — "
        f"is the primary driver of reserve diversification. "
        f"**{top_country}** leads with a score of **{top_score:.0f}/100** and a **{top_streak}-year** consecutive buying streak."
    )
    st.caption(
        "Color indicates the primary driver: 🔴 Red = country faces heavy sanctions (strong incentive to hold non-USD assets), "
        "🟠 Orange = elevated geopolitical risk, 🔵 Blue = strong fundamental buying momentum. "
        "Score range: 0 (no signal) → 100 (strongest predicted accumulator)."
    )

    st.markdown("---")

    # ── View 2: 4-Pillar breakdown ────────────────────────────────────────────
    st.subheader("📊 What Drives Each Country's Score? — 4-Pillar Breakdown")
    st.markdown(
        "The composite score is built from four independent pillars. "
        "Reading across a country's four bars reveals *why* it ranks where it does — "
        "whether the signal is recent buying activity, long-term consistency, geopolitical pressure, or an under-allocated reserve base."
    )

    PILLAR_DESCRIPTIONS = {
        "pillar_momentum":    ("🏋️ Physical Buying Momentum", "30% weight",
                               "Measures actual tonnage purchased in the latest year (price-neutral). "
                               "Countries topping this pillar are actively buying right now."),
        "pillar_consistency": ("🔁 Buying Consistency", "25% weight",
                               "Rewards sustained, repeated buying over 5 years. "
                               "A high score here means the country doesn't just buy once — it keeps buying."),
        "pillar_geo":         ("🌐 Geopolitical Motivation", "25% weight",
                               "Combines UN voting divergence from the US and sanctions exposure. "
                               "High scorers have a structural reason to reduce dollar dependency."),
        "pillar_alloc":       ("📐 Strategic Allocation Gap", "20% weight",
                               "Countries holding less gold than global peers have the most room to grow. "
                               "A rising 3-year trend in gold share adds further conviction."),
    }

    pillar_cols = {
        "Pillar 1: Physical Buying Momentum": "pillar_momentum",
        "Pillar 2: Buying Consistency":       "pillar_consistency",
        "Pillar 3: Geopolitical Motivation":  "pillar_geo",
        "Pillar 4: Strategic Allocation Gap": "pillar_alloc",
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
                # Per-pillar description below each chart
                pinfo = PILLAR_DESCRIPTIONS.get(pillar_col)
                if pinfo:
                    st.markdown(f"**{pinfo[0]}** · *{pinfo[1]}*")
                    st.caption(pinfo[2])

        st.caption(
            "Showing top 5 countries only. Scores are percentile-ranked (0–100) within the full panel. "
            "A missing bar means the country lacks sufficient data for that pillar."
        )
    else:
        st.info("Pillar breakdown not yet in scores CSV. Re-run src/ml/score_countries.py to generate.")

    # ── View 3: Full ranking table + filter ───────────────────────────────────
    st.markdown("---")
    st.subheader(f"📋 Full Country Ranking — {len(scores)} Countries")
    st.markdown(
        "Every country in the panel ranked by predicted gold accumulation likelihood for "
        f"**{predict_year}**. Use the filters below to drill into specific risk tiers or score thresholds."
    )

    show_cols = [
        "country", "gold_accumulation_score", "gold_share_pct", "gold_tonnes_yoy",
        "accumulation_streak", "buy_frequency_5yr", "sanctions_score", "geo_risk_tier", "geo_bloc",
    ]
    show_cols = [c for c in show_cols if c in scores.columns]
    disp = scores[show_cols].copy()

    # Human-readable column names
    col_rename = {
        "country":                "Country",
        "gold_accumulation_score":"Score (0–100)",
        "gold_share_pct":         "Gold % of Reserves",
        "gold_tonnes_yoy":        "Tonnes Bought (YoY)",
        "accumulation_streak":    "Buying Streak (yrs)",
        "buy_frequency_5yr":      "Buys in Last 5 yrs",
        "sanctions_score":        "Sanctions (0–3)",
        "geo_risk_tier":          "Geo Risk",
        "geo_bloc":               "Alignment Bloc",
    }
    disp = disp.rename(columns={c: col_rename.get(c, c) for c in disp.columns})

    f1, f2 = st.columns(2)
    with f1:
        risk_f = st.selectbox("Filter by Geo Risk Tier:", ["All", "high", "medium", "low"])
    with f2:
        score_min = st.slider("Minimum Score:", 0, 100, 0)

    if risk_f != "All" and "Geo Risk" in disp.columns:
        disp = disp[disp["Geo Risk"] == risk_f]
    if "Score (0–100)" in disp.columns:
        disp = disp[disp["Score (0–100)"] >= score_min]

    disp.index = range(1, len(disp) + 1)
    st.dataframe(disp, use_container_width=True, height=430)

    # ── Column glossary ───────────────────────────────────────────────────────
    st.markdown("**📖 Column Guide**")
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        st.caption("**Score (0–100)** — Overall predicted likelihood of increasing gold reserves next year. Higher = stronger signal across all four pillars.")
        st.caption("**Gold % of Reserves** — Current share of gold in the country's total foreign reserves. Low values with rising trends indicate accumulation potential.")
    with col_g2:
        st.caption("**Tonnes Bought (YoY)** — Physical tonnage change in the latest year. Price-neutral metric — reflects actual buying decisions, not valuation changes.")
        st.caption("**Buying Streak (yrs)** — Consecutive years of increasing gold allocation. Long streaks indicate policy-driven, strategic intent rather than opportunistic buying.")
    with col_g3:
        st.caption("**Sanctions (0–3)** — Sanctions exposure level: 0 = none, 1 = partial, 2 = significant, 3 = severe. Sanctioned countries face direct structural incentive to hold non-USD assets.")
        st.caption("**Alignment Bloc** — Political alignment with the US based on UN General Assembly voting: *us_divergent* = votes against US positions most often.")

    with st.expander("📖 How Countries Are Scored"):
        st.markdown(f"""
        The model uses a transparent 4-pillar framework, weighting each factor by its predictive
        relevance to future gold accumulation. Scores are intentionally price-neutral — they reflect
        behavioral and structural signals rather than reacting to short-term gold price movements.

        | Pillar | Weight | What It Measures |
        |--------|--------|-----------------|
        | Physical Buying Momentum | 30% | Recent tonnage growth and gold share change |
        | Buying Consistency | 25% | Sustained accumulation streak and multi-year buy frequency |
        | Geopolitical Motivation | 25% | Sanctions exposure and UN political alignment divergence |
        | Strategic Allocation Gap | 20% | How underweight gold the country is vs. global peers |

        **Validation period:** 2020–{max_data_year} · **Target:** Gold share increase year-over-year
        """)

    # ── Model Performance Metrics ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📐 Model Performance — Validation Results")
    st.markdown(
        f"The scoring model was validated against known gold-buying behaviour from 2020 to {max_data_year}. "
        "Three approaches were benchmarked — Logistic Regression, Gradient Boosting, and an Ensemble — "
        "with Gradient Boosting achieving the strongest predictive signal. "
        "The 4-pillar rule system was calibrated against these results."
    )

    if not model_metrics.empty:
        # Format for display
        disp_metrics = model_metrics.copy()
        rename_map = {
            "model": "Model", "accuracy": "Accuracy", "precision": "Precision",
            "recall": "Recall", "f1": "F1 Score", "auc_roc": "AUC-ROC",
            "tp": "True Pos", "tn": "True Neg", "fp": "False Pos", "fn": "False Neg"
        }
        disp_metrics = disp_metrics.rename(columns={c: rename_map.get(c, c) for c in disp_metrics.columns})
        for col in ["Accuracy", "Precision", "Recall", "F1 Score", "AUC-ROC"]:
            if col in disp_metrics.columns:
                disp_metrics[col] = disp_metrics[col].map(lambda x: f"{x:.3f}")
        st.dataframe(disp_metrics, use_container_width=True, hide_index=True)
        st.caption(
            "**Accuracy** = % of predictions correct overall · "
            "**Precision** = of predicted buyers, how many actually bought · "
            "**Recall** = of actual buyers, how many were predicted · "
            "**F1** = harmonic mean of precision and recall · "
            "**AUC-ROC** = ability to rank buyers above non-buyers (0.5 = random, 1.0 = perfect). "
            "Gradient Boosting performs best across all metrics."
        )
    else:
        st.info("Model metrics file not found. Re-run `src/ml/train_model.py` to generate.")

    # ── Country Coverage Explainer ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔍 Data Coverage — Why Not All Countries Are Scored")
    total_panel   = df["country"].nunique()
    scored_n      = len(scores)
    filtered_out  = total_panel - scored_n
    st.markdown(
        f"The master panel covers **{total_panel} countries** (2000–{max_data_year}). "
        f"The scoring model evaluates **{scored_n} countries** after applying quality filters:"
    )
    cov1, cov2, cov3 = st.columns(3)
    cov1.metric("Countries in Master Panel", total_panel, "all tracked countries")
    cov2.metric("Countries Scored", scored_n, f"pass all quality filters")
    cov3.metric("Filtered Out", filtered_out, "below threshold or missing data")
    st.caption(
        "Filters applied: (1) Gold holdings ≥ $500M USD — removes micro-states and territories whose "
        "reserves are too small to reflect strategic decisions. "
        "(2) Non-null UN divergence score and sanctions data — countries missing geopolitical data "
        "cannot be scored on Pillar 3. "
        "(3) At least 3 years of gold holding history — required for trend and streak calculations."
    )


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#888; font-size:12px'>"
    "Gold Reserve Intelligence Platform · Python · World Bank API · IMF COFER · OFAC · UN Voting · GDELT · Sathwik Arroju"
    "</div>",
    unsafe_allow_html=True
)

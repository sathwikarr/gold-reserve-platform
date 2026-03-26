"""
Central Bank Gold Accumulation vs USD Power & Geopolitical Risk Platform
Interactive Streamlit Dashboard — V4

Run:
    pip install streamlit plotly pandas
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

# ── Data paths ────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
CURATED = BASE / "data" / "curated"
DOCS    = BASE / "docs"

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv(CURATED / "master_panel_nlp.csv")
    scores = pd.read_csv(CURATED / "ml_country_scores.csv")
    return df, scores

df, scores = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Gold_Bars.jpg/320px-Gold_Bars.jpg",
                 use_column_width=True)
st.sidebar.title("🏅 Gold Intelligence")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["🌍 Overview", "📉 Gold vs USD", "🌐 Geopolitics", "📰 Sentiment", "🤖 ML Predictions"],
    index=0
)

st.sidebar.markdown("---")
max_yr = int(df["year"].max())
st.sidebar.markdown(f"""
**Project:** Central Bank Gold Accumulation vs USD Power & Geopolitical Risk Platform
**Data:** World Bank · IMF COFER · OFAC · UN Voting · GDELT
**Model:** Logistic Regression + Gradient Boosting (from scratch)
**Period:** 2000–{max_yr} · {df['country'].nunique()} Countries
""")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🌍 Overview":
    st.title("🏅 Central Bank Gold Accumulation Platform")
    st.markdown("""
    > *Are countries increasing gold reserves due to declining trust in the US dollar and rising geopolitical risk?*

    This platform integrates **central bank data, geopolitical scores, sanctions exposure, and NLP-derived narratives**
    to analyze and predict country-level gold accumulation behavior.
    """)

    # KPI cards — use the latest year with data
    latest_year = int(df["year"].max())
    latest = df[df.year == latest_year]
    col1, col2, col3, col4 = st.columns(4)

    world_gold_bn = latest["world_gold_value_bn"].iloc[0] if len(latest) > 0 else 0
    accumulators = latest["is_accumulating"].sum()
    usd_drawdown = latest["usd_share_drawdown_pct"].mean()
    sanctioned = (latest["sanctions_score"] >= 1).sum()

    col1.metric("🌎 World Gold Reserves", f"${world_gold_bn/1000:.1f}T", f"{latest_year}")
    col2.metric("📈 Countries Accumulating", f"{int(accumulators)}", f"in {latest_year}")
    col3.metric("💵 Avg USD Drawdown", f"{usd_drawdown:.1f}%", "from peak")
    col4.metric("⚠️ Sanctioned Accumulators", f"{int(sanctioned)}", "countries")

    st.markdown("---")

    # Top 10 Gold Holders
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🏆 Top 10 Gold Holders (2023)")
        top_holders = (
            df[df.year == 2023]
            .nlargest(10, "gold_value_usd")
            [["country", "gold_value_usd", "gold_share_pct"]]
            .dropna()
        )
        top_holders["gold_value_usd"] = (top_holders["gold_value_usd"] / 1e9).round(1)
        top_holders.columns = ["Country", "Gold Value ($B)", "Gold Share (%)"]
        top_holders["Gold Share (%)"] = top_holders["Gold Share (%)"].round(1)
        top_holders.index = range(1, len(top_holders) + 1)
        st.dataframe(top_holders, use_container_width=True)

    with col_b:
        st.subheader("📊 Accumulation Rate by Year")
        accum_by_year = df.groupby("year").agg(
            accumulators=("is_accumulating", "sum"),
            total=("is_accumulating", "count")
        ).reset_index()
        accum_by_year["rate"] = (accum_by_year["accumulators"] / accum_by_year["total"] * 100).round(1)

        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=accum_by_year["year"], y=accum_by_year["rate"],
                mode="lines+markers", line=dict(color="#D4AF37", width=2.5),
                fill="tozeroy", fillcolor="rgba(212,175,55,0.15)",
                name="% Accumulating"
            ))
            fig.update_layout(
                xaxis_title="Year", yaxis_title="% of Countries Accumulating Gold",
                height=300, margin=dict(t=10, b=40),
                plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                font=dict(color="white"),
                yaxis=dict(range=[0, 100])
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.fill_between(accum_by_year["year"], accum_by_year["rate"], alpha=0.2, color="#D4AF37")
            ax.plot(accum_by_year["year"], accum_by_year["rate"], color="#D4AF37", linewidth=2)
            ax.set_xlabel("Year"); ax.set_ylabel("% Accumulating")
            ax.set_ylim(0, 100)
            st.pyplot(fig)

    # Chart images
    st.markdown("---")
    st.subheader("📈 Key Charts")
    img_col1, img_col2 = st.columns(2)
    with img_col1:
        if (DOCS / "top10_gold_holders.png").exists():
            st.image(str(DOCS / "top10_gold_holders.png"), caption="Top 10 Gold Holders", use_column_width=True)
    with img_col2:
        if (DOCS / "accumulation_heatmap.png").exists():
            st.image(str(DOCS / "accumulation_heatmap.png"), caption="Accumulation Heatmap by Country", use_column_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — GOLD vs USD
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📉 Gold vs USD":
    st.title("📉 Gold Accumulation vs USD Dominance")
    st.markdown("""
    The core thesis: as the **US dollar loses share of global reserves**, central banks diversify into **gold**.
    This page traces the relationship between USD dominance and global gold accumulation since 2000.
    """)

    # Global USD share vs world gold share
    world_trend = df.groupby("year").agg(
        usd_share=("usd_share_of_reserves_pct", "mean"),
        world_gold_share=("world_gold_share_pct", "first"),
        world_gold_bn=("world_gold_value_bn", "first"),
    ).reset_index().dropna()

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(
            x=world_trend["year"], y=world_trend["usd_share"],
            name="USD Share of Global Reserves (%)",
            line=dict(color="#4A90D9", width=2.5)
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=world_trend["year"], y=world_trend["world_gold_share"],
            name="World Gold Share (%)",
            line=dict(color="#D4AF37", width=2.5)
        ), secondary_y=True)
        fig.update_layout(
            title="USD Dominance vs Global Gold Share (2000–2025)",
            height=400, plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
            font=dict(color="white"),
            legend=dict(orientation="h", y=1.1)
        )
        fig.update_xaxes(title_text="Year")
        fig.update_yaxes(title_text="USD Share (%)", secondary_y=False)
        fig.update_yaxes(title_text="Gold Share (%)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        import matplotlib.pyplot as plt
        fig, ax1 = plt.subplots(figsize=(12, 5))
        ax2 = ax1.twinx()
        ax1.plot(world_trend["year"], world_trend["usd_share"], color="#4A90D9", linewidth=2, label="USD Share")
        ax2.plot(world_trend["year"], world_trend["world_gold_share"], color="#D4AF37", linewidth=2, label="Gold Share")
        ax1.set_xlabel("Year"); ax1.set_ylabel("USD Share (%)")
        ax2.set_ylabel("Gold Share (%)")
        ax1.legend(loc="upper left"); ax2.legend(loc="upper right")
        st.pyplot(fig)

    if (DOCS / "usd_vs_gold_thesis.png").exists():
        st.image(str(DOCS / "usd_vs_gold_thesis.png"), use_column_width=True)

    # Country-level gold trends
    st.markdown("---")
    st.subheader("Country Gold Share Trends")

    all_countries = sorted(df["country"].dropna().unique())
    default_countries = ["China", "India", "Poland", "Czechia", "Singapore", "Turkiye"]
    default_countries = [c for c in default_countries if c in all_countries]

    selected = st.multiselect(
        "Select countries to compare:",
        options=all_countries,
        default=default_countries
    )

    if selected:
        sub = df[df["country"].isin(selected)][["country", "year", "gold_share_pct"]].dropna()
        try:
            import plotly.express as px
            fig = px.line(sub, x="year", y="gold_share_pct", color="country",
                          title="Gold Share of Reserves Over Time (%)",
                          labels={"gold_share_pct": "Gold Share (%)", "year": "Year"})
            fig.update_layout(
                plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                font=dict(color="white"), height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(12, 5))
            for country in selected:
                d = sub[sub.country == country]
                ax.plot(d.year, d.gold_share_pct, label=country, linewidth=2)
            ax.set_xlabel("Year"); ax.set_ylabel("Gold Share (%)")
            ax.legend(); st.pyplot(fig)

    st.markdown("---")
    img_col1, img_col2 = st.columns(2)
    with img_col1:
        if (DOCS / "accumulation_vs_usd_decline.png").exists():
            st.image(str(DOCS / "accumulation_vs_usd_decline.png"),
                     caption="Accumulation During USD Decline", use_column_width=True)
    with img_col2:
        if (DOCS / "usd_drawdown_vs_gold_share.png").exists():
            st.image(str(DOCS / "usd_drawdown_vs_gold_share.png"),
                     caption="USD Drawdown vs Gold Share", use_column_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — GEOPOLITICS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🌐 Geopolitics":
    st.title("🌐 Geopolitical Risk & Gold Accumulation")
    st.markdown("""
    Countries with **high sanctions exposure**, **geopolitical risk**, or **divergence from US foreign policy**
    show systematically higher gold accumulation. This page quantifies those relationships.
    """)

    # Metrics
    latest23 = df[df.year == 2023].dropna(subset=["sanctions_score", "gold_share_pct"])

    col1, col2, col3 = st.columns(3)
    sanc2_avg = latest23[latest23.sanctions_score >= 2]["gold_share_pct"].mean()
    sanc0_avg = latest23[latest23.sanctions_score == 0]["gold_share_pct"].mean()
    divergent_streak = latest23[latest23.geo_bloc == "us_divergent"]["accumulation_streak"].mean()
    allied_streak = latest23[latest23.geo_bloc == "US_allied"]["accumulation_streak"].mean()

    col1.metric("Heavily Sanctioned Avg Gold Share", f"{sanc2_avg:.1f}%", f"+{sanc2_avg - sanc0_avg:.1f}pp vs non-sanctioned")
    col2.metric("US-Divergent Avg Streak", f"{divergent_streak:.1f} yrs", f"+{divergent_streak - allied_streak:.1f}yr vs allied")
    col3.metric("Countries w/ Sanctions Score ≥ 1", f"{int((latest23.sanctions_score >= 1).sum())}", "in panel")

    st.markdown("---")

    # Sanctions analysis
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Sanctions Exposure vs Gold Share (2023)")
        sanc_group = latest23.groupby("sanctions_score").agg(
            avg_gold_share=("gold_share_pct", "mean"),
            countries=("country", "count")
        ).reset_index()
        sanc_group["sanctions_label"] = sanc_group["sanctions_score"].map(
            {0: "None", 1: "Low", 2: "Medium", 3: "High"}
        )

        try:
            import plotly.graph_objects as go
            fig = go.Figure(go.Bar(
                x=sanc_group["sanctions_label"],
                y=sanc_group["avg_gold_share"],
                marker_color=["#2ECC71", "#F39C12", "#E74C3C", "#8E44AD"],
                text=sanc_group["avg_gold_share"].round(1).astype(str) + "%",
                textposition="outside"
            ))
            fig.update_layout(
                yaxis_title="Avg Gold Share (%)",
                xaxis_title="Sanctions Level",
                plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                font=dict(color="white"), height=350,
                yaxis=dict(range=[0, sanc_group["avg_gold_share"].max() * 1.3])
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.bar(sanc_group["sanctions_label"], sanc_group["avg_gold_share"],
                   color=["green", "orange", "red", "purple"])
            ax.set_ylabel("Avg Gold Share (%)"); st.pyplot(fig)

    with col_b:
        st.subheader("Geo Bloc vs Accumulation Streak (2023)")
        bloc_group = latest23.groupby("geo_bloc").agg(
            avg_streak=("accumulation_streak", "mean"),
            avg_gold=("gold_share_pct", "mean"),
            n=("country", "count")
        ).reset_index()

        try:
            import plotly.express as px
            fig = px.bar(bloc_group, x="geo_bloc", y="avg_streak",
                         color="avg_gold",
                         color_continuous_scale="YlOrRd",
                         labels={"avg_streak": "Avg Streak (yrs)", "geo_bloc": "Geopolitical Bloc"},
                         title="")
            fig.update_layout(
                plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                font=dict(color="white"), height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.bar(bloc_group["geo_bloc"], bloc_group["avg_streak"])
            ax.set_ylabel("Avg Streak (yrs)"); st.pyplot(fig)

    # Full country table
    st.markdown("---")
    st.subheader("Country Geopolitical Profile (2023)")
    geo_table = latest23[["country", "geo_bloc", "geo_risk_tier", "sanctions_score",
                           "un_alignment_score", "gold_share_pct", "accumulation_streak"]].copy()
    geo_table = geo_table.sort_values("gold_share_pct", ascending=False).reset_index(drop=True)
    geo_table.index += 1
    geo_table.columns = ["Country", "Geo Bloc", "Risk Tier", "Sanctions", "UN Alignment", "Gold Share %", "Streak"]
    geo_table["Gold Share %"] = geo_table["Gold Share %"].round(1)
    st.dataframe(geo_table, use_container_width=True, height=400)

    # Chart images
    st.markdown("---")
    img_col1, img_col2 = st.columns(2)
    with img_col1:
        if (DOCS / "geo_risk_vs_gold.png").exists():
            st.image(str(DOCS / "geo_risk_vs_gold.png"), use_column_width=True)
    with img_col2:
        if (DOCS / "sanctions_vs_gold_share.png").exists():
            st.image(str(DOCS / "sanctions_vs_gold_share.png"), use_column_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — NLP SENTIMENT
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📰 Sentiment":
    st.title("📰 NLP Narrative Analysis")
    st.markdown("""
    Financial news articles (sourced via GDELT) were processed to extract **USD sentiment**, **gold buying signals**,
    and **de-dollarization mentions** by country and year. This NLP layer captures the *narrative environment*
    driving central bank gold decisions.
    """)

    # Global USD sentiment trend
    nlp_global = df.groupby("year").agg(
        usd_neg=("global_usd_negative_pct", "first"),
        usd_pos=("global_usd_positive_pct", "first"),
        articles=("global_usd_article_count", "first"),
    ).reset_index().dropna()

    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=nlp_global["year"], y=nlp_global["usd_neg"],
            name="Negative USD Sentiment (%)",
            line=dict(color="#E74C3C", width=2.5),
            fill="tozeroy", fillcolor="rgba(231,76,60,0.15)"
        ))
        fig.add_trace(go.Scatter(
            x=nlp_global["year"], y=nlp_global["usd_pos"],
            name="Positive USD Sentiment (%)",
            line=dict(color="#2ECC71", width=2)
        ))
        fig.update_layout(
            title="Global USD Sentiment in Financial News (2000–2025)",
            xaxis_title="Year", yaxis_title="% of Articles",
            plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
            font=dict(color="white"), height=380,
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.fill_between(nlp_global["year"], nlp_global["usd_neg"], alpha=0.3, color="red")
        ax.plot(nlp_global["year"], nlp_global["usd_neg"], color="red", label="Negative USD %")
        ax.plot(nlp_global["year"], nlp_global["usd_pos"], color="green", label="Positive USD %")
        ax.set_xlabel("Year"); ax.set_ylabel("% Articles"); ax.legend(); st.pyplot(fig)

    st.markdown("---")

    # Country NLP signals
    st.subheader("Country-Level NLP Signals (2023)")
    nlp_2023 = df[df.year == 2023][
        ["country", "nlp_gold_positive", "nlp_gold_negative", "nlp_usd_negative",
         "nlp_dedollar_mentions", "nlp_composite_signal", "nlp_article_count"]
    ].dropna(subset=["nlp_composite_signal"]).sort_values("nlp_composite_signal", ascending=False)

    nlp_2023 = nlp_2023[nlp_2023["nlp_article_count"] > 0]

    if len(nlp_2023) > 0:
        try:
            import plotly.express as px
            fig = px.bar(
                nlp_2023.head(20),
                x="nlp_composite_signal", y="country",
                orientation="h",
                color="nlp_composite_signal",
                color_continuous_scale="RdYlGn",
                labels={"nlp_composite_signal": "NLP Composite Signal", "country": "Country"},
                title="Top Countries by NLP Gold/De-dollarization Signal (2023)"
            )
            fig.update_layout(
                plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                font=dict(color="white"), height=450,
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            import matplotlib.pyplot as plt
            top_nlp = nlp_2023.head(15)
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(top_nlp["country"], top_nlp["nlp_composite_signal"])
            ax.set_xlabel("NLP Composite Signal"); ax.invert_yaxis(); st.pyplot(fig)

        st.markdown("**Full NLP table:**")
        display_nlp = nlp_2023.copy()
        display_nlp.columns = ["Country", "Gold Positive", "Gold Negative", "USD Negative",
                                "De-Dollar Mentions", "Composite Signal", "Articles"]
        display_nlp.index = range(1, len(display_nlp) + 1)
        st.dataframe(display_nlp.head(30), use_container_width=True)
    else:
        st.info("NLP article data is based on seeded articles (GDELT was unavailable in training environment). "
                "Connect a NewsAPI or GDELT key to enrich this layer.")

    # NLP methodology
    st.markdown("---")
    with st.expander("📖 NLP Methodology"):
        st.markdown("""
        **Data Source:** GDELT Document API (fallback: 135 seeded financial news articles)

        **Sentiment Model:** FinBERT (HuggingFace) → fallback: FinancialKeywordSentiment (custom keyword scorer)

        **Features Extracted per Country-Year:**
        - `nlp_gold_positive` — % articles mentioning gold positively
        - `nlp_gold_negative` — % articles mentioning gold negatively
        - `nlp_usd_positive / negative` — USD sentiment signals
        - `nlp_dedollar_mentions` — explicit de-dollarization language count
        - `nlp_composite_signal` — weighted aggregate signal (0–100)
        - `nlp_avg_sentiment_score` — mean FinBERT score per country

        **Global signals** (aggregated from all countries per year):
        - `global_usd_negative_pct` — % of USD-related articles with negative tone
        - `global_usd_positive_pct` — % positive
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — ML PREDICTIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 ML Predictions":
    max_data_year = int(df["year"].max())
    predict_year = max_data_year + 1
    st.title(f"🤖 ML Predictions: Top Gold Accumulators {predict_year}")
    st.markdown(f"""
    An **interpretable scoring model** combining gradient boosting feature importance weights
    ranks countries by their likelihood of increasing gold reserves in {predict_year}.

    **Feature weights (from GB importance):**
    - Gold YoY momentum: **40%**
    - USD decline signal: **27%**
    - USD drawdown from peak: **18%**
    - Global gold trend: **10%**
    - Geopolitical risk: **5%**
    - Sanctions bonus: +5 to +18 points
    """)

    # Top 10 chart
    top10 = scores.head(10).copy()

    try:
        import plotly.graph_objects as go

        colors = []
        for _, row in top10.iterrows():
            if row["sanctions_score"] >= 2:
                colors.append("#C0392B")
            elif str(row.get("geo_risk_tier", "")).lower() == "high":
                colors.append("#E67E22")
            else:
                colors.append("#1F3A6E")

        fig = go.Figure(go.Bar(
            x=top10["gold_accumulation_score"],
            y=top10["country"],
            orientation="h",
            marker_color=colors,
            text=top10["gold_accumulation_score"].round(1).astype(str),
            textposition="outside"
        ))
        fig.update_layout(
            title=f"Top 10 Countries Predicted to Increase Gold Reserves in {predict_year}",
            xaxis_title="Gold Accumulation Score (0–100)",
            xaxis=dict(range=[0, 115]),
            plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
            font=dict(color="white"), height=450,
            yaxis=dict(autorange="reversed")
        )

        # Legend annotation
        fig.add_annotation(x=100, y=9, text="🔴 Heavily Sanctioned   🟠 High Geo Risk   🔵 Strong Accumulator",
                           showarrow=False, font=dict(size=10, color="white"))

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        if (DOCS / "ml_top10_predictions.png").exists():
            st.image(str(DOCS / "ml_top10_predictions.png"), use_column_width=True)

    # Full ranking table
    st.markdown("---")
    st.subheader("Full Country Ranking (68 Countries, Gold Holdings > $500M)")

    display_scores = scores.copy()
    display_scores["gold_value_est"] = scores.get("gold_value_usd", pd.Series(dtype=float))

    show_cols = ["country", "gold_accumulation_score", "gold_share_pct", "gold_yoy_change_pct",
                 "accumulation_streak", "sanctions_score", "geo_risk_tier", "usd_share_drawdown_pct"]
    show_cols = [c for c in show_cols if c in display_scores.columns]
    display_scores = display_scores[show_cols].copy()
    display_scores.columns = [c.replace("_", " ").title() for c in show_cols]
    display_scores.index = range(1, len(display_scores) + 1)

    # Color filter
    filter_tier = st.selectbox("Filter by Geo Risk Tier:", ["All", "high", "medium", "low"])
    if filter_tier != "All" and "Geo Risk Tier" in display_scores.columns:
        display_scores = display_scores[display_scores["Geo Risk Tier"] == filter_tier]

    st.dataframe(display_scores, use_container_width=True, height=450)

    # Model diagnostics
    st.markdown("---")
    st.subheader("📊 Model Diagnostics")

    img_col1, img_col2, img_col3 = st.columns(3)
    with img_col1:
        if (DOCS / "ml_feature_importance.png").exists():
            st.image(str(DOCS / "ml_feature_importance.png"), caption="Feature Importance", use_column_width=True)
    with img_col2:
        if (DOCS / "ml_roc_curves.png").exists():
            st.image(str(DOCS / "ml_roc_curves.png"), caption="ROC Curves", use_column_width=True)
    with img_col3:
        if (DOCS / "ml_confusion_matrix.png").exists():
            st.image(str(DOCS / "ml_confusion_matrix.png"), caption="Confusion Matrix", use_column_width=True)

    with st.expander("📖 Methodology Notes"):
        st.markdown("""
        **Training Data:** 2001–2019 (time-based split)
        **Test Data:** 2020–2024 (post-COVID, sanctions acceleration era)
        **Target:** Will this country's gold share increase next year?
        **Models:** Logistic Regression + Gradient Boosting (both implemented from scratch in NumPy)

        **Scoring Model Design:**
        1. Each feature is percentile-ranked across all countries in 2023
        2. Features combined using weights from GB feature importance
        3. Sanctions bonus (+5 to +18 pts) for structural motivation
        4. Final scores normalized to 0–100

        **Limitation:** Binary classification AUC is modest (0.34–0.59) due to noisy target
        (gold value rises with gold price, not just active buying). The interpretable scoring model
        is preferred as the primary output.
        """)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#888; font-size:12px'>"
    "Gold Reserve Intelligence Platform · Built with Python, World Bank API, IMF COFER, OFAC, UN Voting, GDELT · "
    "Models: LR + GB from scratch · Sathwik Arroju</div>",
    unsafe_allow_html=True
)

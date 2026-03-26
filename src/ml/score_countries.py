"""
Country Scoring Model — V5
Builds an interpretable scoring model with four domain-driven pillars.

Problem with V4:
  - 40% weight on USD-based gold_yoy_change_pct: in 2025, gold price rose ~20%
    ($2,386→$2,869/oz), inflating every country's USD value even with no buying.
    Small countries with volatile % swings (Ghana, Guinea) dominated unfairly.
  - 27% on USD drawdown / world_gold_share = global constants, same for every
    country → useless for ranking individual countries.

V5 Methodology — Four pillars, all country-specific:

  Pillar 1 — Physical Buying Momentum (30%)
    gold_tonnes_yoy: actual tonnage change from WGC data (price-neutral)
    Falls back to gold_share_yoy_change (share, not USD) where tonnes unavailable

  Pillar 2 — Buying Consistency (25%)
    accumulation_streak: consecutive years of buying
    buy_frequency_5yr: how many of last 5 years they bought gold

  Pillar 3 — Geopolitical Motivation (25%)
    un_divergence_score: how far from US alignment (higher = more motivated)
    sanctions_score: structural incentive to hold non-USD reserves

  Pillar 4 — Strategic Allocation Gap (20%)
    gold_share_vs_peers: below-average allocation = room to grow
    gold_share_trend: acceleration in gold share over last 3 years

Input:  data/curated/master_panel_nlp.csv
        data/raw/wgc_gold_timeseries.csv  (for price-neutral tonnage data)
Output: data/curated/ml_country_scores.csv
        data/curated/ml_top10_predictions.csv
        docs/ml_top10_predictions.png
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import logging
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parents[2]
CURATED_DIR = BASE_DIR / "data" / "curated"
RAW_DIR     = BASE_DIR / "data" / "raw"
DOCS_DIR    = BASE_DIR / "docs"

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ── Pillar weights ─────────────────────────────────────────────────────────────
PILLAR_WEIGHTS = {
    "physical_momentum": 0.30,   # actual buying (tonnes, price-neutral)
    "consistency":       0.25,   # streak + frequency
    "geo_motivation":    0.25,   # UN divergence + sanctions
    "alloc_gap":         0.20,   # room to grow allocation
}

SANCTIONS_BONUS = {0: 0, 1: 5, 2: 12, 3: 18}


def percentile_rank(series: pd.Series) -> pd.Series:
    """Rank each value as a percentile (0–100) within the series."""
    return series.rank(pct=True, na_option="bottom") * 100


def run():
    log.info("=" * 60)
    log.info("Country Scoring Model — V5")
    log.info("=" * 60)

    df = pd.read_csv(CURATED_DIR / "master_panel_nlp.csv")

    max_year  = int(df["year"].max())
    prev_year = max_year - 1
    predict_year = max_year + 1
    log.info(f"Scoring year: {max_year} → predicting: {predict_year}")

    # ── Load WGC tonnage data (price-neutral physical buying) ──────────────────
    wgc_path = RAW_DIR / "wgc_gold_timeseries.csv"
    if wgc_path.exists():
        wgc = pd.read_csv(wgc_path)
        wgc_cur  = wgc[wgc["year"] == max_year][["country", "gold_tonnes"]].rename(
            columns={"gold_tonnes": "tonnes_cur"})
        wgc_prev = wgc[wgc["year"] == prev_year][["country", "gold_tonnes"]].rename(
            columns={"gold_tonnes": "tonnes_prev"})
        wgc_delta = wgc_cur.merge(wgc_prev, on="country", how="left")
        wgc_delta["gold_tonnes_yoy"] = wgc_delta["tonnes_cur"] - wgc_delta["tonnes_prev"]
        log.info(f"WGC tonnage data loaded: {len(wgc_delta)} countries")
    else:
        wgc_delta = pd.DataFrame(columns=["country", "gold_tonnes_yoy"])
        log.warning("WGC data not found — falling back to gold_share_yoy_change")

    # ── Buying frequency over last 5 years ────────────────────────────────────
    recent = df[df["year"].between(max_year - 4, max_year)].copy()
    freq5 = (
        recent.groupby("country")["is_accumulating"]
        .sum()
        .reset_index()
        .rename(columns={"is_accumulating": "buy_frequency_5yr"})
    )

    # ── Trend in gold share: avg of last 3 years minus avg of 3 years before ──
    last3  = df[df["year"].between(max_year - 2, max_year)].groupby("country")["gold_share_pct"].mean()
    prev3  = df[df["year"].between(max_year - 5, max_year - 3)].groupby("country")["gold_share_pct"].mean()
    trend  = (last3 - prev3).reset_index().rename(columns={"gold_share_pct": "gold_share_3yr_trend"})

    # ── Latest year slice ──────────────────────────────────────────────────────
    latest = df[df["year"] == max_year].copy()
    log.info(f"Countries in latest year: {len(latest)}")

    # Merge in tonnage and frequency features
    latest = latest.merge(wgc_delta[["country", "gold_tonnes_yoy"]], on="country", how="left")
    latest = latest.merge(freq5, on="country", how="left")
    latest = latest.merge(trend,  on="country", how="left")

    # Drop countries with missing core features
    required = ["gold_share_pct", "accumulation_streak", "un_divergence_score",
                "sanctions_score", "country", "country_code"]
    latest = latest.dropna(subset=[c for c in required if c in latest.columns])

    # Filter to meaningful gold markets (> $500M prevents micro-states dominating)
    latest = latest[latest["gold_value_usd"] >= 500_000_000]
    log.info(f"After minimum holdings filter: {len(latest)} countries")

    # Fill missing optional features with neutral values
    latest["gold_tonnes_yoy"]     = latest["gold_tonnes_yoy"].fillna(0)
    latest["buy_frequency_5yr"]   = latest["buy_frequency_5yr"].fillna(0)
    latest["gold_share_3yr_trend"]= latest["gold_share_3yr_trend"].fillna(0)
    latest["accumulation_streak"] = latest["accumulation_streak"].fillna(0)

    # ── PILLAR 1: Physical Buying Momentum ────────────────────────────────────
    # Use tonnage YoY (price-neutral) as primary; supplement with share change
    # Combine: 70% from tonnes, 30% from share trend
    p1_tonnes = percentile_rank(latest["gold_tonnes_yoy"])
    p1_share  = percentile_rank(latest["gold_share_yoy_change"].fillna(0))
    has_tonnes = latest["gold_tonnes_yoy"] != 0
    latest["pillar_momentum"] = np.where(
        has_tonnes,
        0.70 * p1_tonnes + 0.30 * p1_share,
        p1_share,  # fallback when no WGC data
    )
    log.info(f"  P1 top 5 (momentum): {latest.nlargest(5,'pillar_momentum')['country'].tolist()}")

    # ── PILLAR 2: Buying Consistency ──────────────────────────────────────────
    p2_streak = percentile_rank(latest["accumulation_streak"])
    p2_freq   = percentile_rank(latest["buy_frequency_5yr"])
    latest["pillar_consistency"] = 0.60 * p2_streak + 0.40 * p2_freq
    log.info(f"  P2 top 5 (consistency): {latest.nlargest(5,'pillar_consistency')['country'].tolist()}")

    # ── PILLAR 3: Geopolitical Motivation ─────────────────────────────────────
    p3_div      = percentile_rank(latest["un_divergence_score"])
    p3_sanction = percentile_rank(latest["sanctions_score"])
    latest["pillar_geo"] = 0.60 * p3_div + 0.40 * p3_sanction
    log.info(f"  P3 top 5 (geo): {latest.nlargest(5,'pillar_geo')['country'].tolist()}")

    # ── PILLAR 4: Strategic Allocation Gap ────────────────────────────────────
    # Countries with LOWER current gold share have more room to grow
    # But also reward those with positive 3-year trend (they're on the way up)
    p4_low_share = percentile_rank(-latest["gold_share_pct"])   # lower share = higher rank
    p4_trend     = percentile_rank(latest["gold_share_3yr_trend"])
    latest["pillar_alloc"] = 0.40 * p4_low_share + 0.60 * p4_trend
    log.info(f"  P4 top 5 (alloc gap): {latest.nlargest(5,'pillar_alloc')['country'].tolist()}")

    # ── Weighted composite score ───────────────────────────────────────────────
    latest["base_score"] = (
        PILLAR_WEIGHTS["physical_momentum"] * latest["pillar_momentum"]   +
        PILLAR_WEIGHTS["consistency"]       * latest["pillar_consistency"] +
        PILLAR_WEIGHTS["geo_motivation"]    * latest["pillar_geo"]         +
        PILLAR_WEIGHTS["alloc_gap"]         * latest["pillar_alloc"]
    )

    # Sanctions structural bonus (non-linear)
    latest["sanctions_bonus"] = latest["sanctions_score"].map(SANCTIONS_BONUS).fillna(0)

    # ── Final score (normalize to 0–100) ─────────────────────────────────────
    raw_final = latest["base_score"] + latest["sanctions_bonus"]
    latest["gold_accumulation_score"] = (
        (raw_final - raw_final.min()) / (raw_final.max() - raw_final.min()) * 100
    ).round(1)

    ranked = latest.sort_values("gold_accumulation_score", ascending=False).reset_index(drop=True)
    ranked.index += 1

    out_cols = [
        "country", "country_code", "gold_accumulation_score",
        "gold_share_pct", "gold_tonnes_yoy", "buy_frequency_5yr",
        "accumulation_streak", "gold_share_3yr_trend",
        "un_divergence_score", "sanctions_score", "geo_risk_tier", "geo_bloc",
        "pillar_momentum", "pillar_consistency", "pillar_geo", "pillar_alloc",
        "sanctions_bonus",
    ]
    out_cols = [c for c in out_cols if c in ranked.columns]

    score_path = CURATED_DIR / "ml_country_scores.csv"
    ranked[out_cols].to_csv(score_path, index=False)
    log.info(f"Full ranking saved → {score_path}")

    # ── Top 10 ────────────────────────────────────────────────────────────────
    top10 = ranked.head(10)

    log.info("\n" + "=" * 60)
    log.info(f"TOP 10 PREDICTED GOLD ACCUMULATORS — {predict_year}")
    log.info("=" * 60)
    for rank, row in top10.iterrows():
        log.info(
            f"  #{rank:2d}  {row['country']:<35}  "
            f"score={row['gold_accumulation_score']:.1f}  "
            f"streak={int(row.get('accumulation_streak',0))}yr  "
            f"freq={row.get('buy_frequency_5yr',0):.0f}/5  "
            f"sanctions={int(row['sanctions_score'])}  "
            f"geo={row.get('geo_risk_tier','?')}"
        )

    top10_path = CURATED_DIR / "ml_top10_predictions.csv"
    top10[out_cols].to_csv(top10_path, index=False)
    log.info(f"\nTop 10 saved → {top10_path}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#0D1117")

    colors = []
    for _, row in top10.iterrows():
        tier = str(row.get("geo_risk_tier", "")).lower()
        if row["sanctions_score"] >= 2:
            colors.append("#C0392B")
        elif tier == "high":
            colors.append("#E67E22")
        else:
            colors.append("#D4AF37")

    bars = ax.barh(
        top10["country"][::-1],
        top10["gold_accumulation_score"][::-1],
        color=colors[::-1],
        edgecolor="none",
        height=0.65,
    )
    for bar, score in zip(bars, top10["gold_accumulation_score"][::-1]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{score:.0f}", va="center", ha="left", color="white", fontsize=10)

    ax.set_xlabel("Gold Accumulation Score (0–100)", color="#8899AA", fontsize=11)
    ax.set_title(f"Top 10 Countries Predicted to Increase Gold Reserves in {predict_year}\n"
                 f"Scored on: Physical Buying · Consistency · Geo Motivation · Allocation Gap",
                 color="white", fontsize=12, pad=14)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlim(0, 115)
    ax.grid(axis="x", color="#2A3548", linewidth=0.6)

    from matplotlib.patches import Patch
    legend = [
        Patch(color="#D4AF37", label="Low geo risk"),
        Patch(color="#E67E22", label="High geo risk"),
        Patch(color="#C0392B", label="Sanctioned"),
    ]
    ax.legend(handles=legend, loc="lower right", facecolor="#1A2332", edgecolor="none",
              labelcolor="white", fontsize=9)

    plt.tight_layout()
    plot_path = DOCS_DIR / "ml_top10_predictions.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor="#0D1117")
    plt.close()
    log.info(f"Plot saved → {plot_path}")

    # ── Validation: check known buyers are ranked well ─────────────────────────
    log.info("\n  Known WGC 2025 buyers — rank check:")
    known = ["Poland", "India", "China", "Czechia", "Turkiye", "Brazil", "Kazakhstan", "Russian Federation"]
    for c in known:
        row_idx = ranked.index[ranked["country"] == c].tolist()
        if row_idx:
            r = ranked.loc[row_idx[0]]
            log.info(f"    {c:<25} rank=#{row_idx[0]}  score={r['gold_accumulation_score']:.1f}  "
                     f"streak={r.get('accumulation_streak',0):.0f}  tonnes_yoy={r.get('gold_tonnes_yoy',0):.1f}")
        else:
            log.info(f"    {c:<25} NOT IN RANKING")


if __name__ == "__main__":
    run()

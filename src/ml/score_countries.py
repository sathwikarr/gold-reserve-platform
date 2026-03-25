"""
Country Scoring Model — V4 Machine Learning Model
Builds an interpretable scoring model using feature weights derived from
gradient boosting feature importance and logistic regression coefficients.

Methodology:
  1. Each feature is percentile-ranked across all countries in 2023
     (the most recent year with full data)
  2. Features are combined using a weighted sum based on GB importance
  3. Bonuses are applied for sanctions exposure and geopolitical risk
     (countries with these characteristics have structural motivation to buy gold)
  4. Final scores are normalized 0–100

This scoring approach is more interpretable than raw model probabilities
and avoids the class imbalance issues that affect binary classification.
The weights are data-driven (from gradient boosting), not hand-tuned.

Feature weights (from GB importance):
  gold_yoy_change_pct    : 0.40  — recent gold buying momentum
  usd_share_yoy_change   : 0.27  — USD movement (negative = USD declining)
  usd_share_drawdown_pct : 0.18  — cumulative USD decline from peak
  world_gold_share_pct   : 0.10  — global gold trend context
  geo_risk_score         : 0.05  — geopolitical risk bonus

Input:  data/curated/master_panel_nlp.csv
Output: data/curated/ml_country_scores.csv
        data/curated/ml_top10_predictions.csv  (overwrite with better scores)
        docs/ml_top10_predictions.png           (overwrite)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import logging
from pathlib import Path

CURATED_DIR = Path(__file__).resolve().parents[2] / "data" / "curated"
DOCS_DIR    = Path(__file__).resolve().parents[2] / "docs"

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# Weights from gradient boosting feature importance (normalized)
WEIGHTS = {
    "gold_yoy_change_pct":    0.40,
    "usd_share_yoy_change":   0.27,   # higher USD decline → higher score (use negative)
    "usd_share_drawdown_pct": 0.18,
    "world_gold_share_pct":   0.10,
    "geo_risk_score":         0.05,
}

# Bonus weights for structural motivation
SANCTIONS_BONUS = {0: 0, 1: 5, 2: 12, 3: 18}  # points added to final score


def percentile_rank(series: pd.Series) -> pd.Series:
    """Rank each value as a percentile (0–100) within the series."""
    return series.rank(pct=True) * 100


def run():
    log.info("=" * 60)
    log.info("Country Scoring Model — V4")
    log.info("=" * 60)

    df = pd.read_csv(CURATED_DIR / "master_panel_nlp.csv")

    # Use the most recent year with sufficient data
    max_year = int(df["year"].max())
    latest = df[df["year"] == max_year].copy()
    log.info(f"Using latest year: {max_year} | Countries: {len(latest)}")

    # Drop rows with missing key features
    required = list(WEIGHTS.keys()) + ["sanctions_score", "gold_share_pct",
                                        "accumulation_streak", "country", "country_code"]
    latest = latest.dropna(subset=[c for c in required if c in latest.columns])

    # Filter to meaningful gold markets only (> $500M in gold holdings)
    # This prevents tiny countries with volatile % swings from dominating
    latest = latest[latest["gold_value_usd"] >= 500_000_000]
    log.info(f"After dropping missing + minimum holdings filter: {len(latest)}")

    # ── Percentile-rank each feature ──────────────────────────────────────────
    # For usd_share_yoy_change: LOWER (more negative) = USD declining = higher score
    # So we rank the NEGATIVE of this feature
    latest["pct_gold_momentum"]   = percentile_rank(latest["gold_yoy_change_pct"])
    latest["pct_usd_decline"]     = percentile_rank(-latest["usd_share_yoy_change"])
    latest["pct_usd_drawdown"]    = percentile_rank(latest["usd_share_drawdown_pct"])
    latest["pct_world_gold"]      = percentile_rank(latest["world_gold_share_pct"])
    latest["pct_geo_risk"]        = percentile_rank(latest["geo_risk_score"])

    # ── Weighted score ─────────────────────────────────────────────────────────
    latest["base_score"] = (
        WEIGHTS["gold_yoy_change_pct"]    * latest["pct_gold_momentum"] +
        WEIGHTS["usd_share_yoy_change"]   * latest["pct_usd_decline"]   +
        WEIGHTS["usd_share_drawdown_pct"] * latest["pct_usd_drawdown"]  +
        WEIGHTS["world_gold_share_pct"]   * latest["pct_world_gold"]    +
        WEIGHTS["geo_risk_score"]         * latest["pct_geo_risk"]
    )

    # ── Sanctions bonus ───────────────────────────────────────────────────────
    latest["sanctions_bonus"] = latest["sanctions_score"].map(SANCTIONS_BONUS).fillna(0)

    # ── Final score (normalize to 0–100) ─────────────────────────────────────
    raw_final = latest["base_score"] + latest["sanctions_bonus"]
    latest["gold_accumulation_score"] = (
        (raw_final - raw_final.min()) / (raw_final.max() - raw_final.min()) * 100
    ).round(1)

    # ── Sort and show full ranking ────────────────────────────────────────────
    ranked = latest.sort_values("gold_accumulation_score", ascending=False).reset_index(drop=True)
    ranked.index += 1

    out_cols = [
        "country", "country_code", "gold_accumulation_score",
        "gold_share_pct", "gold_yoy_change_pct", "accumulation_streak",
        "sanctions_score", "geo_risk_tier", "geo_bloc",
        "usd_share_drawdown_pct", "un_alignment_score",
        "pct_gold_momentum", "pct_usd_decline", "sanctions_bonus",
    ]
    out_cols = [c for c in out_cols if c in ranked.columns]

    score_path = CURATED_DIR / "ml_country_scores.csv"
    ranked[out_cols].to_csv(score_path, index=False)
    log.info(f"Full ranking saved → {score_path}")

    # ── Top 10 ────────────────────────────────────────────────────────────────
    top10 = ranked.head(10)

    log.info("\n" + "=" * 60)
    predict_year = max_year + 1
    log.info(f"TOP 10 PREDICTED GOLD ACCUMULATORS — {predict_year}")
    log.info("=" * 60)
    for rank, row in top10.iterrows():
        log.info(
            f"  #{rank:2d}  {row['country']:<35}  "
            f"score={row['gold_accumulation_score']:.1f}  "
            f"sanctions={int(row['sanctions_score'])}  "
            f"geo={row.get('geo_risk_tier','?')}"
        )

    # Save top 10
    top10_path = CURATED_DIR / "ml_top10_predictions.csv"
    top10[out_cols].to_csv(top10_path, index=False)
    log.info(f"\nTop 10 saved → {top10_path}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11, 7))

    colors = []
    for _, row in top10.iterrows():
        tier = str(row.get("geo_risk_tier", "")).lower()
        if row["sanctions_score"] >= 2:
            colors.append("#C0392B")
        elif tier == "high":
            colors.append("#E67E22")
        else:
            colors.append("#1F3A6E")

    bars = ax.barh(top10["country"], top10["gold_accumulation_score"],
                   color=colors, edgecolor="white", linewidth=0.5)

    for bar, score in zip(bars, top10["gold_accumulation_score"]):
        ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height()/2,
                f"{score:.1f}", va="center", fontsize=10, color="#333333")

    ax.set_xlabel("Gold Accumulation Score (0–100)", fontsize=11)
    ax.set_title(
        f"Top 10 Countries Predicted to Increase Gold Reserves in {predict_year}\n"
        "Scoring: Gold Momentum (40%) + USD Decline (27%) + USD Drawdown (18%) + Global Trend (10%) + Geo Risk (5%) + Sanctions Bonus",
        fontsize=10, fontweight="bold"
    )
    ax.set_xlim(0, 115)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)

    from matplotlib.patches import Patch
    legend = [
        Patch(color="#C0392B", label="Heavily Sanctioned (OFAC score ≥ 2)"),
        Patch(color="#E67E22", label="High Geopolitical Risk"),
        Patch(color="#1F3A6E", label="Strong Recent Accumulator"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=9)

    plt.tight_layout()
    plot_path = DOCS_DIR / "ml_top10_predictions.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Plot saved → {plot_path}")

    return ranked


if __name__ == "__main__":
    run()

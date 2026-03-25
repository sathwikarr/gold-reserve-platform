"""
Gold Accumulation Predictions — V4 Machine Learning Model
Uses trained model scores to identify the top 10 countries most likely
to increase their gold reserves in 2025.

Prediction methodology:
  The most recent year available per country is 2024. The ensemble
  probability score from that year represents the model's estimate of
  whether that country will accumulate gold in 2025.

  Countries are ranked by ensemble_prob (average of logistic regression
  and gradient boosting probabilities).

Output: data/curated/ml_top10_predictions.csv
        docs/ml_top10_predictions.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import logging
from pathlib import Path

CURATED_DIR = Path(__file__).resolve().parents[2] / "data" / "curated"
DOCS_DIR    = Path(__file__).resolve().parents[2] / "docs"

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# Key context columns to include in prediction output
CONTEXT_COLS = [
    "country", "country_code",
    "gold_share_pct", "sanctions_score", "geo_risk_tier", "geo_bloc",
    "usd_share_drawdown_pct", "un_alignment_score",
    "lr_prob", "gb_prob", "ensemble_prob",
]


def plot_top10(top10: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 7))

    colors = []
    for _, row in top10.iterrows():
        tier = str(row.get("geo_risk_tier", "")).lower()
        if row["sanctions_score"] >= 2:
            colors.append("#C0392B")
        elif tier == "high":
            colors.append("#E67E22")
        else:
            colors.append("#1F3A6E")

    bars = ax.barh(top10["country"], top10["ensemble_prob"] * 100,
                   color=colors, edgecolor="white", linewidth=0.5)

    # Add probability labels
    for bar, prob in zip(bars, top10["ensemble_prob"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{prob*100:.1f}%", va="center", fontsize=10, color="#333333")

    ax.set_xlabel("Probability of Gold Accumulation in 2025 (%)", fontsize=11)
    ax.set_title("Top 10 Countries Predicted to Increase Gold Reserves in 2025\n"
                 "(Ensemble Model: Logistic Regression + Gradient Boosting)",
                 fontsize=12, fontweight="bold")
    ax.set_xlim(0, 105)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)

    # Legend
    from matplotlib.patches import Patch
    legend = [
        Patch(color="#C0392B", label="Heavily Sanctioned (score ≥ 2)"),
        Patch(color="#E67E22", label="High Geopolitical Risk"),
        Patch(color="#1F3A6E", label="Standard Accumulator"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=9)

    plt.tight_layout()
    path = DOCS_DIR / "ml_top10_predictions.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Saved → {path}")


def run():
    log.info("=" * 60)
    log.info("Gold Accumulation Predictions — V4")
    log.info("=" * 60)

    pred_path = CURATED_DIR / "ml_predictions.csv"
    if not pred_path.exists():
        raise FileNotFoundError(f"Run train_model.py first: {pred_path}")

    df = pd.read_csv(pred_path)

    # Merge back context columns from full panel
    full_panel = pd.read_csv(CURATED_DIR / "master_panel_nlp.csv")
    context_cols = ["country_code", "year", "geo_risk_tier", "geo_bloc", "sanctions_active"]
    df = df.merge(full_panel[context_cols], on=["country_code", "year"], how="left")

    # Get most recent year per country (2023 is latest since target = next year)
    latest = (
        df.sort_values("year")
        .groupby("country_code")
        .last()
        .reset_index()
    )

    log.info(f"Latest year in predictions: {latest['year'].max()}")
    log.info(f"Countries covered: {len(latest)}")

    # Rank by ensemble probability
    top10 = (
        latest[CONTEXT_COLS + ["year"]]
        .sort_values("ensemble_prob", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    top10.index += 1  # rank 1–10

    log.info("\n" + "=" * 60)
    log.info("TOP 10 PREDICTED GOLD ACCUMULATORS — 2025")
    log.info("=" * 60)

    for rank, row in top10.iterrows():
        log.info(
            f"  #{rank:2d}  {row['country']:<30}  "
            f"prob={row['ensemble_prob']*100:.1f}%  "
            f"sanctions={int(row['sanctions_score'])}  "
            f"geo={row['geo_risk_tier']}"
        )

    # Save
    out_path = CURATED_DIR / "ml_top10_predictions.csv"
    top10.to_csv(out_path, index=False)
    log.info(f"\nSaved → {out_path}")

    plot_top10(top10)

    # ── Also save full country ranking ────────────────────────────────────────
    full_ranking = (
        latest[CONTEXT_COLS + ["year"]]
        .sort_values("ensemble_prob", ascending=False)
        .reset_index(drop=True)
    )
    full_ranking.index += 1
    full_path = CURATED_DIR / "ml_full_ranking.csv"
    full_ranking.to_csv(full_path, index=False)
    log.info(f"Full country ranking saved → {full_path}")

    return top10


if __name__ == "__main__":
    run()

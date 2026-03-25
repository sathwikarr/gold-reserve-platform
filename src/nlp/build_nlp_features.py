"""
NLP Feature Aggregation — V3 NLP Pipeline
Aggregates article-level sentiment into a country × year feature panel
that can be merged into the master_panel.

Features produced per country-year:
  nlp_article_count        — total articles mentioning this country
  nlp_gold_positive        — % of gold-related articles with positive sentiment
  nlp_gold_negative        — % of gold-related articles with negative sentiment
  nlp_usd_negative         — % of USD/dollar articles with negative sentiment
  nlp_usd_positive         — % of USD/dollar articles with positive sentiment
  nlp_dedollar_mentions    — count of de-dollarization articles mentioning country
  nlp_sanctions_mentions   — count of sanctions-related articles mentioning country
  nlp_composite_signal     — composite score: gold_pos - usd_pos (higher = more bullish on gold, bearish on USD)
  nlp_avg_sentiment_score  — mean raw sentiment score across all articles

GLOBAL rows (no specific country tagged) are kept separately for world-level
USD sentiment trends.

Input:  data/staging/articles_sentiment.csv
Output: data/curated/nlp_features.csv
        data/curated/nlp_global_usd_sentiment.csv  (world-level USD sentiment by year)
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
STAGING_DIR = Path(__file__).resolve().parents[2] / "data" / "staging"
CURATED_DIR = Path(__file__).resolve().parents[2] / "data" / "curated"
CURATED_DIR.mkdir(parents=True, exist_ok=True)

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ── Query label → theme mapping ───────────────────────────────────────────────
GOLD_QUERIES   = {"gold_reserves", "gold_buying"}
USD_QUERIES    = {"usd_dominance", "dedollarization"}
SANCTION_QUERIES = {"sanctions_gold"}


def safe_pct(df_sub: pd.DataFrame, label: str) -> float:
    """Percentage of rows where sentiment_label == label."""
    if len(df_sub) == 0:
        return np.nan
    return round((df_sub["sentiment_label"] == label).sum() / len(df_sub) * 100, 2)


def build_country_year_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate sentiment data to country × year panel.
    Excludes GLOBAL rows (handled separately).
    """
    df_country = df[df["country_code"] != "GLOBAL"].copy()

    records = []
    for (iso3, year), grp in df_country.groupby(["country_code", "year"]):
        gold_grp     = grp[grp["query_label"].isin(GOLD_QUERIES)]
        usd_grp      = grp[grp["query_label"].isin(USD_QUERIES)]
        sanc_grp     = grp[grp["query_label"].isin(SANCTION_QUERIES)]
        dedollar_grp = grp[grp["query_label"] == "dedollarization"]

        gold_pos = safe_pct(gold_grp, "positive")
        gold_neg = safe_pct(gold_grp, "negative")
        usd_pos  = safe_pct(usd_grp, "positive")
        usd_neg  = safe_pct(usd_grp, "negative")

        # Composite signal: positive gold sentiment - positive USD sentiment
        # High value = narrative is bullish on gold, bearish on USD for this country
        if not np.isnan(gold_pos) and not np.isnan(usd_pos):
            composite = round(gold_pos - usd_pos, 2)
        else:
            composite = np.nan

        records.append({
            "country_code":           iso3,
            "year":                   year,
            "nlp_article_count":      len(grp),
            "nlp_gold_positive":      gold_pos,
            "nlp_gold_negative":      gold_neg,
            "nlp_usd_positive":       usd_pos,
            "nlp_usd_negative":       usd_neg,
            "nlp_dedollar_mentions":  len(dedollar_grp),
            "nlp_sanctions_mentions": len(sanc_grp),
            "nlp_composite_signal":   composite,
            "nlp_avg_sentiment_score": round(grp["sentiment_score"].mean(), 4),
        })

    return pd.DataFrame(records)


def build_global_usd_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a world-level USD sentiment trend from GLOBAL-tagged articles.
    This captures macro narrative shifts that affect all countries.
    """
    df_global = df[df["country_code"] == "GLOBAL"].copy()
    df_usd    = df_global[df_global["query_label"].isin(USD_QUERIES)]

    records = []
    for year, grp in df_usd.groupby("year"):
        records.append({
            "year":                        year,
            "global_usd_article_count":    len(grp),
            "global_usd_negative_pct":     safe_pct(grp, "negative"),
            "global_usd_positive_pct":     safe_pct(grp, "positive"),
            "global_usd_neutral_pct":      safe_pct(grp, "neutral"),
            "global_usd_avg_score":        round(grp["sentiment_score"].mean(), 4),
        })

    return pd.DataFrame(records)


def run():
    log.info("=" * 60)
    log.info("NLP Feature Aggregation — V3 NLP Pipeline")
    log.info("=" * 60)

    in_path = STAGING_DIR / "articles_sentiment.csv"
    if not in_path.exists():
        raise FileNotFoundError(f"Sentiment file not found: {in_path}\nRun extract_sentiment.py first.")

    df = pd.read_csv(in_path)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df = df[df["year"] >= 2015].copy()
    log.info(f"Articles loaded: {len(df):,}")

    # ── Country-year features ─────────────────────────────────────────────────
    features = build_country_year_features(df)
    log.info(f"\nCountry-year NLP rows: {len(features):,}")
    log.info(f"Countries covered    : {features['country_code'].nunique()}")
    log.info(f"Years covered        : {features['year'].min()} – {features['year'].max()}")

    feat_path = CURATED_DIR / "nlp_features.csv"
    features.to_csv(feat_path, index=False)
    log.info(f"Saved → {feat_path}")

    # ── Global USD sentiment ──────────────────────────────────────────────────
    global_usd = build_global_usd_sentiment(df)
    if len(global_usd) > 0:
        log.info(f"\nGlobal USD sentiment rows: {len(global_usd)}")
        log.info(global_usd[["year", "global_usd_negative_pct", "global_usd_positive_pct"]].to_string(index=False))
        usd_path = CURATED_DIR / "nlp_global_usd_sentiment.csv"
        global_usd.to_csv(usd_path, index=False)
        log.info(f"Saved → {usd_path}")

    # ── Preview top signals ───────────────────────────────────────────────────
    top = features.dropna(subset=["nlp_composite_signal"]).nlargest(10, "nlp_composite_signal")
    log.info(f"\nTop 10 country-years by composite NLP signal (gold bullish - USD bullish):")
    log.info(top[["country_code", "year", "nlp_composite_signal",
                  "nlp_gold_positive", "nlp_usd_negative"]].to_string(index=False))

    log.info("\nDone.")


if __name__ == "__main__":
    run()

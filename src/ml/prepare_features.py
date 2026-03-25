"""
ML Feature Preparation — V4 Machine Learning Model
Prepares the feature matrix and target vector for model training.

Target variable:
  will_accumulate_next_year — will this country's gold share increase next year?
  (1 = yes, 0 = no)

This is constructed by shifting is_accumulating forward by 1 year per country,
so the model learns: given THIS year's features, predict NEXT year's behaviour.

Feature sets:
  Core (always available, 2001–latest):
    gold_share_pct, accumulation_streak, gold_yoy_change_pct,
    gold_share_yoy_change, gold_share_vs_world, country_share_of_world_gold_pct,
    usd_share_drawdown_pct, usd_share_yoy_change, accumulating_during_usd_decline,
    sanctions_score, geo_risk_score, un_alignment_score

  Global context (always available):
    global_usd_negative_pct, global_usd_positive_pct, world_gold_share_pct

Train/test split: time-based
  Train: 2001–2019
  Test:  2020–latest  (post-COVID, sanctions acceleration era)

Input:  data/curated/master_panel_nlp.csv
Output: data/curated/ml_features.csv  (feature matrix + target, clean rows only)
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path

CURATED_DIR = Path(__file__).resolve().parents[2] / "data" / "curated"
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

FEATURE_COLS = [
    # Gold momentum
    "gold_share_pct",
    "accumulation_streak",
    "gold_yoy_change_pct",
    "gold_share_yoy_change",
    "gold_share_vs_world",
    "country_share_of_world_gold_pct",
    # USD dominance signals
    "usd_share_drawdown_pct",
    "usd_share_yoy_change",
    "accumulating_during_usd_decline",
    # Geopolitical signals
    "sanctions_score",
    "geo_risk_score",
    "un_alignment_score",
    # World context
    "global_usd_negative_pct",
    "global_usd_positive_pct",
    "world_gold_share_pct",
]

TARGET_COL = "will_accumulate_next_year"


def build_target(df: pd.DataFrame) -> pd.DataFrame:
    """
    Shift is_accumulating forward by 1 year per country to create target.
    Row for year Y gets target = is_accumulating in year Y+1.
    The final year row per country has no target → dropped.
    """
    df = df.sort_values(["country_code", "year"]).copy()
    df[TARGET_COL] = (
        df.groupby("country_code")["is_accumulating"].shift(-1)
    )
    # Drop rows where target is NaN (last year per country)
    df = df.dropna(subset=[TARGET_COL])
    df[TARGET_COL] = df[TARGET_COL].astype(int)
    return df


def run():
    log.info("=" * 60)
    log.info("ML Feature Preparation — V4")
    log.info("=" * 60)

    df = pd.read_csv(CURATED_DIR / "master_panel_nlp.csv")
    log.info(f"Panel loaded: {df.shape}")

    # Fill global USD sentiment with median (these are year-level)
    for col in ["global_usd_negative_pct", "global_usd_positive_pct"]:
        df[col] = df[col].fillna(df[col].median())

    max_year = int(df["year"].max())
    log.info(f"Data covers years {int(df['year'].min())}–{max_year}")

    # Build next-year target
    df = build_target(df)
    log.info(f"After target construction: {df.shape}")

    # Drop rows missing any core feature
    df_ml = df[["country", "country_code", "year", TARGET_COL] + FEATURE_COLS].copy()
    before = len(df_ml)
    df_ml = df_ml.dropna()
    log.info(f"After dropping rows with missing features: {len(df_ml):,} (dropped {before - len(df_ml):,})")

    # Target balance
    pos = df_ml[TARGET_COL].sum()
    neg = len(df_ml) - pos
    log.info(f"Target balance — will accumulate: {pos:,} ({pos/len(df_ml)*100:.1f}%) | won't: {neg:,} ({neg/len(df_ml)*100:.1f}%)")

    # Train / test split (time-based)
    train = df_ml[df_ml["year"] <= 2019]
    test  = df_ml[df_ml["year"] >= 2020]
    log.info(f"Train set: {len(train):,} rows (2001–2019)")
    log.info(f"Test set : {len(test):,} rows (2020–{max_year})")

    # Save
    out_path = CURATED_DIR / "ml_features.csv"
    df_ml.to_csv(out_path, index=False)
    log.info(f"Saved → {out_path}")

    return df_ml, train, test, FEATURE_COLS, TARGET_COL


if __name__ == "__main__":
    run()

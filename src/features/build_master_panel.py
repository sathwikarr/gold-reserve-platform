"""
Gold Layer — Master Panel
Merges country-level gold features with world-level USD dominance data.

Input:
  data/curated/gold_features.csv       (country x year)
  data/staging/usd_dominance_clean.csv (world x year)

Output:
  data/curated/master_panel.csv

Each row = one country in one year, with:
  - country gold metrics
  - world USD dominance context
  - relative signals (country gold share vs world trend)
"""

import pandas as pd
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parents[2]
CURATED_DIR = BASE_DIR / "data" / "curated"
STAGING_DIR = BASE_DIR / "data" / "staging"


def run():
    # ── 1. load both tables ───────────────────────────────────────────────────
    gold = pd.read_csv(CURATED_DIR / "gold_features.csv")
    usd  = pd.read_csv(STAGING_DIR / "usd_dominance_clean.csv")

    print(f"▶ Gold features : {gold.shape}")
    print(f"▶ USD dominance : {usd.shape}")

    # ── 2. merge on year (left join keeps all country-year rows) ──────────────
    panel = gold.merge(usd, on="year", how="left")
    print(f"▶ After merge   : {panel.shape}")

    # ── 3. relative signals ───────────────────────────────────────────────────
    # how much does this country's gold share deviate from world average?
    panel["gold_share_vs_world"] = (
        panel["gold_share_pct"] - panel["world_gold_share_pct"]
    ).round(2)

    # is country accumulating while USD is declining? (both signals aligned)
    panel["accumulating_during_usd_decline"] = (
        (panel["is_accumulating"] == 1) &
        (panel["usd_share_yoy_change"] < 0)
    ).astype(int)

    # country gold value as % of world gold value
    panel["country_share_of_world_gold_pct"] = (
        panel["gold_value_usd"] / (panel["world_gold_value_bn"] * 1e9) * 100
    ).round(4)

    # ── 4. save ───────────────────────────────────────────────────────────────
    out_path = CURATED_DIR / "master_panel.csv"
    panel.to_csv(out_path, index=False)

    print(f"\n✅ Saved → {out_path}")
    print(f"   Shape    : {panel.shape}")
    print(f"   Countries: {panel['country_code'].nunique()}")
    print(f"   Years    : {panel['year'].min()} – {panel['year'].max()}")
    print(f"   Columns  : {panel.columns.tolist()}")

    # ── 5. preview — countries accumulating most during USD decline ───────────
    print(f"\n   Countries with most years accumulating during USD decline:")
    summary = (
        panel.groupby(["country", "country_code"])
        .agg(
            years_aligned=("accumulating_during_usd_decline", "sum"),
            total_gold_added_bn=("gold_yoy_change_usd", lambda x: round(x.sum() / 1e9, 1)),
            latest_gold_share=("gold_share_pct", "last"),
            latest_streak=("accumulation_streak", "max"),
        )
        .reset_index()
        .sort_values("years_aligned", ascending=False)
        .head(15)
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    run()
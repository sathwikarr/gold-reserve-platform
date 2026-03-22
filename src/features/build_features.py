"""
Gold Layer — Feature Engineering
Input : data/staging/reserves_clean.csv
Output: data/curated/gold_features.csv

Features built:
  - gold_yoy_change_usd    : year-over-year change in gold value (USD)
  - gold_yoy_change_pct    : year-over-year % change in gold value
  - gold_share_yoy_change  : year-over-year change in gold share of reserves
  - gold_rank              : country rank by gold value (per year)
  - is_accumulating        : 1 if gold_yoy_change_usd > 0
  - accumulation_streak    : consecutive years of accumulation
"""

import pandas as pd
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parents[2]
STAGING_DIR = BASE_DIR / "data" / "staging"
CURATED_DIR = BASE_DIR / "data" / "curated"
CURATED_DIR.mkdir(parents=True, exist_ok=True)


def run():
    path = STAGING_DIR / "reserves_clean.csv"
    df = pd.read_csv(path)
    print(f"▶ Loaded: {df.shape[0]:,} rows, {df['country_code'].nunique()} countries")

    df = df.sort_values(["country_code", "year"]).reset_index(drop=True)

    # ── 1. year-over-year changes (per country) ───────────────────────────────
    grp = df.groupby("country_code")

    df["gold_yoy_change_usd"] = grp["gold_value_usd"].diff()
    df["gold_yoy_change_pct"] = (
        grp["gold_value_usd"].pct_change() * 100
    ).round(2)
    df["gold_share_yoy_change"] = grp["gold_share_pct"].diff().round(2)

    # ── 2. accumulation flag ──────────────────────────────────────────────────
    df["is_accumulating"] = (df["gold_yoy_change_usd"] > 0).astype(int)

    # ── 3. accumulation streak (consecutive years buying) ────────────────────
    def streak(s: pd.Series) -> pd.Series:
        result = []
        count = 0
        for val in s:
            if val == 1:
                count += 1
            else:
                count = 0
            result.append(count)
        return pd.Series(result, index=s.index)

    df["accumulation_streak"] = grp["is_accumulating"].transform(streak)

    # ── 4. annual rank by gold value ──────────────────────────────────────────
    df["gold_rank"] = (
        df.groupby("year")["gold_value_usd"]
        .rank(ascending=False, method="min", na_option="bottom")
        .astype(int)
    )

    # ── 5. save ───────────────────────────────────────────────────────────────
    out_path = CURATED_DIR / "gold_features.csv"
    df.to_csv(out_path, index=False)

    print(f"✅ Saved → {out_path}")
    print(f"   Shape  : {df.shape}")

    # ── 6. preview — most aggressive accumulators in last 5 years ────────────
    recent = df[df["year"] >= 2019].copy()
    summary = (
        recent.groupby(["country", "country_code"])
        .agg(
            years_accumulating=("is_accumulating", "sum"),
            total_gold_added_bn=("gold_yoy_change_usd", lambda x: round(x.sum() / 1e9, 1)),
            latest_streak=("accumulation_streak", "max"),
            latest_gold_share=("gold_share_pct", "last"),
        )
        .reset_index()
        .sort_values("total_gold_added_bn", ascending=False)
        .head(12)
    )
    print(f"\n   Top accumulators (2019–2024):")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    run()
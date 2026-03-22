"""
Silver Layer — Clean & Standardize World Bank Reserves
Input : data/raw/world_bank_reserves_YYYYMMDD.csv  (latest)
Output: data/staging/reserves_clean.csv

Steps:
  1. Load latest raw file
  2. Drop aggregates (regions, income groups — not real countries)
  3. Pivot wide: one row per country-year
  4. Derive gold_value_usd = total_reserves - reserves_excl_gold
  5. Drop rows where both reserve columns are null
  6. Standardize column names and dtypes
  7. Save to staging
"""

import pandas as pd
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parents[2]
RAW_DIR      = BASE_DIR / "data" / "raw"
STAGING_DIR  = BASE_DIR / "data" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# ── World Bank aggregate codes to drop (not real countries) ───────────────────
WB_AGGREGATES = {
    "AFE","AFW","ARB","CEB","CSS","EAP","EAR","EAS","ECA","ECS",
    "EMU","EUU","FCS","HIC","HPC","IBD","IBT","IDA","IDB","IDX",
    "LAC","LCN","LDC","LIC","LMC","LMY","LTE","MEA","MIC","MNA",
    "NAC","OED","OSS","PRE","PSS","PST","SAS","SSA","SSF","SST",
    "TEA","TEC","TLA","TMN","TSA","TSS","UMC","WLD",
}


def load_latest_raw() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("world_bank_reserves_*.csv"))
    if not files:
        raise FileNotFoundError(f"No raw files found in {RAW_DIR}")
    latest = files[-1]
    print(f"▶ Loading: {latest.name}")
    return pd.read_csv(latest)


def run():
    df = load_latest_raw()
    print(f"  Raw shape : {df.shape}")

    # 1. drop aggregates
    df = df[~df["country_code"].isin(WB_AGGREGATES)]
    print(f"  After dropping aggregates : {df['country_code'].nunique()} countries")

    # 2. pivot wide — one row per country + year
    df_wide = df.pivot_table(
        index=["country", "country_code", "year"],
        columns="indicator",
        values="value",
        aggfunc="first",
    ).reset_index()
    df_wide.columns.name = None

    # 3. rename for clarity
    df_wide = df_wide.rename(columns={
        "total_reserves_usd":       "total_reserves_usd",
        "total_reserves_excl_gold": "reserves_excl_gold_usd",
    })

    # 4. derive gold value
    df_wide["gold_value_usd"] = (
        df_wide["total_reserves_usd"] - df_wide["reserves_excl_gold_usd"]
    )

    # 5. drop rows where both source columns are null
    df_wide = df_wide.dropna(subset=["total_reserves_usd", "reserves_excl_gold_usd"], how="all")

    # 6. derive gold share of total reserves (%)
    df_wide["gold_share_pct"] = (
        df_wide["gold_value_usd"] / df_wide["total_reserves_usd"] * 100
    ).round(2)

    # 7. sort and tidy
    df_wide = df_wide.sort_values(["country_code", "year"]).reset_index(drop=True)
    df_wide["year"] = df_wide["year"].astype(int)

    # 8. save
    out_path = STAGING_DIR / "reserves_clean.csv"
    df_wide.to_csv(out_path, index=False)

    print(f"\n✅ Saved → {out_path}")
    print(f"   Shape    : {df_wide.shape}")
    print(f"   Countries: {df_wide['country_code'].nunique()}")
    print(f"   Years    : {df_wide['year'].min()} – {df_wide['year'].max()}")
    print(f"\n   Sample (top gold holders, latest year):")

    latest = df_wide[df_wide["year"] == df_wide["year"].max()].copy()
    top = (
        latest[latest["gold_value_usd"] > 0]
        .sort_values("gold_value_usd", ascending=False)
        .head(10)[["country", "gold_value_usd", "gold_share_pct"]]
    )
    top["gold_value_usd"] = (top["gold_value_usd"] / 1e9).round(1)
    top = top.rename(columns={
        "gold_value_usd":  "gold_USD_bn",
        "gold_share_pct":  "gold_%_of_reserves",
    })
    print(top.to_string(index=False))


if __name__ == "__main__":
    run()
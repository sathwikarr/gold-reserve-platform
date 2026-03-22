"""
Silver Layer — Clean USD Dominance Data
Input : data/raw/usd_dominance_YYYYMMDD.csv (latest)
Output: data/staging/usd_dominance_clean.csv
"""

import pandas as pd
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parents[2]
RAW_DIR     = BASE_DIR / "data" / "raw"
STAGING_DIR = BASE_DIR / "data" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)


def run():
    # load latest raw file
    files = sorted(RAW_DIR.glob("usd_dominance_*.csv"))
    if not files:
        raise FileNotFoundError("No usd_dominance raw file found")
    path = files[-1]
    print(f"▶ Loading: {path.name}")
    df = pd.read_csv(path)

    # clean column order
    df = df[[
        "year",
        "usd_share_of_reserves_pct",
        "usd_share_yoy_change",
        "world_total_reserves_usd",
        "world_gold_value_usd",
        "us_gdp_usd",
        "world_gdp_usd",
        "us_gdp_share_pct",
        "us_total_reserves_usd",
        "us_reserves_excl_gold",
        "us_gold_value_usd",
    ]]

    # derived: world gold share of total reserves
    df["world_gold_share_pct"] = (
        df["world_gold_value_usd"] / df["world_total_reserves_usd"] * 100
    ).round(2)

    # derived: USD share decline from 2000 peak (cumulative drawdown)
    peak = df.loc[df["year"] == 2000, "usd_share_of_reserves_pct"].values[0]
    df["usd_share_drawdown_pct"] = (df["usd_share_of_reserves_pct"] - peak).round(2)

    # scale large USD columns to billions for readability
    for col in ["world_total_reserves_usd", "world_gold_value_usd",
                "us_gdp_usd", "world_gdp_usd",
                "us_total_reserves_usd", "us_reserves_excl_gold", "us_gold_value_usd"]:
        df[col] = (df[col] / 1e9).round(2)

    # rename scaled columns
    df = df.rename(columns={
        "world_total_reserves_usd": "world_total_reserves_bn",
        "world_gold_value_usd":     "world_gold_value_bn",
        "us_gdp_usd":               "us_gdp_bn",
        "world_gdp_usd":            "world_gdp_bn",
        "us_total_reserves_usd":    "us_total_reserves_bn",
        "us_reserves_excl_gold":    "us_reserves_excl_gold_bn",
        "us_gold_value_usd":        "us_gold_value_bn",
    })

    out_path = STAGING_DIR / "usd_dominance_clean.csv"
    df.to_csv(out_path, index=False)

    print(f"✅ Saved → {out_path}")
    print(f"   Shape  : {df.shape}")
    print(f"\n   Full table:")
    print(df[["year", "usd_share_of_reserves_pct", "usd_share_drawdown_pct",
              "world_gold_value_bn", "world_gold_share_pct"]].to_string(index=False))


if __name__ == "__main__":
    run()
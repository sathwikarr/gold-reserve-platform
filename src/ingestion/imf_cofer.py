"""
USD Dominance Data Ingestion — v2
Sources:
  - World Bank API  : US GDP, World GDP, US reserves
  - IMF COFER       : USD share of global reserves (seeded from public IMF summary)
  - Local curated   : World gold totals derived from our own reserves_clean.csv

Output: data/raw/usd_dominance_YYYYMMDD.csv
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

RAW_DIR     = Path(__file__).resolve().parents[2] / "data" / "raw"
STAGING_DIR = Path(__file__).resolve().parents[2] / "data" / "staging"
RAW_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.worldbank.org/v2/country"

INDICATORS = {
    "us_gdp_usd":              ("USA", "NY.GDP.MKTP.CD"),
    "world_gdp_usd":           ("WLD", "NY.GDP.MKTP.CD"),
    "us_total_reserves_usd":   ("USA", "FI.RES.TOTL.CD"),
    "us_reserves_excl_gold":   ("USA", "FI.RES.XGLD.CD"),
}

# IMF COFER USD share of allocated reserves — Q4 each year
# Source: IMF COFER public summary table
# https://data.imf.org/?sk=E6A5F467-C14B-4AA8-9F6D-5A09EC4E62A4
# NOTE: Update this dictionary when new COFER data is published.
#       Check latest at: https://data.imf.org/regular.aspx?key=41175
#       The 2025 Q4 value should be available by March–April 2026.
COFER_USD_SHARE = {
    2000: 71.13, 2001: 71.51, 2002: 67.11, 2003: 65.45, 2004: 65.86,
    2005: 66.51, 2006: 65.47, 2007: 63.87, 2008: 64.15, 2009: 62.14,
    2010: 61.79, 2011: 62.59, 2012: 61.47, 2013: 61.24, 2014: 65.14,
    2015: 65.74, 2016: 65.34, 2017: 62.72, 2018: 61.69, 2019: 60.89,
    2020: 59.02, 2021: 58.81, 2022: 58.36, 2023: 57.33, 2024: 57.08,
    # TODO: Add 2025 value when IMF publishes Q4 2025 COFER data
}


def fetch_wb_series(country: str, indicator: str, label: str) -> pd.DataFrame:
    print(f"  ▶ {label}")
    records = []
    page = 1
    with tqdm(desc="    pages", unit="pg", leave=False) as pbar:
        while True:
            params = {"format": "json", "date": "2000:2025", "per_page": 500, "page": page}
            resp = requests.get(
                f"{BASE_URL}/{country}/indicator/{indicator}",
                params=params, timeout=30
            )
            resp.raise_for_status()
            payload = resp.json()
            if len(payload) < 2 or not payload[1]:
                break
            meta, data = payload
            records.extend(data)
            pbar.update(1)
            if page >= meta["pages"]:
                break
            page += 1

    df = pd.DataFrame([{
        "year":   int(r["date"]),
        "value":  r["value"],
        "series": label,
    } for r in records if r["value"] is not None])
    print(f"    ✓ {len(df)} rows")
    return df


def run():
    # ── 1. World Bank series ──────────────────────────────────────────────────
    frames = []
    for label, (country, indicator) in INDICATORS.items():
        df = fetch_wb_series(country, indicator, label)
        if not df.empty:
            frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    df_wide = raw.pivot_table(
        index="year", columns="series", values="value", aggfunc="first"
    ).reset_index()
    df_wide.columns.name = None
    df_wide = df_wide.sort_values("year").reset_index(drop=True)

    # ── 2. World gold totals from our own staging data ────────────────────────
    reserves_path = STAGING_DIR / "reserves_clean.csv"
    if reserves_path.exists():
        print(f"\n  ▶ Loading world gold totals from {reserves_path.name}")
        res = pd.read_csv(reserves_path)
        world_gold = (
            res.groupby("year")[["total_reserves_usd", "gold_value_usd"]]
            .sum()
            .reset_index()
            .rename(columns={
                "total_reserves_usd": "world_total_reserves_usd",
                "gold_value_usd":     "world_gold_value_usd",
            })
        )
        df_wide = df_wide.merge(world_gold, on="year", how="left")
        print(f"    ✓ merged world gold totals for {len(world_gold)} years")

    # ── 3. IMF COFER USD share ────────────────────────────────────────────────
    df_wide["usd_share_of_reserves_pct"] = df_wide["year"].map(COFER_USD_SHARE)
    df_wide["usd_share_yoy_change"]      = df_wide["usd_share_of_reserves_pct"].diff().round(2)

    # ── 4. Derived signals ────────────────────────────────────────────────────
    df_wide["us_gdp_share_pct"] = (
        df_wide["us_gdp_usd"] / df_wide["world_gdp_usd"] * 100
    ).round(2)

    df_wide["us_gold_value_usd"] = (
        df_wide["us_total_reserves_usd"] - df_wide["us_reserves_excl_gold"]
    )

    # ── 5. Save ───────────────────────────────────────────────────────────────
    today    = datetime.now().strftime("%Y%m%d")
    out_path = RAW_DIR / f"usd_dominance_{today}.csv"
    df_wide.to_csv(out_path, index=False)

    print(f"\n✅ Saved → {out_path}")
    print(f"   Shape : {df_wide.shape}")
    print(f"   Columns: {df_wide.columns.tolist()}")

    print(f"\n   USD share decline vs world gold growth:")
    display = df_wide[["year", "usd_share_of_reserves_pct",
                        "usd_share_yoy_change", "world_gold_value_usd"]].copy()
    display["world_gold_value_usd"] = (display["world_gold_value_usd"] / 1e12).round(2)
    display = display.rename(columns={
        "usd_share_of_reserves_pct": "usd_share_%",
        "usd_share_yoy_change":      "yoy_chg",
        "world_gold_value_usd":      "world_gold_tn",
    })
    print(display.to_string(index=False))


if __name__ == "__main__":
    run()
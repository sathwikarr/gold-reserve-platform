"""
World Gold Council (WGC) / IMF IFS Gold Data Ingestion
=======================================================
Source: World Gold Council — Goldhub
Files:  World_official_gold_holdings_as_of_Mar2026_IFS.xlsx
        Changes_latest_as_of_Mar2026_IFS.xlsx

These files come from the IMF International Financial Statistics (IFS),
March 2026 edition, published by the World Gold Council.

What this script does:
  1. Parses current gold holdings (tonnes) for ~100 countries
  2. Parses annual changes (tonnes) 2002–2025 for ~162 countries
  3. Reconstructs a complete time-series of gold tonnes per country 2000–2025
  4. Converts tonnes → USD using historical annual gold price averages
  5. Outputs: data/raw/wgc_gold_timeseries.csv

This file is then used by clean_reserves.py to SUPPLEMENT/UPDATE the
World Bank reserves data with more accurate gold values, particularly for 2025.

Gold price sources:
  - 2000–2024: World Gold Council historical annual average prices
  - 2025: Full-year 2025 average (~$2,869/oz based on LBMA data)

Troy ounces per metric tonne: 32,150.7374
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# ── Annual average gold prices (USD per troy oz) ──────────────────────────────
# Source: World Gold Council / LBMA
GOLD_PRICE_USD_OZ = {
    2000: 279.11, 2001: 271.04, 2002: 309.73, 2003: 363.38, 2004: 409.72,
    2005: 444.74, 2006: 603.77, 2007: 695.39, 2008: 871.96, 2009: 972.35,
    2010: 1224.53, 2011: 1571.52, 2012: 1668.98, 2013: 1411.23, 2014: 1266.40,
    2015: 1160.06, 2016: 1250.74, 2017: 1257.15, 2018: 1268.49, 2019: 1392.60,
    2020: 1769.64, 2021: 1798.61, 2022: 1800.93, 2023: 1940.54, 2024: 2386.33,
    2025: 2869.00,  # Full-year 2025 average (LBMA)
}

TROY_OZ_PER_TONNE = 32_150.7374

# Country name mapping: WGC names → standardised names
WGC_NAME_MAP = {
    "China, P.R.: Mainland":               "China",
    "Russian Federation":                  "Russian Federation",
    "Poland, Rep. of":                     "Poland",
    "Kazakhstan, Rep. of":                 "Kazakhstan",
    "Uzbekistan, Rep. of":                 "Uzbekistan",
    "Czech Rep.":                          "Czechia",
    "Korea, Rep. of":                      "Korea, Rep.",
    "Turkey*":                             "Turkiye",
    "Turkey5)":                            "Turkiye",
    "Belarus, Rep. of4)":                  "Belarus",
    "Belarus, Rep. of":                    "Belarus",
    "Serbia, Rep. of":                     "Serbia",
    "Kyrgyz Rep.":                         "Kyrgyz Republic",
    "Egypt, Arab Rep. of":                 "Egypt, Arab Rep.",
    "Philippines":                         "Philippines",
    "Taiwan Province of China":            "Taiwan, China",
    "Aruba, Kingdom of the Netherlands":   "Aruba",
    "Bosnia and Herzegovina":              "Bosnia and Herzegovina",
    "Armenia, Rep. of":                    "Armenia",
    "Azerbaijan, Rep. of":                 "Azerbaijan",
    "Hong Kong SAR":                       "Hong Kong SAR, China",
    "Mozambique, Rep. of":                 "Mozambique",
    "Netherlands, The":                    "Netherlands",
    "Sri Lanka":                           "Sri Lanka",
    "Zimbabwe":                            "Zimbabwe",
    "North Macedonia, Republic of":        "North Macedonia",
    "Afghanistan, Islamic Rep. of":        "Afghanistan",
    "State Oil Fund of the Republic of Azerbaijan (SOFAZ)": None,  # skip — not a country
    "Euro Area":                           None,   # skip — aggregate
    "ECB":                                 None,   # skip — institution
    "IMF":                                 None,   # skip — institution
}


def parse_holdings(raw_dir: Path) -> pd.DataFrame:
    """Parse the current holdings snapshot (Jan 2026)."""
    path = raw_dir / "World_official_gold_holdings_as_of_Mar2026_IFS.xlsx"
    raw  = pd.read_excel(path, sheet_name="PDF")

    left  = raw.iloc[4:, :5].copy()
    right = raw.iloc[4:, 5:].copy()
    left.columns  = ["rank", "country", "tonnes", "pct_reserves", "holdings_as_of"]
    right.columns = ["rank", "country", "tonnes", "pct_reserves", "holdings_as_of"]

    df = pd.concat([left, right], ignore_index=True)
    df = df[df["country"].notna() & (df["country"] != "Tonnes")]
    df = df[pd.to_numeric(df["rank"], errors="coerce").notna()]
    df["tonnes"]       = pd.to_numeric(df["tonnes"], errors="coerce")
    df["pct_reserves"] = pd.to_numeric(df["pct_reserves"], errors="coerce")
    df = df[["country", "tonnes", "pct_reserves"]].dropna(subset=["tonnes"]).copy()
    df["country"] = df["country"].map(lambda x: WGC_NAME_MAP.get(x, x))
    df = df[df["country"].notna()]  # drop institutions / aggregates
    print(f"  Holdings snapshot: {len(df)} countries")
    return df


def parse_changes(raw_dir: Path) -> pd.DataFrame:
    """Parse the annual changes in gold holdings (tonnes) 2002–2025."""
    path = raw_dir / "Changes_latest_as_of_Mar2026_IFS.xlsx"
    df   = pd.read_excel(path, sheet_name="Annual")
    df["Country"] = df["Country"].map(lambda x: WGC_NAME_MAP.get(x, x))
    df = df[df["Country"].notna()]  # drop institutions
    year_cols = [c for c in df.columns if isinstance(c, int) and 2000 <= c <= 2025]
    df = df[["Country"] + year_cols].copy()
    df = df.set_index("Country")
    print(f"  Changes data: {len(df)} countries × {len(year_cols)} years ({min(year_cols)}–{max(year_cols)})")
    return df


def build_timeseries(holdings: pd.DataFrame, changes: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct gold tonnes per country per year 2000–2025.

    Method:
      - Holdings snapshot = end of 2025 (Jan 2026)
      - Work backwards: tonnes(year) = tonnes(year+1) - change(year+1)
    """
    snap    = holdings.set_index("country")["tonnes"].to_dict()
    snap_pct = holdings.set_index("country")["pct_reserves"].to_dict()
    records = []
    years   = list(range(2000, 2026))

    for country, tonnes_2025 in snap.items():
        # Get changes series for this country
        if country in changes.index:
            chg_row = changes.loc[country]
        else:
            chg_row = None

        # Rebuild yearly holdings by going backwards from 2025
        yearly = {2025: tonnes_2025}
        for yr in range(2024, 1999, -1):
            prev = yearly[yr + 1]
            delta = float(chg_row[yr + 1]) if (chg_row is not None and (yr + 1) in chg_row.index
                                               and pd.notna(chg_row[yr + 1])) else 0.0
            yearly[yr] = max(prev - delta, 0.0)

        for yr in years:
            records.append({
                "country": country,
                "year":    yr,
                "gold_tonnes": round(yearly[yr], 6),
                # pct_reserves only for 2025 from snapshot
                "wgc_gold_pct_reserves": snap_pct.get(country) if yr == 2025 else np.nan,
            })

    df = pd.DataFrame(records)
    print(f"  Time series built: {df.shape} | Years: {df.year.min()}–{df.year.max()}")
    return df


def add_usd_values(df: pd.DataFrame) -> pd.DataFrame:
    """Convert gold tonnes → USD using annual average gold prices."""
    df["gold_price_usd_oz"] = df["year"].map(GOLD_PRICE_USD_OZ)
    df["wgc_gold_value_usd"] = (
        df["gold_tonnes"] * TROY_OZ_PER_TONNE * df["gold_price_usd_oz"]
    ).round(0)
    return df


def run():
    print("=" * 60)
    print("WGC / IMF IFS Gold Data Ingestion — March 2026")
    print("=" * 60)

    holdings = parse_holdings(RAW_DIR)
    changes  = parse_changes(RAW_DIR)
    ts       = build_timeseries(holdings, changes)
    ts       = add_usd_values(ts)

    # Preview 2025 top buyers
    top2025 = (
        ts[ts.year == 2025]
        .sort_values("wgc_gold_value_usd", ascending=False)
        .head(15)[["country", "gold_tonnes", "wgc_gold_value_usd", "wgc_gold_pct_reserves"]]
    )
    top2025["wgc_gold_value_usd_bn"] = (top2025["wgc_gold_value_usd"] / 1e9).round(2)
    top2025["wgc_gold_pct_reserves"] = (top2025["wgc_gold_pct_reserves"] * 100).round(2)
    print(f"\n  Top 15 gold holders (2025, WGC/IFS):")
    print(top2025[["country", "gold_tonnes", "wgc_gold_value_usd_bn", "wgc_gold_pct_reserves"]].to_string(index=False))

    # Save
    out_path = RAW_DIR / "wgc_gold_timeseries.csv"
    ts.to_csv(out_path, index=False)
    print(f"\n✅ Saved → {out_path}")
    print(f"   Shape  : {ts.shape}")
    print(f"   Countries: {ts.country.nunique()}")
    print(f"   Years  : {ts.year.min()}–{ts.year.max()}")

    return ts


if __name__ == "__main__":
    run()

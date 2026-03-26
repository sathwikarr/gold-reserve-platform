"""
Silver Layer — Clean & Standardize World Bank Reserves
Input : data/raw/world_bank_reserves_YYYYMMDD.csv  (latest)
        data/raw/wgc_gold_timeseries.csv            (WGC/IMF IFS gold data — optional)
Output: data/staging/reserves_clean.csv

Steps:
  1. Load latest World Bank raw file
  2. Drop aggregates (regions, income groups — not real countries)
  3. Pivot wide: one row per country-year
  4. Derive gold_value_usd = total_reserves - reserves_excl_gold
  5. SUPPLEMENT with WGC gold data (more accurate gold values from IMF IFS)
  6. Drop rows where both reserve columns are null
  7. Standardize column names and dtypes
  8. Save to staging

WGC Integration:
  The World Gold Council (WGC) provides gold holdings in tonnes from IMF IFS.
  We convert tonnes → USD using annual gold price averages and use these values
  to supplement/correct World Bank gold data, especially for 2025 where WGC
  data (March 2026 edition) is more complete and accurate.
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
    print(f"▶ Loading World Bank: {latest.name}")
    return pd.read_csv(latest)


def load_wgc() -> pd.DataFrame | None:
    """Load WGC gold time series if available."""
    path = RAW_DIR / "wgc_gold_timeseries.csv"
    if not path.exists():
        print("  WGC gold data not found — using World Bank only")
        return None
    wgc = pd.read_csv(path)
    print(f"▶ Loading WGC gold data: {path.name} ({len(wgc):,} rows, {wgc['country'].nunique()} countries)")
    return wgc


def merge_wgc(df_wide: pd.DataFrame, wgc: pd.DataFrame) -> pd.DataFrame:
    """
    Supplement World Bank gold values with WGC/IFS gold data.

    Strategy:
      - For each country-year present in WGC, prefer WGC gold values
        (uses actual tonnage from IMF IFS + LBMA prices).
      - For 2025 rows where World Bank has no data, WGC provides the only
        source — also derive total_reserves_usd from gold + pct where available.
      - Always keep World Bank total_reserves_usd for prior years.
    """
    wgc_merge = wgc[["country", "year", "wgc_gold_value_usd", "wgc_gold_pct_reserves"]].copy()
    # pct_reserves in WGC file is a fraction (0.747 = 74.7%) — convert to %
    wgc_merge["wgc_gold_pct_reserves"] = wgc_merge["wgc_gold_pct_reserves"] * 100

    # Merge on country name + year
    df_wide = df_wide.merge(wgc_merge, on=["country", "year"], how="left")

    # Fuzzy fallback: first-10-chars match for names not found exactly
    unmatched_mask = df_wide["wgc_gold_value_usd"].isna()
    if unmatched_mask.any():
        wgc_by_cy = wgc_merge.set_index(["country", "year"])
        for idx in df_wide[unmatched_mask].index:
            wb_name = str(df_wide.at[idx, "country"]).lower()[:10]
            yr = df_wide.at[idx, "year"]
            for wgc_name, wgc_yr in wgc_by_cy.index:
                if wgc_yr == yr and str(wgc_name).lower()[:10] == wb_name:
                    df_wide.at[idx, "wgc_gold_value_usd"] = wgc_by_cy.at[(wgc_name, yr), "wgc_gold_value_usd"]
                    df_wide.at[idx, "wgc_gold_pct_reserves"] = wgc_by_cy.at[(wgc_name, yr), "wgc_gold_pct_reserves"]
                    break

    matched = df_wide["wgc_gold_value_usd"].notna().sum()
    print(f"  WGC matched: {matched:,} / {len(df_wide):,} rows")

    # Override gold_value_usd with WGC where available
    has_wgc = df_wide["wgc_gold_value_usd"].notna() & (df_wide["wgc_gold_value_usd"] > 0)
    df_wide.loc[has_wgc, "gold_value_usd"] = df_wide.loc[has_wgc, "wgc_gold_value_usd"]

    # Override gold_share_pct with WGC where official pct is available
    has_wgc_pct = df_wide["wgc_gold_pct_reserves"].notna()
    df_wide.loc[has_wgc_pct, "gold_share_pct"] = df_wide.loc[has_wgc_pct, "wgc_gold_pct_reserves"].round(2)

    # For 2025 rows: derive total_reserves_usd from WGC gold + pct
    # total_reserves = gold_value / (gold_pct / 100)
    y2025_wgc = (
        (df_wide["year"] == 2025)
        & has_wgc
        & has_wgc_pct
        & df_wide["total_reserves_usd"].isna()
        & (df_wide["wgc_gold_pct_reserves"] > 0)
    )
    if y2025_wgc.any():
        df_wide.loc[y2025_wgc, "total_reserves_usd"] = (
            df_wide.loc[y2025_wgc, "wgc_gold_value_usd"]
            / (df_wide.loc[y2025_wgc, "wgc_gold_pct_reserves"] / 100)
        ).round(0)
        df_wide.loc[y2025_wgc, "reserves_excl_gold_usd"] = (
            df_wide.loc[y2025_wgc, "total_reserves_usd"]
            - df_wide.loc[y2025_wgc, "wgc_gold_value_usd"]
        )
        print(f"  2025 total_reserves derived from WGC for {y2025_wgc.sum()} countries")

    df_wide = df_wide.drop(columns=["wgc_gold_value_usd", "wgc_gold_pct_reserves"])
    return df_wide


def build_wgc_2025_rows(wgc: pd.DataFrame, wb_name_code: dict) -> pd.DataFrame:
    """
    Build standalone 2025 rows from WGC data for countries where
    World Bank has no 2025 data (pivot_table drops all-null rows).

    wb_name_code: dict mapping country_name → country_code (ISO3) from WB data.
    """
    wgc25 = wgc[wgc["year"] == 2025].copy()
    # pct is stored as fraction in wgc timeseries CSV
    wgc25 = wgc25[wgc25["wgc_gold_value_usd"] > 0].copy()

    rows = []
    for _, r in wgc25.iterrows():
        cname = r["country"]
        code  = wb_name_code.get(cname)
        if code is None:
            # Fuzzy: try first 10 chars
            for wbname, wbcode in wb_name_code.items():
                if str(wbname).lower()[:10] == str(cname).lower()[:10]:
                    code = wbcode
                    break
        if code is None:
            continue  # can't link to WB country code — skip

        gold_val = float(r["wgc_gold_value_usd"])
        pct_frac = r["wgc_gold_pct_reserves"]  # fraction (0.747) or NaN

        total_res = None
        excl_gold = None
        gold_pct  = None
        if pd.notna(pct_frac) and pct_frac > 0:
            pct_pct   = pct_frac * 100          # → percent (74.7)
            total_res = gold_val / pct_frac      # total reserves
            excl_gold = total_res - gold_val
            gold_pct  = round(pct_pct, 2)

        rows.append({
            "country":              cname,
            "country_code":         code,
            "year":                 2025,
            "total_reserves_usd":   total_res,
            "reserves_excl_gold_usd": excl_gold,
            "gold_value_usd":       gold_val,
            "gold_share_pct":       gold_pct,
        })

    df_2025 = pd.DataFrame(rows)
    print(f"  WGC 2025 rows built: {len(df_2025)} countries")
    return df_2025


def run():
    df    = load_latest_raw()
    wgc   = load_wgc()
    print(f"  Raw shape : {df.shape}")

    # Build country name → ISO3 code mapping from WB data (for 2025 WGC row injection)
    wb_name_code = (
        df[["country", "country_code"]]
        .drop_duplicates()
        .set_index("country")["country_code"]
        .to_dict()
    )

    # 1. drop aggregates
    df = df[~df["country_code"].isin(WB_AGGREGATES)]
    print(f"  After dropping aggregates : {df['country_code'].nunique()} countries")

    # 2. pivot wide — one row per country + year
    #    NOTE: pivot_table drops all-null rows, so 2025 WB rows disappear here
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

    # 4. derive gold value from World Bank
    df_wide["gold_value_usd"] = (
        df_wide["total_reserves_usd"] - df_wide["reserves_excl_gold_usd"]
    )

    # 5. drop rows where both World Bank reserve columns are null (pre-WGC)
    df_wide = df_wide.dropna(subset=["total_reserves_usd", "reserves_excl_gold_usd"], how="all")

    # 6. derive gold share from World Bank
    df_wide["gold_share_pct"] = (
        df_wide["gold_value_usd"] / df_wide["total_reserves_usd"] * 100
    ).round(2)

    # 7. SUPPLEMENT existing rows with WGC/IFS gold data (more accurate)
    if wgc is not None:
        df_wide = merge_wgc(df_wide, wgc)

    # 8. ADD 2025 rows from WGC (WB pivot dropped them — all-null values)
    if wgc is not None:
        df_2025 = build_wgc_2025_rows(wgc, wb_name_code)
        # Only add countries not already in df_wide for year 2025
        existing_2025 = set(df_wide[df_wide["year"] == 2025]["country_code"].tolist())
        df_2025 = df_2025[~df_2025["country_code"].isin(existing_2025)]
        df_wide = pd.concat([df_wide, df_2025], ignore_index=True)
        print(f"  After adding WGC 2025 rows: max year = {int(df_wide['year'].max())}")

    # 8. sort and tidy
    df_wide = df_wide.sort_values(["country_code", "year"]).reset_index(drop=True)
    df_wide["year"] = df_wide["year"].astype(int)

    # 9. save
    out_path = STAGING_DIR / "reserves_clean.csv"
    df_wide.to_csv(out_path, index=False)

    print(f"\n✅ Saved → {out_path}")
    print(f"   Shape    : {df_wide.shape}")
    print(f"   Countries: {df_wide['country_code'].nunique()}")
    print(f"   Years    : {df_wide['year'].min()} – {df_wide['year'].max()}")
    print(f"\n   Top gold holders (latest year, WGC-supplemented):")

    latest_yr = df_wide["year"].max()
    latest = df_wide[df_wide["year"] == latest_yr].copy()
    top = (
        latest[latest["gold_value_usd"] > 0]
        .sort_values("gold_value_usd", ascending=False)
        .head(10)[["country", "gold_value_usd", "gold_share_pct"]]
    )
    top["gold_value_usd"] = (top["gold_value_usd"] / 1e9).round(1)
    top = top.rename(columns={"gold_value_usd": "gold_USD_bn", "gold_share_pct": "gold_%"})
    print(top.to_string(index=False))


if __name__ == "__main__":
    run()
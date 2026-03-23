"""
Tableau Data Export
Prepares a clean, flat CSV from master_panel_geo.csv optimized for Tableau.

- Renames columns to human-readable labels
- Adds region classification
- Rounds floats for cleaner Tableau display
- Saves to data/curated/tableau_export.csv
"""

import pandas as pd
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parents[2]
CURATED_DIR = BASE_DIR / "data" / "curated"


# World Bank region mapping
REGION_MAP = {
    "AFG":"South Asia","AGO":"Sub-Saharan Africa","ALB":"Europe & Central Asia",
    "ARE":"Middle East & North Africa","ARG":"Latin America & Caribbean",
    "ARM":"Europe & Central Asia","AUS":"East Asia & Pacific","AUT":"Europe & Central Asia",
    "AZE":"Europe & Central Asia","BEL":"Europe & Central Asia","BFA":"Sub-Saharan Africa",
    "BGD":"South Asia","BGR":"Europe & Central Asia","BHR":"Middle East & North Africa",
    "BLR":"Europe & Central Asia","BOL":"Latin America & Caribbean",
    "BRA":"Latin America & Caribbean","CAF":"Sub-Saharan Africa",
    "CAN":"North America","CHE":"Europe & Central Asia","CHL":"Latin America & Caribbean",
    "CHN":"East Asia & Pacific","CIV":"Sub-Saharan Africa","CMR":"Sub-Saharan Africa",
    "COD":"Sub-Saharan Africa","COL":"Latin America & Caribbean",
    "CRI":"Latin America & Caribbean","CUB":"Latin America & Caribbean",
    "CZE":"Europe & Central Asia","DEU":"Europe & Central Asia","DNK":"Europe & Central Asia",
    "DOM":"Latin America & Caribbean","DZA":"Middle East & North Africa",
    "ECU":"Latin America & Caribbean","EGY":"Middle East & North Africa",
    "ESP":"Europe & Central Asia","EST":"Europe & Central Asia",
    "ETH":"Sub-Saharan Africa","FIN":"Europe & Central Asia","FRA":"Europe & Central Asia",
    "GBR":"Europe & Central Asia","GEO":"Europe & Central Asia","GHA":"Sub-Saharan Africa",
    "GIN":"Sub-Saharan Africa","GRC":"Europe & Central Asia","HRV":"Europe & Central Asia",
    "HTI":"Latin America & Caribbean","HUN":"Europe & Central Asia",
    "IDN":"East Asia & Pacific","IND":"South Asia","IRL":"Europe & Central Asia",
    "IRN":"Middle East & North Africa","IRQ":"Middle East & North Africa",
    "ISR":"Middle East & North Africa","ITA":"Europe & Central Asia",
    "JOR":"Middle East & North Africa","JPN":"East Asia & Pacific",
    "KAZ":"Europe & Central Asia","KEN":"Sub-Saharan Africa",
    "KGZ":"Europe & Central Asia","KHM":"East Asia & Pacific",
    "KOR":"East Asia & Pacific","KWT":"Middle East & North Africa",
    "LAO":"East Asia & Pacific","LBN":"Middle East & North Africa",
    "LBY":"Middle East & North Africa","LKA":"South Asia","LTU":"Europe & Central Asia",
    "LUX":"Europe & Central Asia","LVA":"Europe & Central Asia",
    "MAR":"Middle East & North Africa","MDA":"Europe & Central Asia",
    "MEX":"Latin America & Caribbean","MKD":"Europe & Central Asia",
    "MLI":"Sub-Saharan Africa","MMR":"East Asia & Pacific","MNG":"East Asia & Pacific",
    "MOZ":"Sub-Saharan Africa","MRT":"Sub-Saharan Africa","MYS":"East Asia & Pacific",
    "NGA":"Sub-Saharan Africa","NIC":"Latin America & Caribbean",
    "NLD":"Europe & Central Asia","NOR":"Europe & Central Asia","NPL":"South Asia",
    "NZL":"East Asia & Pacific","OMN":"Middle East & North Africa",
    "PAK":"South Asia","PAN":"Latin America & Caribbean","PER":"Latin America & Caribbean",
    "PHL":"East Asia & Pacific","POL":"Europe & Central Asia","PRT":"Europe & Central Asia",
    "PRK":"East Asia & Pacific","PSE":"Middle East & North Africa",
    "QAT":"Middle East & North Africa","ROU":"Europe & Central Asia",
    "RUS":"Europe & Central Asia","SAU":"Middle East & North Africa",
    "SDN":"Sub-Saharan Africa","SEN":"Sub-Saharan Africa","SGP":"East Asia & Pacific",
    "SOM":"Sub-Saharan Africa","SRB":"Europe & Central Asia","SVK":"Europe & Central Asia",
    "SVN":"Europe & Central Asia","SWE":"Europe & Central Asia","CHE":"Europe & Central Asia",
    "SYR":"Middle East & North Africa","THA":"East Asia & Pacific","TUN":"Middle East & North Africa",
    "TUR":"Europe & Central Asia","TZA":"Sub-Saharan Africa","UGA":"Sub-Saharan Africa",
    "UKR":"Europe & Central Asia","URY":"Latin America & Caribbean",
    "USA":"North America","UZB":"Europe & Central Asia","VEN":"Latin America & Caribbean",
    "VNM":"East Asia & Pacific","YEM":"Middle East & North Africa",
    "ZAF":"Sub-Saharan Africa","ZMB":"Sub-Saharan Africa","ZWE":"Sub-Saharan Africa",
}


def run():
    df = pd.read_csv(CURATED_DIR / "master_panel_geo.csv")
    print(f"▶ Loaded master panel: {df.shape}")

    # ── add region ────────────────────────────────────────────────────────────
    df["region"] = df["country_code"].map(REGION_MAP).fillna("Other")

    # ── round floats ──────────────────────────────────────────────────────────
    float_cols = [
        "gold_value_usd", "total_reserves_usd", "reserves_excl_gold_usd",
        "gold_share_pct", "gold_yoy_change_usd", "gold_yoy_change_pct",
        "gold_share_yoy_change", "usd_share_of_reserves_pct",
        "usd_share_yoy_change", "usd_share_drawdown_pct",
        "world_gold_value_bn", "world_total_reserves_bn",
        "us_gdp_share_pct", "world_gold_share_pct",
        "gold_share_vs_world", "country_share_of_world_gold_pct",
        "geo_risk_score", "un_alignment_score", "un_divergence_score",
    ]
    for col in float_cols:
        if col in df.columns:
            df[col] = df[col].round(2)

    # ── scale gold value to billions for readability in Tableau ──────────────
    df["gold_value_bn"]         = (df["gold_value_usd"] / 1e9).round(2)
    df["gold_yoy_change_bn"]    = (df["gold_yoy_change_usd"] / 1e9).round(2)
    df["total_reserves_bn"]     = (df["total_reserves_usd"] / 1e9).round(2)

    # ── rename columns to human-readable labels ───────────────────────────────
    df = df.rename(columns={
        "country":                    "Country",
        "country_code":               "ISO3",
        "year":                       "Year",
        "gold_value_bn":              "Gold Value (USD bn)",
        "gold_share_pct":             "Gold Share of Reserves (%)",
        "gold_yoy_change_bn":         "Gold YoY Change (USD bn)",
        "gold_yoy_change_pct":        "Gold YoY Change (%)",
        "gold_share_yoy_change":      "Gold Share YoY Change (pp)",
        "is_accumulating":            "Is Accumulating",
        "accumulation_streak":        "Accumulation Streak (yrs)",
        "gold_rank":                  "Gold Rank",
        "total_reserves_bn":          "Total Reserves (USD bn)",
        "usd_share_of_reserves_pct":  "USD Share of Global Reserves (%)",
        "usd_share_drawdown_pct":     "USD Share Drawdown from 2000 (pp)",
        "world_gold_value_bn":        "World Gold Reserves (USD bn)",
        "world_gold_share_pct":       "World Gold Share (%)",
        "gold_share_vs_world":        "Gold Share vs World Avg (pp)",
        "accumulating_during_usd_decline": "Accumulating During USD Decline",
        "country_share_of_world_gold_pct": "Country Share of World Gold (%)",
        "un_alignment_score":         "UN Alignment with US (score)",
        "un_divergence_score":        "UN Divergence Score",
        "sanctions_score":            "Sanctions Severity (0-3)",
        "sanctions_active":           "Under Sanctions",
        "geo_bloc":                   "Geopolitical Bloc",
        "geo_risk_score":             "Geo Risk Score",
        "geo_risk_tier":              "Geo Risk Tier",
        "region":                     "Region",
        "us_gdp_share_pct":           "US GDP Share of World (%)",
    })

    # ── select and order final columns ────────────────────────────────────────
    keep = [
        "Country", "ISO3", "Year", "Region",
        "Gold Value (USD bn)", "Gold Share of Reserves (%)",
        "Gold YoY Change (USD bn)", "Gold YoY Change (%)",
        "Gold Share YoY Change (pp)", "Is Accumulating",
        "Accumulation Streak (yrs)", "Gold Rank",
        "Total Reserves (USD bn)",
        "USD Share of Global Reserves (%)",
        "USD Share Drawdown from 2000 (pp)",
        "World Gold Reserves (USD bn)",
        "World Gold Share (%)",
        "Gold Share vs World Avg (pp)",
        "Accumulating During USD Decline",
        "Country Share of World Gold (%)",
        "UN Alignment with US (score)",
        "UN Divergence Score",
        "Sanctions Severity (0-3)",
        "Under Sanctions",
        "Geopolitical Bloc",
        "Geo Risk Score",
        "Geo Risk Tier",
        "US GDP Share of World (%)",
    ]
    df = df[[c for c in keep if c in df.columns]]

    out_path = CURATED_DIR / "tableau_export.csv"
    df.to_csv(out_path, index=False)

    print(f"✅ Saved → {out_path}")
    print(f"   Shape    : {df.shape}")
    print(f"   Columns  : {df.columns.tolist()}")
    print(f"\n   Sample (top gold holders 2024):")
    latest = df[df["Year"] == 2024].nlargest(8, "Gold Value (USD bn)")
    print(latest[["Country", "Gold Value (USD bn)",
                  "Gold Share of Reserves (%)", "Geopolitical Bloc",
                  "Accumulation Streak (yrs)"]].to_string(index=False))


if __name__ == "__main__":
    run()
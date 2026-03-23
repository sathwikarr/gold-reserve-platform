"""
Gold Layer — Merge Geopolitical Scores into Master Panel
Input : data/curated/master_panel.csv
        data/staging/geopolitical_clean.csv
Output: data/curated/master_panel_geo.csv

New columns added:
  un_alignment_score       — how closely country votes with US in UNGA (higher = more aligned)
  un_divergence_score      — inverse of alignment (higher = more divergent)
  sanctions_score          — OFAC sanctions severity (0=none, 1=minor, 2=targeted, 3=comprehensive)
  sanctions_active         — binary flag
  geo_bloc                 — US_allied / neutral / us_divergent
  geo_risk_score           — composite risk score (0-100)
  geo_risk_tier            — low / medium / high / very_high
"""

import pandas as pd
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parents[2]
CURATED_DIR = BASE_DIR / "data" / "curated"
STAGING_DIR = BASE_DIR / "data" / "staging"


def run():
    panel = pd.read_csv(CURATED_DIR / "master_panel.csv")
    geo   = pd.read_csv(STAGING_DIR / "geopolitical_clean.csv")

    print(f"▶ Master panel  : {panel.shape}")
    print(f"▶ Geo scores    : {geo.shape}")

    # ── merge on country_code + year ─────────────────────────────────────────
    merged = panel.merge(
        geo[[
            "country_code", "year",
            "un_alignment_score", "un_divergence_score",
            "sanctions_score", "sanctions_active",
            "geo_bloc", "geo_risk_score", "geo_risk_tier",
        ]],
        on=["country_code", "year"],
        how="left",
    )

    # countries not in geo table get neutral defaults
    merged["un_alignment_score"]  = merged["un_alignment_score"].fillna(50)
    merged["un_divergence_score"] = merged["un_divergence_score"].fillna(50)
    merged["sanctions_score"]     = merged["sanctions_score"].fillna(0).astype(int)
    merged["sanctions_active"]    = merged["sanctions_active"].fillna(0).astype(int)
    merged["geo_bloc"]            = merged["geo_bloc"].fillna("neutral")
    merged["geo_risk_score"]      = merged["geo_risk_score"].fillna(50)
    merged["geo_risk_tier"]       = merged["geo_risk_tier"].fillna("medium")

    print(f"▶ After merge   : {merged.shape}")
    print(f"  Geo coverage  : {merged['un_alignment_score'].notna().sum()} / {len(merged)} rows")

    # ── save ─────────────────────────────────────────────────────────────────
    out_path = CURATED_DIR / "master_panel_geo.csv"
    merged.to_csv(out_path, index=False)

    print(f"\n✅ Saved → {out_path}")
    print(f"   Shape    : {merged.shape}")
    print(f"   Columns  : {len(merged.columns)}")

    # ── analysis 1: geo risk vs accumulation ─────────────────────────────────
    print(f"\n  Accumulation rate by geo risk tier (all years):")
    tier_stats = (
        merged.groupby("geo_risk_tier")
        .agg(
            countries=("country_code", "nunique"),
            avg_accumulation_rate=("is_accumulating", "mean"),
            avg_gold_share=("gold_share_pct", "mean"),
            avg_streak=("accumulation_streak", "mean"),
        )
        .round(3)
        .reset_index()
    )
    print(tier_stats.to_string(index=False))

    # ── analysis 2: sanctioned vs non-sanctioned accumulation ────────────────
    print(f"\n  Sanctioned vs non-sanctioned countries:")
    sanc_stats = (
        merged.groupby("sanctions_active")
        .agg(
            countries=("country_code", "nunique"),
            avg_accumulation_rate=("is_accumulating", "mean"),
            avg_gold_share=("gold_share_pct", "mean"),
            pct_accumulating_during_usd_decline=(
                "accumulating_during_usd_decline", "mean"
            ),
        )
        .round(3)
        .reset_index()
    )
    sanc_stats["sanctions_active"] = sanc_stats["sanctions_active"].map(
        {0: "Not sanctioned", 1: "Sanctioned"}
    )
    print(sanc_stats.to_string(index=False))

    # ── analysis 3: top accumulators with geo context ─────────────────────────
    print(f"\n  Top 15 accumulators (2019-2024) with geo scores:")
    recent = merged[merged["year"] >= 2019]
    summary = (
        recent.groupby(["country", "country_code"])
        .agg(
            total_added_bn=("gold_yoy_change_usd", lambda x: round(x.sum()/1e9, 1)),
            years_buying=("is_accumulating", "sum"),
            geo_risk_score=("geo_risk_score", "mean"),
            un_alignment=("un_alignment_score", "mean"),
            sanctions=("sanctions_score", "mean"),
            geo_bloc=("geo_bloc", "first"),
        )
        .reset_index()
        .sort_values("total_added_bn", ascending=False)
        .head(15)
    )
    summary["geo_risk_score"] = summary["geo_risk_score"].round(1)
    summary["un_alignment"]   = summary["un_alignment"].round(0).astype(int)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    run()
"""
Silver Layer — Clean Geopolitical Data
Inputs : data/raw/ofac_sanctions_YYYYMMDD.csv  (latest)
         data/raw/un_votes_YYYYMMDD.csv         (latest)
Output : data/staging/geopolitical_clean.csv

Steps:
  1. Load both raw files
  2. Merge sanctions + UN alignment on country_code + year
  3. Fill non-sanctioned countries with score 0
  4. Build composite geopolitical risk score
  5. Save
"""

import pandas as pd
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parents[2]
RAW_DIR     = BASE_DIR / "data" / "raw"
STAGING_DIR = BASE_DIR / "data" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)


def load_latest(prefix: str) -> pd.DataFrame:
    files = sorted(RAW_DIR.glob(f"{prefix}_*.csv"))
    if not files:
        raise FileNotFoundError(f"No file matching {prefix}_*.csv in {RAW_DIR}")
    path = files[-1]
    print(f"  ▶ Loading: {path.name}")
    return pd.read_csv(path)


def run():
    sanctions = load_latest("ofac_sanctions")
    un        = load_latest("un_votes")

    print(f"  Sanctions : {sanctions.shape}")
    print(f"  UN votes  : {un.shape}")

    # ── 1. merge on country_code + year ──────────────────────────────────────
    # outer join — keep all countries from both sources
    geo = pd.merge(
        un[["country_code", "year", "un_alignment_score", "geo_bloc"]],
        sanctions[["country_code", "year", "sanctions_score", "sanctions_active"]],
        on=["country_code", "year"],
        how="left",   # keep all UN countries, add sanctions where available
    )

    # fill missing sanctions with 0 (no sanctions)
    geo["sanctions_score"]  = geo["sanctions_score"].fillna(0).astype(int)
    geo["sanctions_active"] = geo["sanctions_active"].fillna(0).astype(int)

    # ── 2. composite geopolitical risk score ─────────────────────────────────
    # Inverts UN alignment so higher = more divergent from US
    # un_divergence: 0 (fully aligned) → 90 (fully divergent)
    geo["un_divergence_score"] = (100 - geo["un_alignment_score"]).round(1)

    # Composite: weighted blend of divergence + sanctions severity
    # sanctions_score is 0-3, scale to 0-30 for comparable weight
    geo["geo_risk_score"] = (
        geo["un_divergence_score"] * 0.6 +
        geo["sanctions_score"] * 10 * 0.4
    ).round(2)

    # geo risk tier
    geo["geo_risk_tier"] = pd.cut(
        geo["geo_risk_score"],
        bins=[0, 25, 45, 65, 100],
        labels=["low", "medium", "high", "very_high"],
        include_lowest=True,
    )

    # ── 3. sort and save ─────────────────────────────────────────────────────
    geo = geo.sort_values(["country_code", "year"]).reset_index(drop=True)

    out_path = STAGING_DIR / "geopolitical_clean.csv"
    geo.to_csv(out_path, index=False)

    print(f"\n  ✅ Saved → {out_path}")
    print(f"     Shape    : {geo.shape}")
    print(f"     Countries: {geo['country_code'].nunique()}")

    # ── 4. preview ───────────────────────────────────────────────────────────
    geo24 = geo[geo["year"] == 2024].copy()

    print(f"\n  Geo risk tier distribution (2024):")
    print(geo24["geo_risk_tier"].value_counts().sort_index().to_string())

    print(f"\n  Highest geo risk countries (2024):")
    top = geo24.nlargest(12, "geo_risk_score")[[
        "country_code", "un_alignment_score",
        "sanctions_score", "geo_risk_score", "geo_risk_tier"
    ]]
    print(top.to_string(index=False))


if __name__ == "__main__":
    run()
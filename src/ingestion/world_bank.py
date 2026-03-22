"""
World Bank Data Ingestion
Pulls two indicators for all countries:
  - FI.RES.TOTL.CD  : Total reserves (includes gold, USD)
  - FI.RES.XGLD.CD  : Total reserves (excludes gold, USD)

Gold value = FI.RES.TOTL.CD - FI.RES.XGLD.CD
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# ── paths ────────────────────────────────────────────────────────────────────
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── config ───────────────────────────────────────────────────────────────────
BASE_URL = "https://api.worldbank.org/v2/country/all/indicator"
INDICATORS = {
    "total_reserves_usd":        "FI.RES.TOTL.CD",
    "total_reserves_excl_gold":  "FI.RES.XGLD.CD",
}
START_YEAR = 2000
END_YEAR   = 2024


def fetch_indicator(name: str, code: str) -> pd.DataFrame:
    """Fetch all pages for a single World Bank indicator."""
    print(f"\n▶ Fetching: {name} ({code})")
    all_records = []
    page = 1

    with tqdm(desc="  pages", unit="pg") as pbar:
        while True:
            params = {
                "format":    "json",
                "date":      f"{START_YEAR}:{END_YEAR}",
                "per_page":  1000,
                "page":      page,
            }
            resp = requests.get(f"{BASE_URL}/{code}", params=params, timeout=30)
            resp.raise_for_status()

            payload = resp.json()
            # World Bank returns [metadata, data]
            if len(payload) < 2 or not payload[1]:
                break

            meta, data = payload
            all_records.extend(data)
            pbar.update(1)

            if page >= meta["pages"]:
                break
            page += 1

    df = pd.DataFrame([{
        "country":      r["country"]["value"],
        "country_code": r["countryiso3code"],
        "year":         int(r["date"]),
        "value":        r["value"],
        "indicator":    name,
    } for r in all_records if r["countryiso3code"]])  # drop blanks

    print(f"  ✓ {len(df):,} rows fetched")
    return df


def run():
    frames = []
    for name, code in INDICATORS.items():
        df = fetch_indicator(name, code)
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)

    # ── save raw ─────────────────────────────────────────────────────────────
    today     = datetime.now().strftime("%Y%m%d")
    out_path  = RAW_DIR / f"world_bank_reserves_{today}.csv"
    raw.to_csv(out_path, index=False)
    print(f"\n✅ Saved → {out_path}")
    print(f"   Shape  : {raw.shape}")
    print(f"   Years  : {raw['year'].min()} – {raw['year'].max()}")
    print(f"   Countries: {raw['country_code'].nunique()}")


if __name__ == "__main__":
    run()
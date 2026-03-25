"""
GDELT News Ingestion — V3 NLP Pipeline
Fetches article headlines from the GDELT Doc API v2 for topics related to:
  - Central bank gold reserves
  - De-dollarization
  - USD dominance / dollar hegemony
  - Gold accumulation and sanctions

No API key required. GDELT is a free, open dataset.
Output: data/raw/gdelt_articles.csv
"""

import requests
import pandas as pd
import time
import logging
from pathlib import Path
from datetime import datetime

# ── paths ────────────────────────────────────────────────────────────────────
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ── GDELT Doc API config ──────────────────────────────────────────────────────
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
MAX_RECORDS = 250  # GDELT hard limit per request

# Search queries — each targets a key narrative in the project thesis
QUERIES = [
    ("gold_reserves",       "central bank gold reserves accumulation"),
    ("dedollarization",     "de-dollarization dollar dominance alternative currency"),
    ("usd_dominance",       "USD share global reserves dollar hegemony decline"),
    ("sanctions_gold",      "sanctions gold reserves dollar alternative SWIFT"),
    ("gold_buying",         "central bank buying gold 2020 2021 2022 2023 2024"),
]

# Year range — focus on 2015-2024 for recency and relevance
YEARS = list(range(2015, 2025))


def fetch_gdelt_articles(query: str, year: int) -> list[dict]:
    """
    Fetch up to MAX_RECORDS article headlines from GDELT Doc API
    for a given query and calendar year.
    """
    start_dt = f"{year}0101000000"
    end_dt   = f"{year}1231235959"

    params = {
        "query":          query,
        "mode":           "artlist",
        "format":         "json",
        "maxrecords":     MAX_RECORDS,
        "startdatetime":  start_dt,
        "enddatetime":    end_dt,
        "sourcelang":     "english",
    }

    try:
        resp = requests.get(GDELT_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        log.info(f"  {query[:40]:<40} {year}  →  {len(articles):>3} articles")
        return articles
    except requests.exceptions.RequestException as e:
        log.warning(f"  Request failed for {query} / {year}: {e}")
        return []
    except Exception as e:
        log.warning(f"  Parse error for {query} / {year}: {e}")
        return []


def build_article_dataframe(articles: list[dict], query_label: str, year: int) -> pd.DataFrame:
    """
    Convert raw GDELT article list to a clean DataFrame row set.
    """
    rows = []
    for art in articles:
        rows.append({
            "query_label":    query_label,
            "year":           year,
            "title":          art.get("title", "").strip(),
            "url":            art.get("url", ""),
            "domain":         art.get("domain", ""),
            "seendate":       art.get("seendate", ""),
            "language":       art.get("language", ""),
            "sourcecountry":  art.get("sourcecountry", ""),
        })
    return pd.DataFrame(rows)


def run():
    """
    Main ingestion loop: query GDELT for each (query, year) combination,
    collect all articles into a single CSV.
    """
    log.info("=" * 60)
    log.info("GDELT Article Ingestion — V3 NLP Pipeline")
    log.info("=" * 60)

    all_frames = []
    total_requests = len(QUERIES) * len(YEARS)
    completed = 0

    for label, query in QUERIES:
        log.info(f"\nQuery: {label}")
        for year in YEARS:
            articles = fetch_gdelt_articles(query, year)
            if articles:
                df = build_article_dataframe(articles, label, year)
                all_frames.append(df)
            # Polite rate limiting — GDELT recommends ~1 req/sec
            time.sleep(1.2)
            completed += 1
            if completed % 10 == 0:
                log.info(f"  Progress: {completed}/{total_requests} requests completed")

    if not all_frames:
        log.error("No articles fetched. Check network connection or GDELT API status.")
        return

    df_all = pd.concat(all_frames, ignore_index=True)

    # Drop rows with empty titles
    df_all = df_all[df_all["title"].str.len() > 5].reset_index(drop=True)

    out_path = RAW_DIR / f"gdelt_articles_{datetime.today().strftime('%Y%m%d')}.csv"
    df_all.to_csv(out_path, index=False)

    log.info(f"\n{'=' * 60}")
    log.info(f"Done. Total articles fetched : {len(df_all):,}")
    log.info(f"Unique titles               : {df_all['title'].nunique():,}")
    log.info(f"Years covered               : {df_all['year'].min()} – {df_all['year'].max()}")
    log.info(f"Saved → {out_path}")


if __name__ == "__main__":
    run()

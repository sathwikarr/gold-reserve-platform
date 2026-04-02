#!/usr/bin/env python3
"""
Gold Reserve Platform — Live Data Refresh
==========================================
Pulls fresh data from all automated sources, checks WGC file staleness,
then re-runs the full analytics pipeline.

Automated sources (no manual step needed):
  - World Bank API   : total reserves, GDP (all countries, 2000–present)
  - IMF COFER        : USD share of global reserves (World Bank API proxy)
  - UN Votes         : Harvard Dataverse (auto-fetched)
  - OFAC Sanctions   : US Treasury consolidated list (auto-fetched)
  - GDELT            : Financial news articles (auto-fetched)

Manual sources (download required — see instructions below):
  - World Gold Council / IMF IFS : gold tonnes by country
    URL: https://www.gold.org/goldhub/data/gold-reserves-by-country
    Download: "World Official Gold Holdings" Excel (.xlsx)
    Save to:  data/raw/  (script detects latest file automatically)

Usage:
  python scripts/refresh_data.py            # full refresh + pipeline
  python scripts/refresh_data.py --check    # staleness check only, no fetch
  python scripts/refresh_data.py --no-pipeline  # fetch only, skip pipeline
"""

import sys
import argparse
import subprocess
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import json
import io

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parents[1]
RAW     = ROOT / "data" / "raw"
STAGING = ROOT / "data" / "staging"
CURATED = ROOT / "data" / "curated"
META    = ROOT / "data" / ".refresh_meta.json"

RAW.mkdir(parents=True, exist_ok=True)

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):    print(f"  {GREEN}✓{RESET}  {msg}")
def warn(msg):  print(f"  {YELLOW}⚠{RESET}  {msg}")
def err(msg):   print(f"  {RED}✗{RESET}  {msg}")
def info(msg):  print(f"  {CYAN}→{RESET}  {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}\n{'─'*60}")


# ══════════════════════════════════════════════════════════════════
# METADATA — track last fetch timestamps per source
# ══════════════════════════════════════════════════════════════════

def load_meta() -> dict:
    if META.exists():
        return json.loads(META.read_text())
    return {}

def save_meta(meta: dict):
    META.write_text(json.dumps(meta, indent=2, default=str))

def days_since(iso_ts: str | None) -> float:
    """Days since a timestamp string (or infinity if None)."""
    if not iso_ts:
        return float("inf")
    dt = datetime.fromisoformat(iso_ts)
    return (datetime.now() - dt).total_seconds() / 86400


# ══════════════════════════════════════════════════════════════════
# STALENESS CHECK
# ══════════════════════════════════════════════════════════════════

STALE_DAYS = {
    "world_bank":   30,   # World Bank API: quarterly updates
    "un_votes":     90,   # UN votes: annual session
    "ofac":         7,    # OFAC: can change any time
    "gdelt":        1,    # GDELT: daily news
    "wgc":          30,   # WGC: monthly IFS release
}

def check_staleness(meta: dict) -> dict[str, bool]:
    """Return dict of source → is_stale (True = needs refresh)."""
    header("STALENESS CHECK")
    results = {}
    for source, threshold in STALE_DAYS.items():
        ts = meta.get(f"{source}_last_fetched")
        age = days_since(ts)
        stale = age > threshold
        results[source] = stale

        if ts is None:
            warn(f"{source:<15} never fetched")
        elif stale:
            warn(f"{source:<15} {age:.0f} days old  (threshold: {threshold}d)  → STALE")
        else:
            ok(f"{source:<15} {age:.0f} days old  (threshold: {threshold}d)  → fresh")

    # WGC: check file presence regardless of timestamp
    wgc_files = sorted(RAW.glob("World_official_gold_holdings*.xlsx"))
    if not wgc_files:
        err("wgc               no Excel file found in data/raw/")
        print()
        print(f"  {YELLOW}Download the latest WGC file:{RESET}")
        print(f"  https://www.gold.org/goldhub/data/gold-reserves-by-country")
        print(f"  Save as: data/raw/World_official_gold_holdings_as_of_MMMYYYY_IFS.xlsx")
        results["wgc"] = True
    else:
        latest = wgc_files[-1]
        mtime_days = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days
        if mtime_days > STALE_DAYS["wgc"]:
            warn(f"wgc               file {latest.name} is {mtime_days} days old — check for newer IFS release")
        else:
            ok(f"wgc               {latest.name}  ({mtime_days} days old)")

    return results


# ══════════════════════════════════════════════════════════════════
# WORLD BANK — total reserves + GDP
# ══════════════════════════════════════════════════════════════════

WB_INDICATORS = {
    "total_reserves_usd":       "FI.RES.TOTL.CD",
    "total_reserves_excl_gold": "FI.RES.XGLD.CD",
}

def fetch_world_bank(start_year=2000) -> bool:
    """Pull World Bank reserves data via API. Returns True on success."""
    header("WORLD BANK RESERVES")
    end_year = datetime.now().year
    base = "https://api.worldbank.org/v2/country/all/indicator"
    all_dfs = []

    for label, code in WB_INDICATORS.items():
        info(f"Fetching {label} ({code}) ...")
        records, page = [], 1
        try:
            while True:
                params = {
                    "format": "json",
                    "date":   f"{start_year}:{end_year}",
                    "per_page": 1000,
                    "page":   page,
                }
                resp = requests.get(f"{base}/{code}", params=params, timeout=30)
                resp.raise_for_status()
                payload = resp.json()
                if len(payload) < 2 or not payload[1]:
                    break
                meta_pg, data = payload
                for row in data:
                    if row.get("value") is not None:
                        records.append({
                            "country":      row["country"]["value"],
                            "country_code": row["countryiso3code"],
                            "year":         int(row["date"]),
                            label:          float(row["value"]),
                        })
                if page >= meta_pg["pages"]:
                    break
                page += 1

            df = pd.DataFrame(records)
            all_dfs.append(df.set_index(["country", "country_code", "year"]))
            ok(f"{label}: {len(records):,} records")

        except Exception as e:
            err(f"Failed to fetch {label}: {e}")
            return False

    if not all_dfs:
        return False

    combined = pd.concat(all_dfs, axis=1).reset_index()
    ts = datetime.now().strftime("%Y%m%d")
    out = RAW / f"world_bank_reserves_{ts}.csv"
    combined.to_csv(out, index=False)
    ok(f"Saved → {out.name}  ({len(combined):,} rows)")
    return True


# ══════════════════════════════════════════════════════════════════
# IMF COFER via World Bank proxy
# ══════════════════════════════════════════════════════════════════

def fetch_imf_cofer() -> bool:
    """
    Fetch USD share of global reserves from World Bank (IMF COFER proxy).
    Indicator: RAXG.FXRS.TOTL.ZS  — share of USD in allocated reserves.
    Falls back to our curated hardcoded series if the API doesn't have latest.
    """
    header("IMF COFER — USD SHARE OF RESERVES")

    # IMF Data API (COFER) — direct JSON endpoint
    COFER_URL = "https://data.imf.org/api/v2/data/COFER/Q.USD.TOTAL_RESERVES"

    try:
        info("Querying IMF Data API for COFER series ...")
        resp = requests.get(COFER_URL, timeout=20)
        # IMF API may return 404 or different schema — handle gracefully
        if resp.status_code == 200:
            try:
                payload = resp.json()
                # If we get a valid response, parse it
                # (IMF API structure varies — fall through to WB if format unexpected)
                ok("IMF COFER API responded")
            except Exception:
                pass
    except Exception:
        pass

    # World Bank proxy: FX reserves USD share (closest public proxy)
    info("Fetching World Bank USD reserve share proxy ...")
    try:
        url = "https://api.worldbank.org/v2/country/1W/indicator/RAXG.FXRS.TOTL.ZS"
        params = {"format": "json", "date": "2000:2025", "per_page": 100}
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()

        if len(payload) == 2 and payload[1]:
            records = [
                {"year": int(r["date"]), "usd_share_pct": float(r["value"])}
                for r in payload[1]
                if r.get("value") is not None
            ]
            if records:
                df = pd.DataFrame(records).sort_values("year")
                ts = datetime.now().strftime("%Y%m%d")
                out = RAW / f"usd_dominance_{ts}.csv"
                df.to_csv(out, index=False)
                ok(f"USD share series: {len(df)} years ({df['year'].min()}–{df['year'].max()})")
                ok(f"Saved → {out.name}")
                return True
    except Exception as e:
        warn(f"World Bank USD proxy failed: {e}")

    # Fallback: the hardcoded COFER series in imf_cofer.py is authoritative
    info("Using curated IMF COFER series (hardcoded in src/ingestion/imf_cofer.py)")
    info("Update the COFER_USD_SHARE dict when Q4 data is published at:")
    info("  https://data.imf.org/regular.aspx?key=41175")
    return True  # not a blocking failure


# ══════════════════════════════════════════════════════════════════
# UN VOTES — Harvard Dataverse
# ══════════════════════════════════════════════════════════════════

UN_VOTES_URL = (
    "https://dataverse.harvard.edu/api/access/datafile/6358048"
)

def fetch_un_votes() -> bool:
    """Download UN General Assembly voting dataset (Voeten et al.)."""
    header("UN GENERAL ASSEMBLY VOTES")
    ts = datetime.now().strftime("%Y%m%d")
    out = RAW / f"un_votes_{ts}.csv"

    # Check if we already have a recent file
    existing = sorted(RAW.glob("un_votes_*.csv"))
    if existing:
        latest = existing[-1]
        age_days = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days
        if age_days < STALE_DAYS["un_votes"]:
            ok(f"Using existing {latest.name} ({age_days} days old — within {STALE_DAYS['un_votes']}d threshold)")
            return True

    info("Downloading UN votes dataset from Harvard Dataverse ...")
    try:
        resp = requests.get(UN_VOTES_URL, timeout=60, stream=True)
        resp.raise_for_status()

        # Dataset may be tab-separated (Stata export) — try to parse
        content = resp.content
        try:
            df = pd.read_csv(io.BytesIO(content), sep="\t", low_memory=False)
        except Exception:
            df = pd.read_csv(io.BytesIO(content), low_memory=False)

        df.to_csv(out, index=False)
        ok(f"Downloaded: {len(df):,} voting records → {out.name}")
        return True

    except Exception as e:
        warn(f"Harvard Dataverse fetch failed: {e}")
        warn("UN votes data unchanged — using existing files in data/raw/")
        # Not a blocking failure if we already have historical data
        return bool(existing)


# ══════════════════════════════════════════════════════════════════
# OFAC SANCTIONS — US Treasury
# ══════════════════════════════════════════════════════════════════

OFAC_URL = "https://www.treasury.gov/ofac/downloads/consolidated/cons_prim.csv"

def fetch_ofac() -> bool:
    """Download OFAC consolidated sanctions list."""
    header("OFAC SANCTIONS LIST")
    ts = datetime.now().strftime("%Y%m%d")
    out = RAW / f"ofac_sanctions_{ts}.csv"

    info("Downloading OFAC consolidated sanctions list ...")
    try:
        resp = requests.get(OFAC_URL, timeout=30)
        resp.raise_for_status()

        # OFAC CSV has no standard header — detect encoding
        try:
            df = pd.read_csv(io.BytesIO(resp.content), encoding="latin-1", low_memory=False)
        except Exception:
            df = pd.read_csv(io.BytesIO(resp.content), low_memory=False)

        df.to_csv(out, index=False)
        ok(f"Downloaded: {len(df):,} entries → {out.name}")
        return True

    except Exception as e:
        warn(f"OFAC download failed: {e}")
        warn("Sanctions scoring will use existing curated data in src/ingestion/geopolitical.py")
        return True  # curated fallback is fine


# ══════════════════════════════════════════════════════════════════
# GDELT — Financial news articles
# ══════════════════════════════════════════════════════════════════

GDELT_THEMES = ["GOLD", "ECON_DEBTRESTRUCTURE", "ECON_RESERVES", "SANCTION"]
GDELT_API    = "https://api.gdeltproject.org/api/v2/doc/doc"

def fetch_gdelt(max_articles=500) -> bool:
    """
    Fetch recent financial articles mentioning gold/reserves/sanctions
    using the GDELT DOC 2.0 API.
    """
    header("GDELT NEWS ARTICLES")
    ts  = datetime.now().strftime("%Y%m%d")
    out = RAW / f"gdelt_articles_{ts}.csv"

    # GDELT DOC API query
    query_terms = [
        '"gold reserves"',
        '"central bank gold"',
        '"de-dollarization"',
        '"dollar dominance"',
        '"gold accumulation"',
        '"reserve currency"',
    ]
    query = " OR ".join(query_terms)

    info(f"Querying GDELT DOC 2.0 API (last 7 days) ...")

    try:
        params = {
            "query":    query,
            "mode":     "artlist",
            "maxrecords": max_articles,
            "format":   "json",
            "timespan": "7d",
            "sort":     "DateDesc",
        }
        resp = requests.get(GDELT_API, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        articles = data.get("articles", [])
        if not articles:
            warn("No articles returned from GDELT API")
            return True

        rows = []
        for a in articles:
            rows.append({
                "url":         a.get("url", ""),
                "title":       a.get("title", ""),
                "seendate":    a.get("seendate", ""),
                "source":      a.get("domain", ""),
                "language":    a.get("language", ""),
                "tone":        a.get("tone", None),
            })

        df = pd.DataFrame(rows)
        df["fetched_at"] = datetime.now().isoformat()
        df.to_csv(out, index=False)
        ok(f"Fetched: {len(df):,} articles → {out.name}")
        return True

    except Exception as e:
        warn(f"GDELT fetch failed: {e}")
        warn("Sentiment feed will use existing GDELT data in data/raw/")
        return True  # non-blocking


# ══════════════════════════════════════════════════════════════════
# WGC FILE CHECK
# ══════════════════════════════════════════════════════════════════

def check_wgc() -> bool:
    """Check WGC file presence and freshness. Print instructions if stale."""
    header("WORLD GOLD COUNCIL (WGC) — MANUAL STEP")
    wgc_files = sorted(RAW.glob("World_official_gold_holdings*.xlsx"))

    if not wgc_files:
        err("No WGC Excel file found in data/raw/")
        print()
        print(f"  {YELLOW}Action required:{RESET}")
        print(f"  1. Go to: https://www.gold.org/goldhub/data/gold-reserves-by-country")
        print(f"  2. Download: 'World Official Gold Holdings' Excel (.xlsx)")
        print(f"  3. Save to: data/raw/  (keep the original filename)")
        print(f"  4. Re-run: python scripts/refresh_data.py")
        return False

    latest = wgc_files[-1]
    mtime  = datetime.fromtimestamp(latest.stat().st_mtime)
    age_days = (datetime.now() - mtime).days
    ok(f"Found: {latest.name}")

    # WGC publishes a new IFS file around the 5th of each month
    current_month = datetime.now().strftime("%b%Y")
    if age_days > 35:
        warn(f"File is {age_days} days old — a newer IFS release may be available")
        print()
        print(f"  {YELLOW}Check for updates at:{RESET}")
        print(f"  https://www.gold.org/goldhub/data/gold-reserves-by-country")
        print(f"  Expected filename: World_official_gold_holdings_as_of_{current_month}_IFS.xlsx")
    else:
        ok(f"File age: {age_days} days — looks current")

    return True


# ══════════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ══════════════════════════════════════════════════════════════════

def run_pipeline() -> bool:
    """Re-run the full analytics pipeline after data refresh."""
    header("RUNNING ANALYTICS PIPELINE")
    info("Executing: python run_pipeline.py")
    print()

    result = subprocess.run(
        [sys.executable, str(ROOT / "run_pipeline.py")],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        err(f"Pipeline failed (exit code {result.returncode})")
        return False

    ok("Pipeline completed successfully")
    return True


# ══════════════════════════════════════════════════════════════════
# SUMMARY REPORT
# ══════════════════════════════════════════════════════════════════

def print_summary(meta: dict):
    header("REFRESH SUMMARY")
    now = datetime.now()

    panel_path = CURATED / "master_panel_nlp.csv"
    scores_path = CURATED / "ml_country_scores.csv"

    if panel_path.exists():
        panel = pd.read_csv(panel_path)
        ok(f"Master panel:   {panel.shape[0]:,} rows × {panel.shape[1]} cols")
        ok(f"Countries:      {panel['country'].nunique()}")
        ok(f"Years:          {int(panel['year'].min())}–{int(panel['year'].max())}")

    if scores_path.exists():
        scores = pd.read_csv(scores_path)
        predict_year = int(panel["year"].max()) + 1 if panel_path.exists() else "?"
        ok(f"Countries scored: {len(scores)} (predict: {predict_year})")
        print()
        print(f"  {BOLD}Top 5 predicted gold accumulators:{RESET}")
        for i, row in scores.head(5).iterrows():
            print(f"    {i+1}. {row['country']:<30} score={row['gold_accumulation_score']:.1f}")

    print()
    ok(f"Refresh completed at {now.strftime('%Y-%m-%d %H:%M')}")
    info("Next step: git add data/raw/ && git commit -m 'Data refresh YYYY-MM-DD' && git push")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Gold Reserve Platform — Data Refresh")
    parser.add_argument("--check",       action="store_true", help="Staleness check only, no fetching")
    parser.add_argument("--no-pipeline", action="store_true", help="Fetch data but skip pipeline re-run")
    parser.add_argument("--source",      type=str,            help="Refresh only one source: wb | cofer | un | ofac | gdelt")
    args = parser.parse_args()

    print(f"\n{BOLD}{'='*60}")
    print(f"  GOLD RESERVE PLATFORM — DATA REFRESH")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}{RESET}")

    meta = load_meta()

    # ── Staleness check ───────────────────────────────────────────
    staleness = check_staleness(meta)

    if args.check:
        print(f"\n{CYAN}--check mode: no data fetched.{RESET}")
        sys.exit(0)

    # ── Selective source ──────────────────────────────────────────
    if args.source:
        source_map = {
            "wb":    fetch_world_bank,
            "cofer": fetch_imf_cofer,
            "un":    fetch_un_votes,
            "ofac":  fetch_ofac,
            "gdelt": fetch_gdelt,
        }
        fn = source_map.get(args.source)
        if not fn:
            err(f"Unknown source: {args.source}. Choose: {list(source_map)}")
            sys.exit(1)
        success = fn()
        if success:
            meta[f"{args.source}_last_fetched"] = datetime.now().isoformat()
            save_meta(meta)
        sys.exit(0 if success else 1)

    # ── Full refresh ──────────────────────────────────────────────
    results = {}

    results["world_bank"] = fetch_world_bank()
    if results["world_bank"]:
        meta["world_bank_last_fetched"] = datetime.now().isoformat()

    results["cofer"] = fetch_imf_cofer()
    if results["cofer"]:
        meta["cofer_last_fetched"] = datetime.now().isoformat()

    results["un"] = fetch_un_votes()
    if results["un"]:
        meta["un_votes_last_fetched"] = datetime.now().isoformat()

    results["ofac"] = fetch_ofac()
    if results["ofac"]:
        meta["ofac_last_fetched"] = datetime.now().isoformat()

    results["gdelt"] = fetch_gdelt()
    if results["gdelt"]:
        meta["gdelt_last_fetched"] = datetime.now().isoformat()

    wgc_ok = check_wgc()
    results["wgc"] = wgc_ok

    save_meta(meta)

    # ── Pipeline ──────────────────────────────────────────────────
    if not args.no_pipeline:
        if not wgc_ok:
            warn("Skipping pipeline — WGC file missing (required for gold tonnes data)")
            warn("Add the WGC Excel file to data/raw/ then re-run with: python scripts/refresh_data.py")
            sys.exit(1)

        pipeline_ok = run_pipeline()
        if not pipeline_ok:
            sys.exit(1)

    # ── Summary ───────────────────────────────────────────────────
    print_summary(meta)

    # Exit non-zero if any critical source failed
    critical = ["world_bank"]
    if any(not results.get(s) for s in critical):
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
NLP Panel Merger — V3 NLP Pipeline
Merges NLP features into the existing master_panel_geo (v2b output)
to produce the final enriched panel with all layers:
  - Gold reserves & features       (v1)
  - USD dominance context          (v2a)
  - Geopolitical scores            (v2b)
  - NLP sentiment signals          (v3)  ← new

NLP features are left-joined on (country_code, year).
Countries / years with no NLP coverage keep NaN values.
NLP data only covers 2015-2024, so pre-2015 rows will have NaN NLP columns.

Input:  data/curated/master_panel_geo.csv
        data/curated/nlp_features.csv
        data/curated/nlp_global_usd_sentiment.csv  (optional)
Output: data/curated/master_panel_nlp.csv
"""

import pandas as pd
import logging
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
CURATED_DIR = Path(__file__).resolve().parents[2] / "data" / "curated"

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


def run():
    log.info("=" * 60)
    log.info("NLP Panel Merger — V3 NLP Pipeline")
    log.info("=" * 60)

    # ── Load master panel (geo layer, v2b output) ─────────────────────────────
    geo_path = CURATED_DIR / "master_panel_geo.csv"
    if not geo_path.exists():
        raise FileNotFoundError(f"master_panel_geo.csv not found: {geo_path}")
    panel = pd.read_csv(geo_path)
    log.info(f"master_panel_geo loaded : {panel.shape}")

    # ── Load NLP country-year features ────────────────────────────────────────
    nlp_path = CURATED_DIR / "nlp_features.csv"
    if not nlp_path.exists():
        raise FileNotFoundError(f"nlp_features.csv not found: {nlp_path}\nRun build_nlp_features.py first.")
    nlp = pd.read_csv(nlp_path)
    log.info(f"NLP features loaded     : {nlp.shape}")

    # ── Merge NLP → panel on (country_code, year) ─────────────────────────────
    panel = panel.merge(nlp, on=["country_code", "year"], how="left")
    log.info(f"After NLP merge         : {panel.shape}")

    # ── Optionally merge global USD sentiment by year ─────────────────────────
    global_path = CURATED_DIR / "nlp_global_usd_sentiment.csv"
    if global_path.exists():
        global_usd = pd.read_csv(global_path)
        panel = panel.merge(global_usd, on="year", how="left")
        log.info(f"After global USD merge  : {panel.shape}")
    else:
        log.info("No global USD sentiment file found — skipping that merge.")

    # ── NLP coverage report ───────────────────────────────────────────────────
    nlp_cols = [c for c in panel.columns if c.startswith("nlp_")]
    coverage = panel[nlp_cols[0]].notna().sum() if nlp_cols else 0
    total    = len(panel)
    log.info(f"\nNLP coverage: {coverage:,} / {total:,} rows ({coverage/total*100:.1f}%)")
    log.info("(NLP only covers 2015–2024; pre-2015 rows will have NaN NLP columns)")

    # ── NLP signal preview ────────────────────────────────────────────────────
    if "nlp_composite_signal" in panel.columns:
        top_signals = (
            panel.dropna(subset=["nlp_composite_signal"])
            .nlargest(10, "nlp_composite_signal")
            [["country", "country_code", "year", "nlp_composite_signal",
              "nlp_gold_positive", "nlp_usd_negative", "sanctions_score", "geo_risk_tier"]]
        )
        log.info(f"\nTop 10 rows by NLP composite signal:\n{top_signals.to_string(index=False)}")

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = CURATED_DIR / "master_panel_nlp.csv"
    panel.to_csv(out_path, index=False)

    log.info(f"\nDone.")
    log.info(f"Saved → {out_path}")
    log.info(f"Shape    : {panel.shape}")
    log.info(f"Columns  : {panel.columns.tolist()}")


if __name__ == "__main__":
    run()

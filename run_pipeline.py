#!/usr/bin/env python3
"""
Gold Reserve Platform — Full Pipeline Runner
==============================================
Run this after fetching new data (e.g., 2025 World Bank + IMF COFER update).

Steps:
  1. Data Cleaning     → data/staging/
  2. Feature Engineering → data/curated/master_panel.csv
  3. Geo Features       → data/curated/master_panel_geo.csv
  4. NLP Features       → data/curated/master_panel_nlp.csv
  5. ML Feature Prep    → data/curated/ml_features.csv
  6. ML Training        → models + evaluation charts
  7. ML Scoring         → data/curated/ml_country_scores.csv
  8. ML Predictions     → data/curated/ml_top10_predictions.csv

Usage:
  python run_pipeline.py
"""

import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).parent

STEPS = [
    ("1/8 — Cleaning reserves",          "src/cleaning/clean_reserves.py"),
    ("2/8 — Cleaning USD dominance",      "src/cleaning/clean_usd_dominance.py"),
    ("3/8 — Cleaning geopolitical",       "src/cleaning/clean_geopolitical.py"),
    ("4/8 — Building features",           "src/features/build_features.py"),
    ("5/8 — Building geo features",       "src/features/build_geo_features.py"),
    ("6/8 — Building master panel",       "src/features/build_master_panel.py"),
    ("7/8 — Merging NLP features",        "src/nlp/merge_nlp_panel.py"),
    ("8/8 — ML: prepare → train → score", None),  # composite step
]

ML_STEPS = [
    "src/ml/prepare_features.py",
    "src/ml/train_model.py",
    "src/ml/score_countries.py",
    "src/ml/predict.py",
]


def run_step(label: str, script: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  → {script}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, str(BASE / script)],
        cwd=str(BASE),
    )
    if result.returncode != 0:
        print(f"\n❌ FAILED: {script} (exit code {result.returncode})")
        sys.exit(1)
    print(f"✅ Done: {label}")


def main():
    print("=" * 60)
    print("  GOLD RESERVE PLATFORM — FULL PIPELINE")
    print("=" * 60)

    # Steps 1–7
    for label, script in STEPS:
        if script is not None:
            run_step(label, script)

    # Step 8: ML pipeline (4 sub-steps)
    for i, script in enumerate(ML_STEPS, 1):
        run_step(f"8.{i}/4 — ML: {Path(script).stem}", script)

    print("\n" + "=" * 60)
    print("  ✅ FULL PIPELINE COMPLETE!")
    print("=" * 60)

    # Show summary
    import pandas as pd
    curated = BASE / "data" / "curated"

    panel = pd.read_csv(curated / "master_panel_nlp.csv")
    print(f"\n  Panel: {panel.shape[0]:,} rows × {panel.shape[1]} cols")
    print(f"  Years: {int(panel['year'].min())}–{int(panel['year'].max())}")
    print(f"  Countries: {panel['country'].nunique()}")

    if (curated / "ml_country_scores.csv").exists():
        scores = pd.read_csv(curated / "ml_country_scores.csv")
        predict_year = int(panel["year"].max()) + 1
        print(f"\n  Predictions for: {predict_year}")
        print(f"  Countries scored: {len(scores)}")
        print(f"  Top 5:")
        for i, row in scores.head(5).iterrows():
            print(f"    {i+1}. {row['country']:<30} score={row['gold_accumulation_score']:.1f}")

    print(f"\n  Next: commit + push, then update dashboard/app if needed")


if __name__ == "__main__":
    main()

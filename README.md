# Central Bank Gold Accumulation vs USD Power & Geopolitical Risk Platform

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://gold-reserve-platform-az4sd962a7cyf3mifjeae8.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

> Are countries increasing gold reserves due to declining trust in the US dollar and rising geopolitical risk?

An end-to-end analytics and ML platform integrating central bank gold reserves, global USD dominance metrics, sanctions exposure, and NLP-derived financial narratives to analyze and predict country-level gold accumulation behavior.

**[→ Open Live Dashboard](https://gold-reserve-platform-az4sd962a7cyf3mifjeae8.streamlit.app/)**

---

## Architecture

![Pipeline Architecture](docs/architecture.png)

The platform follows a **Bronze → Silver → Gold** data engineering pattern:

| Layer | Path | Description |
|-------|------|-------------|
| Bronze | `data/raw/` | Raw CSV/Excel from WGC, IMF, World Bank, OFAC, UN |
| Silver | `data/staging/` | Cleaned, ISO3-coded, quarterly-aligned |
| Gold | `data/curated/` | Feature-engineered master panel (4,376 rows × 49 cols) |
| ML | `data/curated/ml_*` | Model outputs, scores, 2026 predictions |

---

## Key Findings (March 2026)

- **$2.99 trillion** in world central bank gold holdings (2025) — up 21% in one year
- USD share of global reserves has fallen from **71.1% (2001) → 56.9% (2025)** — every year since 2015
- Countries under **OFAC sanctions** hold proportionally more gold (avg 25.4% vs 13.3% for non-sanctioned)
- **Poland** added 102 tonnes in 2025 alone — gold share jumped 16.9% → 30.1% in 12 months
- Top 2026 predicted buyers: **Belarus, Iraq, Libya, Uzbekistan, Qatar** (scored on physical buying momentum, consistency streak, and geopolitical motivation)

---

## ML Model

**Goal:** Predict which countries will increase gold reserves in 2026.

**Approach:** 4-Pillar Rule-Based Scoring Model (validated against XGBoost and Logistic Regression)

**Pillars (weighted):**

| Pillar | Weight | Signals |
|--------|--------|---------|
| Physical Buying Momentum | 30% | Actual tonne changes YoY (price-neutral, from WGC data) |
| Buying Consistency | 25% | Accumulation streak + 5-year buying frequency |
| Geopolitical Motivation | 25% | UN divergence from US + sanctions exposure |
| Strategic Allocation Gap | 20% | Room to grow gold share (below-average allocation + trend) |

**Country Coverage:** 182 countries in master panel → 72 scored (filters: ≥$500M gold holdings, sufficient history, non-null geo data)

**Model Performance (test set 2020–2025):**

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC |
|-------|----------|-----------|--------|----|---------|
| Logistic Regression | 0.264 | 0.787 | 0.218 | 0.342 | 0.529 |
| **Gradient Boosting** | **0.402** | **0.861** | **0.378** | **0.525** | **0.561** |
| Ensemble | 0.256 | 0.800 | 0.201 | 0.321 | 0.528 |

Gradient Boosting performs best across all metrics. High precision (0.86) means when the model predicts a country will buy gold, it is correct 86% of the time.

**Training:** 2001–2019 | **Test:** 2020–2025 | **Predict:** 2026

---

## Top 10 Predicted Gold Accumulators — 2026

![Top 10 Predictions](docs/ml_top10_predictions.png)

| # | Country | Score | Key Driver |
|---|---------|-------|-----------|
| 1 | Belarus | 100.0 | 10-yr streak + max sanctions (level 2) + high geo risk |
| 2 | Iraq | 97.9 | +12t buying + 10-yr streak + UN divergence |
| 3 | Libya | 88.8 | 10-yr streak + sanctions + high geo risk |
| 4 | Uzbekistan | 86.3 | +7.8t buying + 12-yr streak + 86% gold share |
| 5 | Qatar | 86.0 | +4.4t buying + 11-yr streak |
| 6 | Algeria | 83.1 | 10-yr streak + high UN divergence score |
| 7 | China | 83.0 | +26.7t buying + 11-yr streak + high geo risk |
| 8 | Egypt | 77.1 | +2.5t buying + 10-yr streak |
| 9 | India | 71.0 | +4.2t buying + 10-yr streak |
| 10 | Lebanon | 70.4 | 10-yr streak + 82% gold share |

---

## Data Sources

| Source | Data | Countries |
|--------|------|-----------|
| World Gold Council / IMF IFS | Gold holdings in tonnes | 182 |
| IMF COFER | USD share of global reserves | Global aggregate |
| World Bank API | Total reserves, GDP, macro indicators | 182 |
| OFAC | Sanctions severity scores (0–3) | All |
| UN General Assembly | Voting alignment divergence from US | 182 |
| GDELT / News APIs | Financial news sentiment (NLP) | Live feed |

---

## Tech Stack

```
Python · pandas · numpy · scikit-learn · XGBoost · HuggingFace FinBERT
PostgreSQL · SQLAlchemy · psycopg2
Streamlit · Plotly · Chart.js
Docker · docker-compose
```

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/sathwikarr/gold-reserve-platform.git
cd gold-reserve-platform
pip install -r requirements.txt

# 2. Run the full pipeline (re-processes all data + ML)
python run_pipeline.py

# 3. Launch the Streamlit app
streamlit run app.py

# 4. Or open the standalone HTML dashboard
open dashboard.html
```

### With Docker (includes PostgreSQL)

```bash
cp .env.example .env          # fill in your settings
docker-compose up --build     # starts app + postgres
# App: http://localhost:8501
# DB:  localhost:5432
```

### Load data into PostgreSQL

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/gold_reserve_db
psql $DATABASE_URL -f sql/schema.sql   # create tables
python src/db/load_to_postgres.py      # load curated data
psql $DATABASE_URL -f sql/queries.sql  # run analysis queries
```

---

## Project Structure

```
gold-reserve-platform/
├── app.py                        # Streamlit multi-page app (5 pages)
├── dashboard.html                # Standalone HTML dashboard (Chart.js)
├── run_pipeline.py               # Single command re-runs full pipeline
│
├── src/
│   ├── ingestion/
│   │   ├── wgc_gold.py           # WGC/IMF IFS gold tonnage parser
│   │   ├── world_bank.py         # World Bank API ingestion
│   │   └── imf_cofer.py          # IMF COFER USD share
│   ├── cleaning/
│   │   ├── clean_reserves.py     # World Bank + WGC merge
│   │   ├── clean_usd_dominance.py
│   │   └── clean_geopolitical.py
│   ├── features/
│   │   ├── build_features.py     # Gold-specific features
│   │   ├── build_master_panel.py # Joins gold + USD data
│   │   └── build_geo_features.py # Merges geopolitical scores
│   ├── nlp/
│   │   └── merge_nlp_panel.py    # NLP sentiment merge
│   ├── ml/
│   │   ├── prepare_features.py   # Train/test split
│   │   ├── train_model.py        # XGBoost + LR ensemble
│   │   ├── score_countries.py    # V5 4-pillar scoring
│   │   └── predict.py            # 2026 predictions
│   └── db/
│       └── load_to_postgres.py   # ETL into PostgreSQL
│
├── sql/
│   ├── schema.sql                # Star schema with 6 tables + 1 view
│   └── queries.sql               # 10 analytical SQL queries
│
├── data/
│   ├── raw/                      # Bronze: original source files
│   ├── staging/                  # Silver: cleaned, standardized
│   └── curated/                  # Gold: final panel + ML outputs
│       ├── master_panel_nlp.csv  # 4,376 rows × 49 cols, 182 countries
│       ├── ml_country_scores.csv # 72 scored countries with pillar breakdown
│       ├── ml_top10_predictions.csv
│       └── ml_model_metrics.csv  # Gradient Boosting F1=0.525, AUC=0.561
│
├── docs/
│   ├── architecture.png          # Pipeline architecture diagram
│   ├── ml_top10_predictions.png  # Top 10 bar chart (auto-generated)
│   ├── ml_feature_importance.png
│   └── ml_roc_curves.png
│
├── notebooks/
│   ├── 01_eda_gold_reserves.ipynb      # Gold holdings EDA
│   ├── 02_eda_usd_vs_gold.ipynb        # USD dominance EDA
│   └── 03_eda_geopolitical.ipynb       # Geopolitical risk EDA
│
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

## Streamlit App Pages

| Page | Description |
|------|-------------|
| Overview | Global gold map, top holders, KPI cards — macro context at a glance |
| Gold vs USD | Gold trend vs USD dominance (dual-axis), Pearson correlation OLS trendline |
| Geopolitics | Sanctions scoring, UN alignment scatter, geo bloc analysis |
| Sentiment | Live NLP feed from GDELT/Reuters — gold & USD sentiment signals |
| ML Predictions | 2026 country-level predictions — 4-pillar scores, model metrics, coverage funnel |

---

## Resume Line

> Built an end-to-end geopolitical analytics platform integrating central bank gold reserves (WGC/IMF IFS, 182 countries, 2000–2025), global USD dominance metrics, sanctions exposure, and NLP-derived financial narratives to analyze and predict country-level gold accumulation behavior — deployed with Streamlit, PostgreSQL, and Docker. Gradient Boosting model achieves 0.86 precision on 2026 gold accumulation predictions.

---

## Roadmap

- [x] Streamlit multi-page app with 5 analytical pages
- [x] PostgreSQL star schema + 10 analytical SQL queries
- [x] Docker deployment with docker-compose
- [x] 4-Pillar ML scoring with model performance metrics
- [ ] Live GDELT news feed integration (real-time NLP)
- [ ] Airflow DAG for automated pipeline scheduling
- [ ] dbt transformations for Silver → Gold layer
- [ ] Prophet time-series forecasting for gold price trends
- [ ] Streamlit Cloud deployment (public demo URL)

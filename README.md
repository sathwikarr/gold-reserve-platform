# Central Bank Gold Accumulation vs USD Power & Geopolitical Risk

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://gold-reserve-platform-az4sd962a7cyf3mifjeae8.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

An end-to-end analytics and ML platform that tracks central bank gold accumulation, measures USD dominance, quantifies geopolitical risk, and predicts which countries are likely to increase gold reserves next — combining structured macroeconomic data with NLP-derived financial narratives across 182 countries from 2000 to 2025.

**[→ Open Live Dashboard](https://gold-reserve-platform-az4sd962a7cyf3mifjeae8.streamlit.app/)**

---

## Key Findings

- **$2.99 trillion** in central bank gold holdings globally (2025) — up 21% in one year
- USD share of global reserves has declined from **71.1% (2001) → 56.9% (2025)**, falling every year since 2015
- Countries under **OFAC sanctions** hold proportionally more gold on average (25.4% vs 13.3% for non-sanctioned peers)
- **Poland** added 102 tonnes in 2025 alone — gold share jumped from 16.9% → 30.1% in 12 months
- Top 2026 predicted buyers: **Belarus, Iraq, Libya, Uzbekistan, Qatar** — scored on buying momentum, streak consistency, and geopolitical motivation

---

## Architecture

![Pipeline Architecture](docs/architecture.png)

The platform follows a **Bronze → Silver → Gold** data engineering pattern with a separate NLP layer feeding into the final master panel.

| Layer | Path | Description |
|-------|------|-------------|
| Bronze | `data/raw/` | Raw source files — WGC, IMF, World Bank, OFAC, UN |
| Silver | `data/staging/` | Cleaned, ISO3-coded, quarterly-aligned |
| Gold | `data/curated/` | Feature-engineered master panel (4,376 rows × 49 cols) |
| ML | `data/curated/ml_*` | Scores, predictions, model outputs |

The PostgreSQL schema is documented in [`sql/schema.sql`](sql/schema.sql) — a star schema with 5 tables, 1 denormalized analytical fact table, and a ranked accumulator view.

---

## ML Model

**Goal:** Predict which countries will increase gold reserves in 2026.

**Approach:** 4-Pillar Rule-Based Scoring Model, validated against Gradient Boosting and Logistic Regression baselines.

| Pillar | Weight | Signals |
|--------|--------|---------|
| Physical Buying Momentum | 30% | Actual tonne changes YoY (price-neutral, from WGC data) |
| Buying Consistency | 25% | Accumulation streak + 5-year buying frequency |
| Geopolitical Motivation | 25% | UN divergence from US + sanctions exposure |
| Strategic Allocation Gap | 20% | Room to grow gold share relative to peers |

**Coverage:** 182 countries in the master panel → 72 scored (filters: ≥ $500M gold holdings, sufficient history, non-null geo data)

**Model Performance (test set: 2020–2025)**

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC |
|-------|----------|-----------|--------|----|---------|
| Logistic Regression | 0.264 | 0.787 | 0.218 | 0.342 | 0.529 |
| **Gradient Boosting** | **0.402** | **0.861** | **0.378** | **0.525** | **0.561** |
| Ensemble | 0.256 | 0.800 | 0.201 | 0.321 | 0.528 |

Gradient Boosting achieves 0.86 precision — when it predicts a country will buy gold, it is correct 86% of the time. Training: 2001–2019 | Test: 2020–2025 | Predict: 2026.

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

## Dashboard Pages

| Page | What it shows |
|------|--------------|
| Overview | Global gold map, top 15 holders, KPI cards — macro context at a glance |
| Gold vs USD | Gold trend vs USD dominance (dual-axis), Pearson correlation, OLS trendline |
| Geopolitics | Sanctions scoring, UN alignment scatter, geo bloc analysis |
| Sentiment | Live NLP feed — gold & USD sentiment signals from GDELT/Reuters |
| ML Predictions | 2026 country-level scores — 4-pillar breakdown, model metrics, coverage funnel |

---

## Data Sources

| Source | Data | Coverage |
|--------|------|----------|
| World Gold Council / IMF IFS | Gold holdings in tonnes | 182 countries |
| IMF COFER | USD share of global reserves | Global aggregate |
| World Bank API | Total reserves, GDP, macro indicators | 182 countries |
| OFAC | Sanctions severity (0–3) | All countries |
| UN General Assembly | Voting divergence from US | 182 countries |
| GDELT / News APIs | Financial news sentiment (NLP) | Live feed |

---

## Tech Stack

```
Python · pandas · numpy · scikit-learn · XGBoost · HuggingFace FinBERT
PostgreSQL · SQLAlchemy · psycopg2
Streamlit · Plotly
Docker · docker-compose
```

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/sathwikarr/gold-reserve-platform.git
cd gold-reserve-platform
pip install -r requirements.txt

# Run the full pipeline (re-processes all data + ML)
python run_pipeline.py

# Launch the Streamlit app
streamlit run app.py
```

### With Docker

```bash
cp .env.example .env          # fill in your settings
docker-compose up --build     # starts app + postgres at localhost:8501
```

### Load data into PostgreSQL

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/gold_reserve_db
psql $DATABASE_URL -f sql/schema.sql      # create tables and view
python src/db/load_to_postgres.py         # load curated data
psql $DATABASE_URL -f sql/queries.sql     # run analytical queries
```

---

## Project Structure

```
gold-reserve-platform/
├── app.py                          # Streamlit app (5 analytical pages)
├── run_pipeline.py                 # Single command re-runs full pipeline
│
├── src/
│   ├── ingestion/                  # Raw data fetchers (WGC, IMF, World Bank)
│   ├── cleaning/                   # Standardisation and ISO3 alignment
│   ├── features/                   # Feature engineering and master panel build
│   ├── nlp/                        # NLP sentiment merge
│   ├── ml/                         # Scoring, training, and 2026 predictions
│   └── db/                         # PostgreSQL ETL loader
│
├── sql/
│   ├── schema.sql                  # Star schema — 5 tables, 1 view, indexes
│   └── queries.sql                 # 10 analytical queries
│
├── data/
│   ├── raw/                        # Bronze: original source files
│   ├── staging/                    # Silver: cleaned, standardised
│   └── curated/                    # Gold: master panel + ML outputs
│       ├── master_panel_nlp.csv    # 4,376 rows × 49 cols, 182 countries
│       ├── ml_country_scores.csv   # 72 scored countries with pillar breakdown
│       └── ml_top10_predictions.csv
│
├── notebooks/
│   ├── 01_eda_gold_reserves.ipynb
│   ├── 02_eda_usd_vs_gold.ipynb
│   ├── 03_eda_geopolitical.ipynb
│   └── 04_ml_model_training.ipynb
│
├── docs/
│   ├── architecture.png
│   ├── ml_top10_predictions.png
│   ├── ml_feature_importance.png
│   └── ml_roc_curves.png
│
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## License

[MIT](LICENSE) © 2026 Sathwik Arroju

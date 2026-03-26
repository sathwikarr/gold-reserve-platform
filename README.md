# Central Bank Gold Accumulation vs USD Power & Geopolitical Risk Platform

> Are countries increasing gold reserves due to declining trust in the US dollar and rising geopolitical risk?

An end-to-end analytics and ML platform integrating central bank gold reserves, global USD dominance metrics, sanctions exposure, and NLP-derived financial narratives to analyze and predict country-level gold accumulation behavior.

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
- Top 2026 predicted buyers: **Qatar, Uzbekistan, Iraq, China, India** (based on streak + physical momentum + geo motivation)

---

## ML Model

**Goal:** Predict which countries will increase gold reserves next year.

**Features (4 pillars):**
1. Physical buying momentum — actual tonne changes (price-neutral, from WGC data)
2. Buying consistency — accumulation streak + 5-year frequency
3. Geopolitical motivation — UN divergence score + sanctions exposure
4. Strategic allocation gap — room to grow gold share

**Models:** XGBoost + Logistic Regression ensemble
**Training:** 2001–2019 | **Test:** 2020–2025 | **Predict:** 2026

---

## Data Sources

| Source | Data | Update Frequency |
|--------|------|-----------------|
| World Gold Council / IMF IFS | Gold holdings in tonnes (98 countries) | Monthly |
| IMF COFER | USD share of global reserves | Quarterly |
| World Bank API | Total reserves, GDP, macro indicators | Annual |
| OFAC | Sanctions severity scores | Ongoing |
| UN General Assembly | Voting alignment with US | Annual |
| GDELT / News APIs | Financial news sentiment (NLP) | Daily |

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
│
├── docs/
│   ├── architecture.png          # Pipeline architecture diagram
│   ├── ml_top10_predictions.png
│   ├── ml_feature_importance.png
│   └── ml_roc_curves.png
│
├── notebooks/
│   └── 01_eda_gold_reserves.ipynb
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
| Overview | Global gold map, top holders, KPI cards |
| Gold vs USD | Gold trend vs USD dominance (dual-axis) |
| Geopolitics | Sanctions scoring, UN alignment, geo blocs |
| Sentiment | NLP analysis of financial news |
| ML Predictions | 2026 country-level predictions with scores |

---

## Resume Line

> Built an end-to-end geopolitical analytics platform integrating central bank gold reserves (WGC/IMF IFS, 98 countries), global USD dominance metrics, sanctions exposure, and NLP-derived financial narratives to analyze and predict country-level gold accumulation behavior. Data updated March 2026 — predicts 2026 accumulators.

---

## Roadmap

- [ ] Live GDELT news feed integration (real-time NLP)
- [ ] Airflow DAG for automated pipeline scheduling
- [ ] dbt transformations for Silver → Gold layer
- [ ] Prophet time-series forecasting for gold price trends
- [ ] Streamlit Cloud deployment (public demo URL)

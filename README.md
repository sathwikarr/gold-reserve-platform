# Gold Reserve Analytics Platform

An end-to-end analytics platform tracking central bank gold accumulation
against USD dominance and geopolitical risk.

## Project Phases
- **v1** — Gold + reserves data pipeline + dashboard
- **v2** — Geopolitical scoring layer
- **v3** — NLP narrative analysis
- **v4** — ML prediction model

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Project Structure
```
data/         # Bronze / Silver / Gold data layers
notebooks/    # Exploratory analysis
src/          # Python modules (ingestion, cleaning, features, nlp, ml)
sql/          # Schema and queries
docs/         # Architecture and documentation
```

## Stack
Python · pandas · PostgreSQL · Jupyter · Tableau

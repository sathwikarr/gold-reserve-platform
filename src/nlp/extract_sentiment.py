"""
Sentiment Extraction — V3 NLP Pipeline
Runs FinBERT sentiment analysis on cleaned article titles.

Primary model: ProsusAI/finbert (financial domain BERT)
  - Labels: positive / negative / neutral
  - Pre-trained on financial news and analyst reports
  - Ideal for central bank / macroeconomic news headlines

Fallback: VADER (rule-based, no model download required)
  - Used automatically if transformers / torch are not installed
  - VADER compound score mapped to positive/negative/neutral labels

Input:  data/staging/articles_clean.csv
Output: data/staging/articles_sentiment.csv
"""

import pandas as pd
import logging
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
STAGING_DIR = Path(__file__).resolve().parents[2] / "data" / "staging"

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ── Model config ──────────────────────────────────────────────────────────────
FINBERT_MODEL = "ProsusAI/finbert"
BATCH_SIZE    = 32
MAX_LENGTH    = 128  # FinBERT max token length


def load_finbert():
    """
    Attempt to load FinBERT pipeline.
    Returns (pipeline, 'finbert') on success, (None, 'vader') on failure.
    """
    try:
        from transformers import pipeline
        log.info("Loading FinBERT model (ProsusAI/finbert) — first run downloads ~440MB...")
        nlp_pipeline = pipeline(
            "text-classification",
            model=FINBERT_MODEL,
            tokenizer=FINBERT_MODEL,
            max_length=MAX_LENGTH,
            truncation=True,
            device=-1,  # CPU inference
        )
        log.info("FinBERT loaded successfully.")
        return nlp_pipeline, "finbert"
    except ImportError:
        log.warning("transformers not installed. Falling back to VADER sentiment.")
        return None, "vader"
    except Exception as e:
        log.warning(f"FinBERT load failed ({e}). Falling back to VADER.")
        return None, "vader"


class FinancialKeywordSentiment:
    """
    Rule-based financial sentiment scorer for central bank / macro headlines.
    Designed specifically for the gold-reserves, de-dollarization, and USD
    dominance domain. No external dependencies required.

    Scoring: positive keywords +1 each, negative keywords -1 each.
    Compound = sum / (|sum| + 1) → bounded in (-1, 1).
    Label thresholds: positive > 0.05, negative < -0.05, else neutral.
    """

    POSITIVE = [
        "record", "surge", "surges", "accelerates", "boosts", "adds",
        "rebounds", "stable", "rises", "rises to", "hit record", "hits record",
        "buys", "buying", "increases", "increase", "expanded", "expands",
        "diversification", "diversifies", "repatriates", "milestone",
        "doubles", "triples", "reaches", "joins", "strategic", "resilient",
        "strong", "dominant", "demand", "elevated", "largest", "highest",
        "net buyer", "net buyers", "plans", "announces", "program",
        "pays off", "growth", "positive", "benefit",
    ]

    NEGATIVE = [
        "sanctions", "sanctioned", "frozen", "crisis", "decline", "declines",
        "falls", "falling", "loses", "loss", "weaponized", "weaponization",
        "threat", "threatens", "risk", "halts", "suspends", "concern",
        "pain", "uncertainty", "volatility", "dump", "dumps", "abandons",
        "squeeze", "trouble", "slips", "lowest", "shock", "record high debt",
        "depletion", "pledge", "pledged", "collateral", "circumvents",
        "smuggling", "smuggle", "bypass", "isolation", "excluded", "warning",
    ]

    def score(self, text: str) -> tuple[float, str]:
        text = text.lower()
        pos = sum(1 for w in self.POSITIVE if w in text)
        neg = sum(1 for w in self.NEGATIVE if w in text)
        raw = pos - neg
        compound = round(raw / (abs(raw) + 1), 4) if raw != 0 else 0.0
        if compound > 0.05:
            label = "positive"
        elif compound < -0.05:
            label = "negative"
        else:
            label = "neutral"
        return compound, label


def run_finbert(df: pd.DataFrame, pipeline) -> pd.DataFrame:
    """Run FinBERT on text_clean column in batches."""
    texts = df["text_clean"].tolist()
    results = []

    log.info(f"Running FinBERT on {len(texts):,} articles in batches of {BATCH_SIZE}...")
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        preds = pipeline(batch, truncation=True, max_length=MAX_LENGTH)
        results.extend(preds)
        if (i // BATCH_SIZE) % 10 == 0:
            log.info(f"  Processed {min(i + BATCH_SIZE, len(texts)):,} / {len(texts):,}")

    df["sentiment_label"]  = [r["label"].lower() for r in results]
    df["sentiment_score"]  = [round(r["score"], 4) for r in results]
    df["sentiment_method"] = "finbert"
    return df


def run_keyword_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """Run rule-based financial keyword sentiment on text_clean column."""
    log.info(f"Running financial keyword sentiment on {len(df):,} articles...")
    analyzer = FinancialKeywordSentiment()
    results = df["text_clean"].apply(analyzer.score)
    df["sentiment_score"]  = results.apply(lambda x: x[0])
    df["sentiment_label"]  = results.apply(lambda x: x[1])
    df["sentiment_method"] = "financial_keyword"
    return df


def run():
    log.info("=" * 60)
    log.info("Sentiment Extraction — V3 NLP Pipeline")
    log.info("=" * 60)

    in_path = STAGING_DIR / "articles_clean.csv"
    if not in_path.exists():
        raise FileNotFoundError(f"Clean articles not found: {in_path}\nRun clean_articles.py first.")

    df = pd.read_csv(in_path)
    log.info(f"Articles loaded: {len(df):,}")

    # Try FinBERT first, fall back to keyword-based
    pipeline, method = load_finbert()

    if method == "finbert":
        df = run_finbert(df, pipeline)
    else:
        log.info("FinBERT unavailable — using financial keyword sentiment scorer.")
        df = run_keyword_sentiment(df)

    # ── Sentiment distribution summary ────────────────────────────────────────
    dist = df["sentiment_label"].value_counts()
    log.info(f"\nSentiment distribution ({method}):")
    log.info(dist.to_string())

    # ── Per-query sentiment breakdown ─────────────────────────────────────────
    query_sent = df.groupby(["query_label", "sentiment_label"]).size().unstack(fill_value=0)
    log.info(f"\nSentiment by query:\n{query_sent.to_string()}")

    out_path = STAGING_DIR / "articles_sentiment.csv"
    df.to_csv(out_path, index=False)
    log.info(f"\nSaved → {out_path}")
    log.info(f"Method used: {method}")


if __name__ == "__main__":
    run()

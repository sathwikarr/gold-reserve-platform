"""
Article Cleaning & Country Tagging — V3 NLP Pipeline
Reads raw GDELT articles and:
  1. Deduplicates by title
  2. Filters to English-language articles
  3. Removes noise (short titles, ads, irrelevant domains)
  4. Tags each article with a country ISO3 code based on title keywords
  5. Computes a text_clean field ready for NLP

Input:  data/raw/gdelt_articles_*.csv  (most recent)
Output: data/staging/articles_clean.csv
"""

import re
import pandas as pd
import logging
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
RAW_DIR     = Path(__file__).resolve().parents[2] / "data" / "raw"
STAGING_DIR = Path(__file__).resolve().parents[2] / "data" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ── Country keyword mapping ───────────────────────────────────────────────────
# Maps country name / demonym / alias → ISO3 code
# Focuses on the most relevant countries for the gold accumulation thesis
COUNTRY_KEYWORDS = {
    # Major gold accumulators
    "CHN": ["china", "chinese", "beijing", "pboc", "people's bank of china"],
    "RUS": ["russia", "russian", "moscow", "kremlin", "bank of russia"],
    "IND": ["india", "indian", "rbi", "reserve bank of india", "new delhi"],
    "TUR": ["turkey", "turkish", "ankara", "tcmb", "erdogan"],
    "POL": ["poland", "polish", "warsaw", "nbp"],
    "KAZ": ["kazakhstan", "kazakh", "astana", "national bank of kazakhstan"],
    "UZB": ["uzbekistan", "uzbek", "tashkent"],
    "QAT": ["qatar", "qatari", "doha", "qatar central bank"],
    "SAU": ["saudi", "saudi arabia", "riyadh", "sama"],
    "IRN": ["iran", "iranian", "tehran"],
    "VEN": ["venezuela", "venezuelan", "caracas"],
    "EGY": ["egypt", "egyptian", "cairo", "cbe"],
    "BRA": ["brazil", "brazilian", "brasilia", "banco central do brasil"],
    "ZAF": ["south africa", "south african", "sarb", "johannesburg"],
    "MEX": ["mexico", "mexican", "banxico", "mexico city"],
    "SGP": ["singapore", "mas", "monetary authority of singapore"],
    "HKG": ["hong kong", "hkma"],
    "ARE": ["uae", "dubai", "abu dhabi", "emirates", "cbuae"],
    "DEU": ["germany", "german", "bundesbank", "berlin", "frankfurt"],
    "FRA": ["france", "french", "banque de france", "paris"],
    "GBR": ["uk", "britain", "british", "bank of england", "london"],
    "JPN": ["japan", "japanese", "boj", "bank of japan", "tokyo"],
    "USA": ["united states", "federal reserve", "fed", "us treasury", "washington"],
    "EUR": ["eurozone", "ecb", "european central bank"],
    "HUN": ["hungary", "hungarian", "mnb", "budapest"],
    "CZE": ["czech", "cnb", "prague"],
    "SRB": ["serbia", "serbian", "belgrade", "nbs"],
    "THA": ["thailand", "thai", "bank of thailand", "bangkok"],
    "MYS": ["malaysia", "bank negara", "kuala lumpur"],
    "IDN": ["indonesia", "bank indonesia", "jakarta"],
    "PHL": ["philippines", "bsp", "bangko sentral", "manila"],
    "PAK": ["pakistan", "sbp", "state bank of pakistan", "islamabad"],
    "BGD": ["bangladesh", "dhaka"],
    "NGA": ["nigeria", "cbn", "central bank of nigeria", "abuja"],
    "KEN": ["kenya", "cbk", "nairobi"],
    "GHA": ["ghana", "bog", "bank of ghana", "accra"],
    "ARG": ["argentina", "bcra", "buenos aires"],
    "CHL": ["chile", "chilean", "santiago"],
    "COL": ["colombia", "banrep", "bogota"],
    "PER": ["peru", "peruvian", "lima"],
    "UKR": ["ukraine", "ukrainian", "kyiv", "kiev"],
    "BLR": ["belarus", "belarusian", "minsk"],
    "AZE": ["azerbaijan", "baku", "cbar"],
    "GEO": ["georgia", "tbilisi", "nbg"],
    "MNG": ["mongolia", "mongolian", "ulaanbaatar"],
    "SRB": ["serbia", "serbian", "belgrade"],
    "KWT": ["kuwait", "kuwaiti", "cbk"],
}

# Noise domains to filter out
NOISE_DOMAINS = {
    "reddit.com", "twitter.com", "facebook.com", "youtube.com",
    "instagram.com", "pinterest.com", "tumblr.com", "tiktok.com",
}

# Minimum title length (chars) to keep
MIN_TITLE_LEN = 20


def load_latest_raw(raw_dir: Path) -> pd.DataFrame:
    """Load the most recently created GDELT raw file."""
    files = sorted(raw_dir.glob("gdelt_articles_*.csv"), reverse=True)
    if not files:
        raise FileNotFoundError(f"No GDELT raw files found in {raw_dir}")
    log.info(f"Loading: {files[0].name}")
    return pd.read_csv(files[0])


def clean_title(title: str) -> str:
    """Normalize title text for NLP processing."""
    title = str(title).lower().strip()
    # Remove URLs
    title = re.sub(r"http\S+", "", title)
    # Remove special characters but keep spaces and basic punctuation
    title = re.sub(r"[^\w\s\-\']", " ", title)
    # Collapse whitespace
    title = re.sub(r"\s+", " ", title).strip()
    return title


def tag_country(title_lower: str) -> str:
    """
    Return the ISO3 code of the first country found in the title.
    Returns 'GLOBAL' if no specific country is matched
    (article is about world-level trends).
    """
    for iso3, keywords in COUNTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in title_lower:
                return iso3
    return "GLOBAL"


def run():
    log.info("=" * 60)
    log.info("Article Cleaning & Country Tagging — V3 NLP Pipeline")
    log.info("=" * 60)

    df = load_latest_raw(RAW_DIR)
    log.info(f"Raw articles loaded : {len(df):,}")

    # ── 1. Filter English only ────────────────────────────────────────────────
    df = df[df["language"].str.lower().fillna("") == "english"].copy()
    log.info(f"After English filter: {len(df):,}")

    # ── 2. Remove noise domains ───────────────────────────────────────────────
    df = df[~df["domain"].isin(NOISE_DOMAINS)].copy()

    # ── 3. Remove short / empty titles ───────────────────────────────────────
    df = df[df["title"].str.len() >= MIN_TITLE_LEN].copy()

    # ── 4. Deduplicate by title ───────────────────────────────────────────────
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["title"]).reset_index(drop=True)
    log.info(f"After dedup         : {len(df):,}  (removed {before_dedup - len(df):,} duplicates)")

    # ── 5. Clean title text ───────────────────────────────────────────────────
    df["text_clean"] = df["title"].apply(clean_title)

    # ── 6. Tag countries ──────────────────────────────────────────────────────
    df["country_code"] = df["text_clean"].apply(tag_country)

    # ── 7. Parse year from seendate if available ──────────────────────────────
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)

    # ── Stats ─────────────────────────────────────────────────────────────────
    country_dist = df["country_code"].value_counts().head(15)
    log.info(f"\nTop 15 country tags:\n{country_dist.to_string()}")
    log.info(f"\nQuery label distribution:\n{df['query_label'].value_counts().to_string()}")

    out_path = STAGING_DIR / "articles_clean.csv"
    df.to_csv(out_path, index=False)

    log.info(f"\nDone. Clean articles : {len(df):,}")
    log.info(f"Countries tagged     : {df['country_code'].nunique()} unique codes")
    log.info(f"Saved → {out_path}")


if __name__ == "__main__":
    run()

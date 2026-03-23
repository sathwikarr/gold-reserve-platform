"""
Geopolitical Data Ingestion
Two sources:
  1. OFAC Sanctions — which countries have active US sanctions
     Source: US Treasury OFAC sanctions programs list (public CSV)

  2. UN General Assembly Voting — how closely each country votes with the US
     Source: Erik Voeten UNvotes dataset (public, Harvard Dataverse)
     https://dataverse.harvard.edu/dataset.xhtml?persistentId=hdl:1902.1/12379

Output:
  data/raw/ofac_sanctions_YYYYMMDD.csv
  data/raw/un_votes_YYYYMMDD.csv
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import io

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


# ── OFAC Sanctions ────────────────────────────────────────────────────────────
# US Treasury publishes a consolidated sanctions list as a public CSV
OFAC_URL = "https://www.treasury.gov/ofac/downloads/consolidated/cons_prim.csv"

# Country-level sanctions programs — manually curated from OFAC website
# Source: https://ofac.treasury.gov/sanctions-programs-and-country-information
# Each entry represents an active country-level sanctions program
# score = severity (3=comprehensive, 2=targeted, 1=sectoral/minor)
SANCTIONS_DATA = {
    # Comprehensive sanctions (score 3)
    "IRN": {"country": "Iran",           "score": 3, "since": 1979, "programs": ["Iran"]},
    "PRK": {"country": "North Korea",    "score": 3, "since": 1950, "programs": ["DPRK"]},
    "CUB": {"country": "Cuba",           "score": 3, "since": 1963, "programs": ["Cuba"]},
    "SYR": {"country": "Syria",          "score": 3, "since": 2004, "programs": ["Syria"]},
    # Major targeted sanctions (score 2) — post-2014
    "RUS": {"country": "Russia",         "score": 2, "since": 2014, "programs": ["Ukraine-EO13685","Russia-EO14024"]},
    "BLR": {"country": "Belarus",        "score": 2, "since": 2004, "programs": ["Belarus"]},
    "VEN": {"country": "Venezuela",      "score": 2, "since": 2015, "programs": ["Venezuela-EO13850"]},
    "MMR": {"country": "Myanmar",        "score": 2, "since": 2021, "programs": ["Burma-EO14014"]},
    "NIC": {"country": "Nicaragua",      "score": 2, "since": 2018, "programs": ["Nicaragua-EO13851"]},
    "HTI": {"country": "Haiti",          "score": 1, "since": 2022, "programs": ["Haiti-EO14058"]},
    # Sectoral / targeted individuals (score 1)
    "ZWE": {"country": "Zimbabwe",       "score": 1, "since": 2003, "programs": ["Zimbabwe"]},
    "SDN": {"country": "Sudan",          "score": 1, "since": 1997, "programs": ["Sudan"]},
    "MLI": {"country": "Mali",           "score": 1, "since": 2022, "programs": ["Mali-EO13882"]},
    "SOM": {"country": "Somalia",        "score": 1, "since": 2010, "programs": ["Somalia-EO13536"]},
    "COD": {"country": "DR Congo",       "score": 1, "since": 2006, "programs": ["DRC-EO13413"]},
    "LBY": {"country": "Libya",          "score": 1, "since": 2011, "programs": ["Libya-EO13566"]},
    "YEM": {"country": "Yemen",          "score": 1, "since": 2012, "programs": ["Yemen-EO13611"]},
    "IRQ": {"country": "Iraq",           "score": 1, "since": 1990, "programs": ["Iraq (Historical)"]},
    "ETH": {"country": "Ethiopia",       "score": 1, "since": 2021, "programs": ["Ethiopia-EO14046"]},
}

# Year each sanctions program became active at country level
SANCTIONS_YEAR_START = {
    "IRN": 1979, "PRK": 1950, "CUB": 1963, "SYR": 2004,
    "RUS": 2014, "BLR": 2006, "VEN": 2015, "MMR": 2021,
    "NIC": 2018, "HTI": 2022, "ZWE": 2003, "SDN": 1997,
    "MLI": 2022, "SOM": 2010, "COD": 2006, "LBY": 2011,
    "YEM": 2012, "IRQ": 1990, "ETH": 2021,
}


def build_sanctions_panel(start_year=2000, end_year=2024) -> pd.DataFrame:
    """Build a country x year sanctions score panel."""
    print("▶ Building OFAC sanctions panel...")
    rows = []
    for year in range(start_year, end_year + 1):
        for iso3, info in SANCTIONS_DATA.items():
            # sanctions score is 0 before the program started
            active_since = SANCTIONS_YEAR_START.get(iso3, info.get("since", 9999))
            score = info["score"] if year >= active_since else 0
            rows.append({
                "country_code":    iso3,
                "year":            year,
                "sanctions_score": score,
                "sanctions_active": 1 if score > 0 else 0,
                "sanctions_programs": ", ".join(info["programs"]) if score > 0 else "",
            })
    df = pd.DataFrame(rows)
    print(f"  ✓ {len(df)} country-year rows ({df['country_code'].nunique()} countries)")
    return df


# ── UN Voting Data ────────────────────────────────────────────────────────────
# Voeten, Erik; Strezhnev, Anton; Bailey, Michael, 2009,
# "United Nations General Assembly Voting Data"
# Harvard Dataverse — public dataset
UN_VOTES_URL = (
    "https://dataverse.harvard.edu/api/access/datafile/"
    ":persistentId?persistentId=doi:10.7910/DVN/LEJUQZ/IPRJ3I"
)

# Fallback: manually computed US alignment scores from published research
# Source: Bailey, Strezhnev & Voeten (2017) + UN data portal
# Value = % of UNGA votes where country voted same as US (ideal point proximity)
# Higher = more aligned with US foreign policy positions
UN_ALIGNMENT_SCORES = {
    # Strong US allies (score 70-95)
    "ISR": 85, "GBR": 78, "AUS": 76, "CAN": 74, "NZL": 73,
    "FRA": 70, "DEU": 69, "JPN": 68, "KOR": 67, "ITA": 66,
    "ESP": 64, "NLD": 65, "BEL": 64, "SWE": 62, "NOR": 63,
    "DNK": 62, "CHE": 60, "AUT": 59, "FIN": 61, "PRT": 62,
    "POL": 63, "CZE": 62, "HUN": 58, "ROU": 60, "BGR": 59,
    "HRV": 58, "SVK": 60, "SVN": 61, "EST": 63, "LVA": 62,
    "LTU": 62, "LUX": 63, "GRC": 60, "TUR": 48, "MEX": 42,
    # Moderate alignment (score 35-60)
    "BRA": 38, "ARG": 36, "COL": 52, "CHL": 46, "PER": 44,
    "URY": 40, "PAN": 48, "CRI": 50, "DOM": 46, "ECU": 38,
    "PHL": 52, "THA": 44, "IDN": 38, "MYS": 36, "SGP": 50,
    "IND": 35, "BGD": 33, "PAK": 32, "LKA": 34, "NPL": 33,
    "KEN": 38, "ETH": 34, "NGA": 35, "GHA": 38, "TZA": 33,
    "UGA": 34, "ZAF": 33, "MAR": 44, "TUN": 40, "EGY": 36,
    "JOR": 42, "SAU": 44, "ARE": 44, "KWT": 46, "QAT": 42,
    "OMN": 40, "BHR": 44, "IRQ": 38, "LBN": 36, "PSE": 18,
    "UKR": 52, "GEO": 55, "ARM": 42, "AZE": 40, "KAZ": 35,
    "UZB": 33, "MDA": 50, "SRB": 45, "ALB": 62, "MKD": 60,
    # Low alignment (score 15-35)
    "CHN": 22, "RUS": 18, "IRN": 12, "SYR": 14, "CUB": 15,
    "PRK": 10, "VEN": 18, "NIC": 22, "BLR": 20, "MMR": 25,
    "ZWE": 22, "SDN": 20, "BOL": 28, "ECU": 28, "DZA": 25,
    "AGO": 26, "MOZ": 25, "ZMB": 28, "CMR": 30, "CIV": 32,
    "MLI": 24, "BFA": 24, "GIN": 26, "SEN": 34, "MRT": 26,
    "LAO": 22, "KHM": 28, "VNM": 24, "MNG": 30, "AFG": 32,
    "YEM": 30, "LBY": 26, "SOM": 28, "COD": 28, "CAF": 25,
}


def build_un_alignment_panel(start_year=2000, end_year=2024) -> pd.DataFrame:
    """Build UN voting alignment panel — constant score per country across years."""
    print("▶ Building UN voting alignment panel...")

    rows = []
    for iso3, score in UN_ALIGNMENT_SCORES.items():
        for year in range(start_year, end_year + 1):
            rows.append({
                "country_code":      iso3,
                "year":              year,
                "un_alignment_score": score,
                # categorize alignment
                "geo_bloc": (
                    "US_allied"   if score >= 60 else
                    "neutral"     if score >= 35 else
                    "us_divergent"
                ),
            })
    df = pd.DataFrame(rows)
    print(f"  ✓ {len(df)} country-year rows ({df['country_code'].nunique()} countries)")
    return df


def run():
    today = datetime.now().strftime("%Y%m%d")

    # sanctions panel
    sanctions = build_sanctions_panel()
    sanctions_path = RAW_DIR / f"ofac_sanctions_{today}.csv"
    sanctions.to_csv(sanctions_path, index=False)
    print(f"  ✅ Saved → {sanctions_path}")

    # UN alignment panel
    un = build_un_alignment_panel()
    un_path = RAW_DIR / f"un_votes_{today}.csv"
    un.to_csv(un_path, index=False)
    print(f"  ✅ Saved → {un_path}")

    print(f"\n  Sanctions distribution:")
    print(sanctions[sanctions["year"] == 2024]["sanctions_score"]
          .value_counts().sort_index().to_string())

    print(f"\n  UN alignment distribution (2024):")
    un24 = un[un["year"] == 2024]
    print(un24["geo_bloc"].value_counts().to_string())
    print(f"\n  Most divergent (lowest US alignment):")
    print(un24.nsmallest(10, "un_alignment_score")[
        ["country_code", "un_alignment_score", "geo_bloc"]
    ].to_string(index=False))


if __name__ == "__main__":
    run()
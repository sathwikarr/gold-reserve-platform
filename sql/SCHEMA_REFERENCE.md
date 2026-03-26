# Database Schema Reference - Gold Reserve Platform

Complete reference documentation for all tables, columns, and relationships.

## Table of Contents

1. [Dimension Tables](#dimension-tables)
2. [Fact Tables](#fact-tables)
3. [Views](#views)
4. [Relationships](#relationships)
5. [Indexes](#indexes)
6. [Constraints](#constraints)

---

## Dimension Tables

### `dim_country`

Master dimension table for country master data. Contains static and slowly-changing attributes.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `country_code` | VARCHAR(3) | PRIMARY KEY | ISO 3166-1 alpha-3 country code (e.g., USA, CHN, GBR) |
| `country_name` | VARCHAR(255) | NOT NULL | Full country name |
| `geo_bloc` | VARCHAR(50) | - | Geographic/political bloc (e.g., "BRICS", "G20", "EU", "neutral") |
| `region` | VARCHAR(100) | - | Geographic region (e.g., "Asia Pacific", "Europe", "Americas") |
| `created_at` | TIMESTAMP | DEFAULT NOW | Timestamp of record creation |
| `updated_at` | TIMESTAMP | DEFAULT NOW | Timestamp of last update |

**Primary Key**: `country_code`

**Indexes**:
- `idx_dim_country_name` - For country name lookups
- `idx_dim_country_region` - For regional analysis
- `idx_dim_country_geo_bloc` - For bloc-based grouping

**Example Records**:
```
USA      | United States           | G20       | North America
CHN      | China                   | BRICS     | Asia Pacific
GBR      | United Kingdom          | G20       | Europe
RUS      | Russian Federation      | BRICS     | Europe/Asia
AUS      | Australia               | G20       | Asia Pacific
```

---

## Fact Tables

### `fact_gold_reserves`

Time-series fact table tracking gold holdings and reserve composition by country and year.

**Business Purpose**: Core measure table for tracking gold accumulation patterns, reserve composition, and year-over-year changes.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `gold_reserves_id` | SERIAL | PRIMARY KEY | Surrogate key |
| `country_code` | VARCHAR(3) | NOT NULL, FK | Reference to dim_country |
| `year` | INTEGER | NOT NULL | Year of observation (2000-2100) |
| `gold_tonnes` | NUMERIC(15,4) | - | Physical gold holdings in metric tonnes |
| `gold_value_usd` | NUMERIC(18,2) | >= 0 | USD valuation of gold reserves |
| `gold_share_pct` | NUMERIC(6,2) | - | Gold as percentage of total reserves (0-100) |
| `total_reserves_usd` | NUMERIC(18,2) | >= 0 | Total reserves in USD (gold + FX + other) |
| `reserves_excl_gold_usd` | NUMERIC(18,2) | >= 0 | Reserves excluding gold in USD |
| `is_accumulating` | BOOLEAN | - | TRUE if country bought gold this year |
| `accumulation_streak` | INTEGER | - | Consecutive years of gold buying |
| `gold_yoy_change_usd` | NUMERIC(18,2) | - | Year-over-year change in gold value (USD) |
| `gold_yoy_change_pct` | NUMERIC(8,2) | - | Year-over-year percentage change |
| `gold_share_yoy_change` | NUMERIC(8,2) | - | Year-over-year change in gold share (percentage points) |
| `gold_rank` | INTEGER | - | Country's rank by gold value (1=highest) |
| `country_share_of_world_gold_pct` | NUMERIC(6,2) | - | Country's share of world total gold (%) |
| `created_at` | TIMESTAMP | DEFAULT NOW | Record creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT NOW | Record update timestamp |

**Unique Constraint**: `(country_code, year)` - One record per country per year

**Check Constraints**:
- `positive_year`: year >= 2000 AND year <= 2100
- `non_negative_gold_value`: gold_value_usd >= 0
- `non_negative_total_reserves`: total_reserves_usd >= 0

**Indexes**:
- `idx_fact_gold_reserves_country_year` - Most common query pattern
- `idx_fact_gold_reserves_year` - Time-based filtering
- `idx_fact_gold_reserves_accumulating` - Boolean flag queries
- `idx_fact_gold_reserves_gold_share` - Ranking queries

**Example Queries**:
```sql
-- Top gold holders in 2025
SELECT country_code, gold_value_usd, gold_rank
FROM fact_gold_reserves
WHERE year = 2025 AND gold_rank <= 10;

-- Countries accumulating gold
SELECT country_code, gold_yoy_change_pct
FROM fact_gold_reserves
WHERE is_accumulating = TRUE AND year = 2025;
```

---

### `fact_usd_dominance`

Time-series fact table tracking global USD currency dominance metrics.

**Business Purpose**: Aggregate global measures for analyzing de-dollarization trends and USD's declining role in reserves.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `usd_dominance_id` | SERIAL | PRIMARY KEY | Surrogate key |
| `year` | INTEGER | UNIQUE NOT NULL | Year of observation |
| `usd_share_pct` | NUMERIC(6,2) | 0-100 | USD's share of global reserves (%) |
| `usd_share_yoy_change` | NUMERIC(8,2) | - | Year-over-year change in USD share (pct points) |
| `usd_share_drawdown_pct` | NUMERIC(8,2) | - | USD share trend indicator (-2 = rapid decline) |
| `world_gold_value_bn` | NUMERIC(12,2) | - | Global gold reserves value (billions USD) |
| `world_gold_share_pct` | NUMERIC(6,2) | - | Gold as % of world reserves |
| `world_total_reserves_bn` | NUMERIC(15,2) | - | Total global reserves (billions USD) |
| `us_total_reserves_bn` | NUMERIC(12,2) | - | US total reserves (billions USD) |
| `us_reserves_excl_gold_bn` | NUMERIC(12,2) | - | US FX reserves excl. gold (billions USD) |
| `us_gold_value_bn` | NUMERIC(12,2) | - | US gold value (billions USD) |
| `us_gdp_bn` | NUMERIC(15,2) | - | US GDP (billions USD) |
| `world_gdp_bn` | NUMERIC(15,2) | - | World GDP (billions USD) |
| `us_gdp_share_pct` | NUMERIC(6,2) | - | US share of world GDP (%) |
| `created_at` | TIMESTAMP | DEFAULT NOW | Record creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT NOW | Record update timestamp |

**Unique Constraint**: One record per year only

**Indexes**:
- `idx_fact_usd_dominance_year` - Time-based lookups

**Example Queries**:
```sql
-- USD decline trend
SELECT year, usd_share_pct, usd_share_yoy_change
FROM fact_usd_dominance
WHERE year >= 2015
ORDER BY year DESC;

-- World gold metrics
SELECT year, world_gold_value_bn, world_gold_share_pct
FROM fact_usd_dominance;
```

---

### `fact_geopolitical`

Time-series fact table tracking geopolitical and sanctions metrics by country.

**Business Purpose**: Captures international alignment, divergence, sanctions, and geopolitical risk for correlation analysis.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `geopolitical_id` | SERIAL | PRIMARY KEY | Surrogate key |
| `country_code` | VARCHAR(3) | NOT NULL, FK | Reference to dim_country |
| `year` | INTEGER | NOT NULL | Year of observation |
| `un_alignment_score` | NUMERIC(6,2) | 0-100 | UN voting alignment with major powers (%) |
| `un_divergence_score` | NUMERIC(6,2) | 0-100 | UN voting divergence from Western bloc (%) |
| `sanctions_score` | NUMERIC(6,2) | 0-100 | Severity of international sanctions (0=none, 100=severe) |
| `sanctions_active` | BOOLEAN | - | TRUE if country currently under sanctions |
| `geo_risk_score` | NUMERIC(6,2) | 0-100 | Overall geopolitical risk score |
| `geo_risk_tier` | VARCHAR(50) | - | Risk classification: "low", "medium", "high", "critical" |
| `created_at` | TIMESTAMP | DEFAULT NOW | Record creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT NOW | Record update timestamp |

**Unique Constraint**: `(country_code, year)`

**Indexes**:
- `idx_fact_geopolitical_country_year` - Time-series lookups
- `idx_fact_geopolitical_sanctions` - Sanctions-based analysis
- `idx_fact_geopolitical_risk_tier` - Risk classification queries

**Example Queries**:
```sql
-- Sanctioned countries
SELECT country_code, sanctions_score, geo_risk_tier
FROM fact_geopolitical
WHERE sanctions_active = TRUE AND year = 2025;
```

---

### `fact_master_panel`

Denormalized comprehensive fact table combining all core metrics.

**Business Purpose**: Single-table source for comprehensive analytical queries without complex JOINs. Optimized for dashboard queries and exploratory analysis.

| Column | Type | Description |
|--------|------|-------------|
| `master_panel_id` | SERIAL | Surrogate key |
| `country_code` | VARCHAR(3) | Country code (FK to dim_country) |
| `year` | INTEGER | Year of observation |
| **Gold Reserve Metrics** | | |
| `reserves_excl_gold_usd` | NUMERIC(18,2) | FX reserves excluding gold |
| `total_reserves_usd` | NUMERIC(18,2) | Total reserves |
| `gold_value_usd` | NUMERIC(18,2) | Gold value in USD |
| `gold_share_pct` | NUMERIC(6,2) | Gold % of reserves |
| `gold_yoy_change_usd` | NUMERIC(18,2) | YoY change in gold value |
| `gold_yoy_change_pct` | NUMERIC(8,2) | YoY percentage change |
| `gold_share_yoy_change` | NUMERIC(8,2) | YoY change in gold share |
| `is_accumulating` | BOOLEAN | Buying gold this year |
| `accumulation_streak` | INTEGER | Consecutive buying years |
| `gold_rank` | INTEGER | Rank by gold value |
| `country_share_of_world_gold_pct` | NUMERIC(6,2) | Share of world gold |
| **Global Context Metrics** | | |
| `world_total_reserves_bn` | NUMERIC(15,2) | World reserves total |
| `world_gold_value_bn` | NUMERIC(12,2) | World gold value |
| `world_gold_share_pct` | NUMERIC(6,2) | Gold % of world reserves |
| `us_gdp_bn` | NUMERIC(15,2) | US GDP |
| `world_gdp_bn` | NUMERIC(15,2) | World GDP |
| `us_gdp_share_pct` | NUMERIC(6,2) | US GDP % of world |
| **Geopolitical Metrics** | | |
| `un_alignment_score` | NUMERIC(6,2) | UN voting alignment |
| `un_divergence_score` | NUMERIC(6,2) | UN divergence score |
| `sanctions_score` | NUMERIC(6,2) | Sanctions severity |
| `sanctions_active` | BOOLEAN | Currently sanctioned |
| `geo_bloc` | VARCHAR(50) | Geographic bloc |
| `geo_risk_tier` | VARCHAR(50) | Risk classification |
| **NLP Sentiment Metrics** | | |
| `nlp_article_count` | INTEGER | News articles mentioning gold |
| `nlp_gold_positive` | INTEGER | Positive gold sentiment articles |
| `nlp_gold_negative` | INTEGER | Negative gold sentiment articles |
| `nlp_usd_positive` | INTEGER | Positive USD sentiment articles |
| `nlp_usd_negative` | INTEGER | Negative USD sentiment articles |
| `nlp_dedollar_mentions` | INTEGER | De-dollarization mentions |
| `nlp_sanctions_mentions` | INTEGER | Sanctions mentions |
| `nlp_composite_signal` | NUMERIC(8,2) | Composite signal score |
| `nlp_avg_sentiment_score` | NUMERIC(6,2) | Average sentiment (-1 to 1) |
| **Global NLP Context** | | |
| `global_usd_article_count` | INTEGER | Global USD articles |
| `global_usd_negative_pct` | NUMERIC(6,2) | % negative USD sentiment |
| `global_usd_positive_pct` | NUMERIC(6,2) | % positive USD sentiment |
| `global_usd_neutral_pct` | NUMERIC(6,2) | % neutral USD sentiment |
| **Derived Flags** | | |
| `accumulating_during_usd_decline` | BOOLEAN | Buying gold while USD weakens |

**Indexes**:
- `idx_fact_master_panel_country_year` - Standard lookups
- `idx_fact_master_panel_year` - Time-based filtering
- `idx_fact_master_panel_accumulating` - Boolean queries
- `idx_fact_master_panel_geo_bloc` - Regional analysis
- `idx_fact_master_panel_usd_divergence` - Strategy classification

---

### `ml_predictions`

Machine learning model predictions and component scores.

**Business Purpose**: Stores ML model outputs for gold accumulation propensity scoring with pillar-based feature importance.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `prediction_id` | SERIAL | PRIMARY KEY | Surrogate key |
| `country_code` | VARCHAR(3) | NOT NULL, FK | Reference to dim_country |
| `prediction_year` | INTEGER | NOT NULL | Year being predicted for |
| **Overall Score** | | | |
| `gold_accumulation_score` | NUMERIC(6,2) | 0-100 | Overall accumulation propensity (0-100) |
| **Component Pillars** | | | |
| `pillar_momentum` | NUMERIC(6,2) | 0-100 | Recent buying acceleration score |
| `pillar_consistency` | NUMERIC(6,2) | 0-100 | Long-term consistency score |
| `pillar_geo` | NUMERIC(6,2) | 0-100 | Geopolitical factor score |
| `pillar_alloc` | NUMERIC(6,2) | 0-100 | Allocation efficiency score |
| **Adjustments** | | | |
| `sanctions_bonus` | NUMERIC(6,2) | - | Adjustment for sanctions impact |
| **Supporting Features** | | | |
| `gold_share_pct` | NUMERIC(6,2) | - | Current gold share of reserves |
| `gold_tonnes_yoy` | NUMERIC(12,4) | - | Year-over-year gold tonnes change |
| `buy_frequency_5yr` | INTEGER | - | Gold purchases in past 5 years |
| `accumulation_streak` | INTEGER | - | Consecutive accumulation years |
| `gold_share_3yr_trend` | NUMERIC(8,2) | - | 3-year trend in gold share |
| `un_divergence_score` | NUMERIC(6,2) | - | UN voting divergence |
| `sanctions_score` | NUMERIC(6,2) | - | Sanctions severity |
| `geo_risk_tier` | VARCHAR(50) | - | Risk classification |
| `geo_bloc` | VARCHAR(50) | - | Geographic bloc |
| `created_at` | TIMESTAMP | DEFAULT NOW | Prediction creation time |
| `updated_at` | TIMESTAMP | DEFAULT NOW | Last update time |

**Unique Constraint**: `(country_code, prediction_year)`

**Indexes**:
- `idx_ml_predictions_country_year` - Lookups
- `idx_ml_predictions_year` - Year-based filtering
- `idx_ml_predictions_score` - Ranking by score
- `idx_ml_predictions_geo_bloc` - Regional analysis

---

## Views

### `v_top_accumulators`

Ranked view of top gold-buying countries with comprehensive metrics.

**Purpose**: Executive dashboard view showing countries by gold accumulation activity and geopolitical context.

**Key Columns**:
- `country_code`, `country_name` - Country identifiers
- `latest_year` - Most recent data available
- `gold_value_usd` - Current gold holdings value
- `accumulation_streak` - Years of consecutive buying
- `accumulating_years` - Total years buying in dataset
- `avg_gold_share_pct` - Average gold share of reserves
- `latest_ml_score` - Latest ML prediction score
- `latest_momentum`, `latest_consistency` - ML component scores

**Example Usage**:
```sql
SELECT * FROM v_top_accumulators
WHERE gold_value_usd > 100000000000  -- $100B+
ORDER BY latest_ml_score DESC;
```

---

## Relationships

### Foreign Key Relationships

```
dim_country
    ├── fact_gold_reserves.country_code → dim_country.country_code
    ├── fact_geopolitical.country_code → dim_country.country_code
    ├── fact_master_panel.country_code → dim_country.country_code
    └── ml_predictions.country_code → dim_country.country_code
```

**Referential Integrity**: All fact tables maintain referential integrity to the dimension table. Deleting a country code from `dim_country` is restricted by foreign key constraints.

---

## Indexes

### Summary of All Indexes

| Table | Index Name | Columns | Purpose |
|-------|-----------|---------|---------|
| dim_country | idx_dim_country_name | country_name | Name lookups |
| dim_country | idx_dim_country_region | region | Regional grouping |
| dim_country | idx_dim_country_geo_bloc | geo_bloc | Bloc-based analysis |
| fact_gold_reserves | idx_fact_gold_reserves_country_year | country_code, year | Standard lookups |
| fact_gold_reserves | idx_fact_gold_reserves_year | year | Time-based filtering |
| fact_gold_reserves | idx_fact_gold_reserves_accumulating | is_accumulating, year | Status queries |
| fact_gold_reserves | idx_fact_gold_reserves_gold_share | gold_share_pct DESC | Ranking queries |
| fact_usd_dominance | idx_fact_usd_dominance_year | year | Year lookups |
| fact_geopolitical | idx_fact_geopolitical_country_year | country_code, year | Standard lookups |
| fact_geopolitical | idx_fact_geopolitical_sanctions | sanctions_active, year | Sanctions analysis |
| fact_geopolitical | idx_fact_geopolitical_risk_tier | geo_risk_tier | Risk classification |
| fact_master_panel | idx_fact_master_panel_country_year | country_code, year | Standard lookups |
| fact_master_panel | idx_fact_master_panel_year | year | Time filtering |
| fact_master_panel | idx_fact_master_panel_accumulating | is_accumulating | Status queries |
| fact_master_panel | idx_fact_master_panel_geo_bloc | geo_bloc | Regional analysis |
| fact_master_panel | idx_fact_master_panel_gold_share | gold_share_pct DESC | Ranking queries |
| fact_master_panel | idx_fact_master_panel_usd_divergence | accumulating_during_usd_decline | Strategy queries |
| ml_predictions | idx_ml_predictions_country_year | country_code, prediction_year | Lookups |
| ml_predictions | idx_ml_predictions_year | prediction_year | Year filtering |
| ml_predictions | idx_ml_predictions_score | gold_accumulation_score DESC | Ranking |
| ml_predictions | idx_ml_predictions_geo_bloc | geo_bloc | Regional analysis |

---

## Constraints

### Data Validation Constraints

**Year Constraints** (all fact tables):
- Valid range: 2000 to 2100
- Ensures historical data integrity and prevents future data entry errors

**Value Constraints**:
- `gold_value_usd >= 0` - Non-negative financial amounts
- `total_reserves_usd >= 0` - Non-negative reserves
- `reserves_excl_gold_usd >= 0` - Non-negative FX reserves
- `usd_share_pct` between 0 and 100 - Valid percentage
- `gold_share_pct` between 0 and 100 - Valid percentage
- Score columns (0-100) - Valid ML score ranges

**Uniqueness Constraints**:
- `fact_gold_reserves(country_code, year)` - One record per country-year
- `fact_usd_dominance(year)` - One global record per year
- `fact_geopolitical(country_code, year)` - One record per country-year
- `fact_master_panel(country_code, year)` - One record per country-year
- `ml_predictions(country_code, prediction_year)` - One prediction per country-year

**Referential Integrity**:
- All foreign keys require matching country codes in dim_country
- Cascade delete not enabled (prevent accidental data loss)

---

## Data Dictionary Summary

| Metric | Source Table | Typical Range | Frequency |
|--------|-------------|---------------|-----------|
| Gold Holdings (USD) | fact_gold_reserves | $0 - $650B | Annual |
| Gold Share of Reserves (%) | fact_gold_reserves | 0 - 100% | Annual |
| Gold Accumulation (YoY %) | fact_gold_reserves | -50% to +50% | Annual |
| USD Reserve Share (%) | fact_usd_dominance | 50% - 80% | Annual |
| Sanctions Score | fact_geopolitical | 0 - 100 | Annual |
| UN Divergence Score | fact_geopolitical | 0 - 100 | Annual |
| ML Accumulation Score | ml_predictions | 0 - 100 | Annual |
| NLP Sentiment | fact_master_panel | -1 to +1 | Event-based |

---

**Document Version**: 1.0
**Last Updated**: March 2026
**Database Version**: PostgreSQL 12+

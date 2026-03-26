-- ============================================================================
-- Gold Reserve Platform - PostgreSQL Schema
-- Professional data warehouse schema for gold reserve analysis
-- ============================================================================

-- Drop existing objects if they exist (for clean re-creation)
DROP VIEW IF EXISTS v_top_accumulators CASCADE;
DROP TABLE IF EXISTS ml_predictions CASCADE;
DROP TABLE IF EXISTS fact_geopolitical CASCADE;
DROP TABLE IF EXISTS fact_usd_dominance CASCADE;
DROP TABLE IF EXISTS fact_master_panel CASCADE;
DROP TABLE IF EXISTS fact_gold_reserves CASCADE;
DROP TABLE IF EXISTS dim_country CASCADE;

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

-- dim_country: Master dimension table for countries
-- Contains static/slowly-changing reference data about countries
CREATE TABLE dim_country (
    country_code VARCHAR(3) PRIMARY KEY,
    country_name VARCHAR(255) NOT NULL,
    geo_bloc VARCHAR(50),
    region VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_country_name ON dim_country(country_name);
CREATE INDEX idx_dim_country_region ON dim_country(region);
CREATE INDEX idx_dim_country_geo_bloc ON dim_country(geo_bloc);

-- ============================================================================
-- FACT TABLES
-- ============================================================================

-- fact_gold_reserves: Time-series facts about countries' gold reserves
-- Core measure table tracking gold holdings and reserve composition
CREATE TABLE fact_gold_reserves (
    gold_reserves_id SERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL REFERENCES dim_country(country_code),
    year INTEGER NOT NULL,
    gold_tonnes NUMERIC(15, 4),
    gold_value_usd NUMERIC(18, 2),
    gold_share_pct NUMERIC(6, 2),
    total_reserves_usd NUMERIC(18, 2),
    reserves_excl_gold_usd NUMERIC(18, 2),
    is_accumulating BOOLEAN,
    accumulation_streak INTEGER,
    gold_yoy_change_usd NUMERIC(18, 2),
    gold_yoy_change_pct NUMERIC(8, 2),
    gold_share_yoy_change NUMERIC(8, 2),
    gold_rank INTEGER,
    country_share_of_world_gold_pct NUMERIC(6, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(country_code, year),
    CONSTRAINT positive_year CHECK (year >= 2000 AND year <= 2100),
    CONSTRAINT non_negative_gold_value CHECK (gold_value_usd >= 0),
    CONSTRAINT non_negative_total_reserves CHECK (total_reserves_usd >= 0)
);

CREATE INDEX idx_fact_gold_reserves_country_year ON fact_gold_reserves(country_code, year);
CREATE INDEX idx_fact_gold_reserves_year ON fact_gold_reserves(year);
CREATE INDEX idx_fact_gold_reserves_accumulating ON fact_gold_reserves(is_accumulating, year);
CREATE INDEX idx_fact_gold_reserves_gold_share ON fact_gold_reserves(gold_share_pct DESC);

-- fact_usd_dominance: Time-series facts tracking USD dominance metrics globally
-- Aggregate global measures of USD's role in reserves and gold valuation
CREATE TABLE fact_usd_dominance (
    usd_dominance_id SERIAL PRIMARY KEY,
    year INTEGER UNIQUE NOT NULL,
    usd_share_pct NUMERIC(6, 2),
    usd_share_yoy_change NUMERIC(8, 2),
    usd_share_drawdown_pct NUMERIC(8, 2),
    world_gold_value_bn NUMERIC(12, 2),
    world_gold_share_pct NUMERIC(6, 2),
    world_total_reserves_bn NUMERIC(15, 2),
    us_total_reserves_bn NUMERIC(12, 2),
    us_reserves_excl_gold_bn NUMERIC(12, 2),
    us_gold_value_bn NUMERIC(12, 2),
    us_gdp_bn NUMERIC(15, 2),
    world_gdp_bn NUMERIC(15, 2),
    us_gdp_share_pct NUMERIC(6, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT positive_year CHECK (year >= 2000 AND year <= 2100),
    CONSTRAINT valid_usd_share CHECK (usd_share_pct >= 0 AND usd_share_pct <= 100)
);

CREATE INDEX idx_fact_usd_dominance_year ON fact_usd_dominance(year);

-- fact_geopolitical: Time-series geopolitical and sanctions metrics by country
-- Tracks international alignment, divergence, and geopolitical risk
CREATE TABLE fact_geopolitical (
    geopolitical_id SERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL REFERENCES dim_country(country_code),
    year INTEGER NOT NULL,
    un_alignment_score NUMERIC(6, 2),
    un_divergence_score NUMERIC(6, 2),
    sanctions_score NUMERIC(6, 2),
    sanctions_active BOOLEAN,
    geo_risk_score NUMERIC(6, 2),
    geo_risk_tier VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(country_code, year),
    CONSTRAINT positive_year CHECK (year >= 2000 AND year <= 2100),
    CONSTRAINT valid_scores CHECK (
        un_alignment_score >= 0 AND un_alignment_score <= 100 AND
        un_divergence_score >= 0 AND un_divergence_score <= 100 AND
        sanctions_score >= 0 AND sanctions_score <= 100 AND
        geo_risk_score >= 0 AND geo_risk_score <= 100
    )
);

CREATE INDEX idx_fact_geopolitical_country_year ON fact_geopolitical(country_code, year);
CREATE INDEX idx_fact_geopolitical_sanctions ON fact_geopolitical(sanctions_active, year);
CREATE INDEX idx_fact_geopolitical_risk_tier ON fact_geopolitical(geo_risk_tier);

-- fact_master_panel: Comprehensive fact table combining all core metrics
-- Denormalized table for efficient analytical queries
CREATE TABLE fact_master_panel (
    master_panel_id SERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL REFERENCES dim_country(country_code),
    year INTEGER NOT NULL,

    -- Gold reserve metrics
    reserves_excl_gold_usd NUMERIC(18, 2),
    total_reserves_usd NUMERIC(18, 2),
    gold_value_usd NUMERIC(18, 2),
    gold_share_pct NUMERIC(6, 2),
    gold_yoy_change_usd NUMERIC(18, 2),
    gold_yoy_change_pct NUMERIC(8, 2),
    gold_share_yoy_change NUMERIC(8, 2),
    is_accumulating BOOLEAN,
    accumulation_streak INTEGER,
    gold_rank INTEGER,
    usd_share_of_reserves_pct NUMERIC(6, 2),
    usd_share_yoy_change NUMERIC(8, 2),
    country_share_of_world_gold_pct NUMERIC(6, 2),

    -- Global metrics
    world_total_reserves_bn NUMERIC(15, 2),
    world_gold_value_bn NUMERIC(12, 2),
    us_gdp_bn NUMERIC(15, 2),
    world_gdp_bn NUMERIC(15, 2),
    us_gdp_share_pct NUMERIC(6, 2),
    us_total_reserves_bn NUMERIC(12, 2),
    us_reserves_excl_gold_bn NUMERIC(12, 2),
    us_gold_value_bn NUMERIC(12, 2),
    world_gold_share_pct NUMERIC(6, 2),
    usd_share_drawdown_pct NUMERIC(8, 2),

    -- Geopolitical metrics
    un_alignment_score NUMERIC(6, 2),
    un_divergence_score NUMERIC(6, 2),
    sanctions_score NUMERIC(6, 2),
    sanctions_active BOOLEAN,
    geo_bloc VARCHAR(50),
    geo_risk_score NUMERIC(6, 2),
    geo_risk_tier VARCHAR(50),

    -- NLP metrics
    nlp_article_count INTEGER,
    nlp_gold_positive INTEGER,
    nlp_gold_negative INTEGER,
    nlp_usd_positive INTEGER,
    nlp_usd_negative INTEGER,
    nlp_dedollar_mentions INTEGER,
    nlp_sanctions_mentions INTEGER,
    nlp_composite_signal NUMERIC(8, 2),
    nlp_avg_sentiment_score NUMERIC(6, 2),

    -- Global NLP metrics
    global_usd_article_count INTEGER,
    global_usd_negative_pct NUMERIC(6, 2),
    global_usd_positive_pct NUMERIC(6, 2),
    global_usd_neutral_pct NUMERIC(6, 2),
    global_usd_avg_score NUMERIC(6, 2),

    accumulating_during_usd_decline BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(country_code, year),
    CONSTRAINT positive_year CHECK (year >= 2000 AND year <= 2100)
);

CREATE INDEX idx_fact_master_panel_country_year ON fact_master_panel(country_code, year);
CREATE INDEX idx_fact_master_panel_year ON fact_master_panel(year);
CREATE INDEX idx_fact_master_panel_accumulating ON fact_master_panel(is_accumulating);
CREATE INDEX idx_fact_master_panel_geo_bloc ON fact_master_panel(geo_bloc);
CREATE INDEX idx_fact_master_panel_gold_share ON fact_master_panel(gold_share_pct DESC);
CREATE INDEX idx_fact_master_panel_usd_divergence ON fact_master_panel(accumulating_during_usd_decline);

-- ml_predictions: Machine learning model predictions and scores
-- Stores ML model outputs for gold accumulation propensity and feature importance
CREATE TABLE ml_predictions (
    prediction_id SERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL REFERENCES dim_country(country_code),
    prediction_year INTEGER NOT NULL,

    -- Overall score and ranking
    gold_accumulation_score NUMERIC(6, 2),

    -- Pillar-based component scores
    pillar_momentum NUMERIC(6, 2),
    pillar_consistency NUMERIC(6, 2),
    pillar_geo NUMERIC(6, 2),
    pillar_alloc NUMERIC(6, 2),

    -- Adjustment factors
    sanctions_bonus NUMERIC(6, 2),

    -- Additional features for context
    gold_share_pct NUMERIC(6, 2),
    gold_tonnes_yoy NUMERIC(12, 4),
    buy_frequency_5yr INTEGER,
    accumulation_streak INTEGER,
    gold_share_3yr_trend NUMERIC(8, 2),
    un_divergence_score NUMERIC(6, 2),
    sanctions_score NUMERIC(6, 2),
    geo_risk_tier VARCHAR(50),
    geo_bloc VARCHAR(50),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(country_code, prediction_year),
    CONSTRAINT positive_year CHECK (prediction_year >= 2000 AND prediction_year <= 2150),
    CONSTRAINT valid_scores CHECK (
        gold_accumulation_score >= 0 AND gold_accumulation_score <= 100 AND
        pillar_momentum >= 0 AND pillar_momentum <= 100 AND
        pillar_consistency >= 0 AND pillar_consistency <= 100 AND
        pillar_geo >= 0 AND pillar_geo <= 100 AND
        pillar_alloc >= 0 AND pillar_alloc <= 100
    )
);

CREATE INDEX idx_ml_predictions_country_year ON ml_predictions(country_code, prediction_year);
CREATE INDEX idx_ml_predictions_year ON ml_predictions(prediction_year);
CREATE INDEX idx_ml_predictions_score ON ml_predictions(gold_accumulation_score DESC);
CREATE INDEX idx_ml_predictions_geo_bloc ON ml_predictions(geo_bloc);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- v_top_accumulators: Ranked view of top gold-buying countries with comprehensive metrics
-- Useful for executive dashboards and identifying key market players
CREATE VIEW v_top_accumulators AS
SELECT
    dc.country_code,
    dc.country_name,
    dc.geo_bloc,
    dc.region,
    MAX(fgr.year) AS latest_year,
    MAX(fgr.gold_value_usd) AS gold_value_usd,
    MAX(fgr.gold_share_pct) AS gold_share_pct,
    MAX(fgr.accumulation_streak) AS accumulation_streak,
    SUM(CASE WHEN fgr.is_accumulating THEN 1 ELSE 0 END) AS accumulating_years,
    COUNT(DISTINCT fgr.year) AS years_in_dataset,
    ROUND(AVG(fgr.gold_share_pct), 2) AS avg_gold_share_pct,
    ROUND(AVG(fgr.gold_yoy_change_pct), 2) AS avg_yoy_change_pct,
    MAX(fgr.gold_rank) AS best_rank,
    MAX(fmp.un_divergence_score) AS latest_un_divergence,
    MAX(fmp.sanctions_active) AS latest_sanctions_active,
    MAX(fmp.geo_risk_tier) AS latest_geo_risk_tier,
    MAX(mp.gold_accumulation_score) AS latest_ml_score,
    MAX(mp.pillar_momentum) AS latest_momentum,
    MAX(mp.pillar_consistency) AS latest_consistency
FROM
    dim_country dc
    LEFT JOIN fact_gold_reserves fgr ON dc.country_code = fgr.country_code
    LEFT JOIN fact_master_panel fmp ON dc.country_code = fmp.country_code
        AND fmp.year = (SELECT MAX(year) FROM fact_master_panel WHERE country_code = dc.country_code)
    LEFT JOIN ml_predictions mp ON dc.country_code = mp.country_code
        AND mp.prediction_year = (SELECT MAX(prediction_year) FROM ml_predictions WHERE country_code = dc.country_code)
WHERE
    fgr.year IS NOT NULL
GROUP BY
    dc.country_code,
    dc.country_name,
    dc.geo_bloc,
    dc.region
ORDER BY
    MAX(fgr.gold_value_usd) DESC,
    country_name ASC;

-- ============================================================================
-- GRANTS AND PERMISSIONS (optional, customize as needed)
-- ============================================================================
-- Uncomment and modify these based on your user management strategy
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO analytics_user;

-- ============================================================================
-- DATA VALIDATION TRIGGERS (optional, for data quality)
-- ============================================================================
-- These can be added later to ensure data integrity at insertion time

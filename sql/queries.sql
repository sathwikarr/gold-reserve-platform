-- ============================================================================
-- Gold Reserve Platform - Analytical Queries
-- 10 Professional SQL queries for gold reserve analysis and intelligence
-- ============================================================================

-- ============================================================================
-- QUERY 1: Top 10 Gold Accumulators by Total Tonnes Added (2020-2025)
-- ============================================================================
-- Purpose: Identify which countries have increased their gold reserves most
--          significantly during the recent period (post-pandemic, de-dollarization era)
-- Use Case: Strategic analysis for geopolitical and economic trends
-- ============================================================================

SELECT
    dc.country_code,
    dc.country_name,
    dc.geo_bloc,
    COUNT(DISTINCT fgr.year) AS years_in_period,
    MIN(fgr.year) AS first_year,
    MAX(fgr.year) AS last_year,
    SUM(CASE WHEN fgr.gold_yoy_change_usd > 0 THEN fgr.gold_yoy_change_usd ELSE 0 END) AS total_gold_added_usd,
    SUM(CASE WHEN fgr.gold_yoy_change_pct > 0 THEN 1 ELSE 0 END) AS years_accumulating,
    ROUND(AVG(fgr.gold_yoy_change_pct), 2) AS avg_yoy_change_pct,
    MAX(fgr.gold_value_usd) AS latest_gold_value_usd,
    MAX(fgr.accumulation_streak) AS max_accumulation_streak
FROM
    fact_gold_reserves fgr
    INNER JOIN dim_country dc ON fgr.country_code = dc.country_code
WHERE
    fgr.year >= 2020
    AND fgr.year <= 2025
    AND fgr.gold_yoy_change_usd IS NOT NULL
GROUP BY
    dc.country_code,
    dc.country_name,
    dc.geo_bloc
HAVING
    SUM(CASE WHEN fgr.gold_yoy_change_usd > 0 THEN fgr.gold_yoy_change_usd ELSE 0 END) > 0
ORDER BY
    total_gold_added_usd DESC
LIMIT 10;

-- ============================================================================
-- QUERY 2: Countries Buying Gold While USD is Declining (De-Dollarization Signal)
-- ============================================================================
-- Purpose: Find countries executing counter-cyclical gold buying during USD weakness
--          This is a key signal of de-dollarization strategy
-- Use Case: Identify countries moving away from USD dependence
-- ============================================================================

WITH global_usd_trends AS (
    SELECT
        year,
        usd_share_drawdown_pct,
        LAG(usd_share_drawdown_pct) OVER (ORDER BY year) AS prev_drawdown
    FROM
        fact_usd_dominance
    WHERE
        year >= 2020
),
usd_decline_years AS (
    SELECT
        year
    FROM
        global_usd_trends
    WHERE
        usd_share_drawdown_pct < 0
        OR (prev_drawdown IS NOT NULL AND usd_share_drawdown_pct < prev_drawdown)
)
SELECT
    dc.country_code,
    dc.country_name,
    dc.geo_bloc,
    fgr.year,
    fgr.gold_yoy_change_pct,
    fgr.gold_yoy_change_usd,
    fgr.gold_share_pct,
    fgr.accumulation_streak,
    fmp.un_divergence_score,
    fmp.sanctions_score,
    CASE
        WHEN fmp.accumulating_during_usd_decline = TRUE THEN 'Strategic De-Dollar'
        ELSE 'Market Opportunistic'
    END AS strategy_classification
FROM
    fact_gold_reserves fgr
    INNER JOIN dim_country dc ON fgr.country_code = dc.country_code
    INNER JOIN fact_master_panel fmp ON fgr.country_code = fmp.country_code AND fgr.year = fmp.year
    INNER JOIN usd_decline_years udy ON fgr.year = udy.year
WHERE
    fgr.gold_yoy_change_pct > 0
    AND fgr.is_accumulating = TRUE
ORDER BY
    fgr.year DESC,
    fgr.gold_yoy_change_pct DESC;

-- ============================================================================
-- QUERY 3: Gold Share % Trends for G20 Countries Over Time
-- ============================================================================
-- Purpose: Track how major economies are allocating reserves toward gold
--          Identifies divergence in central bank policies
-- Use Case: Compare reserve management strategies of global power centers
-- ============================================================================

WITH g20_countries AS (
    SELECT country_code
    FROM dim_country
    WHERE country_code IN (
        'USA', 'CHN', 'JPN', 'DEU', 'IND', 'GBR', 'FRA', 'ITA', 'BRA',
        'CAN', 'KOR', 'RUS', 'AUS', 'MEX', 'IDN', 'NLD', 'SAU', 'TUR',
        'ZAF', 'ARG'
    )
)
SELECT
    dc.country_code,
    dc.country_name,
    fgr.year,
    fgr.gold_share_pct,
    fgr.total_reserves_usd,
    fgr.gold_value_usd,
    LAG(fgr.gold_share_pct) OVER (
        PARTITION BY fgr.country_code ORDER BY fgr.year
    ) AS previous_year_share,
    ROUND(fgr.gold_share_pct - LAG(fgr.gold_share_pct) OVER (
        PARTITION BY fgr.country_code ORDER BY fgr.year
    ), 2) AS share_change_pct,
    RANK() OVER (
        PARTITION BY fgr.year ORDER BY fgr.gold_share_pct DESC
    ) AS rank_by_year
FROM
    fact_gold_reserves fgr
    INNER JOIN g20_countries g20 ON fgr.country_code = g20.country_code
    INNER JOIN dim_country dc ON fgr.country_code = dc.country_code
WHERE
    fgr.year >= 2015
ORDER BY
    fgr.year DESC,
    rank_by_year ASC;

-- ============================================================================
-- QUERY 4: Correlation Proxy - Countries with High Sanctions AND High Gold Buying
-- ============================================================================
-- Purpose: Identify sanctioned nations increasing gold reserves
--          Indicator of sanctions-driven de-dollarization behavior
-- Use Case: Understand geopolitical risk and reserve substitution strategies
-- ============================================================================

SELECT
    dc.country_code,
    dc.country_name,
    dc.geo_bloc,
    fmp.year,
    fmp.sanctions_active,
    fmp.sanctions_score,
    fmp.gold_yoy_change_pct,
    fmp.gold_yoy_change_usd,
    fmp.gold_share_pct,
    fmp.un_divergence_score,
    fmp.geo_risk_tier,
    CASE
        WHEN fmp.sanctions_score >= 50 AND fmp.gold_yoy_change_pct > 5 THEN 'High Risk Accumulator'
        WHEN fmp.sanctions_score >= 50 AND fmp.gold_yoy_change_pct > 0 THEN 'Sanctioned Buyer'
        WHEN fmp.sanctions_score >= 50 THEN 'Sanctioned Non-Buyer'
        ELSE 'Non-Sanctioned'
    END AS geopolitical_classification,
    ROUND(
        (COALESCE(fmp.sanctions_score, 0) * 0.4) +
        (COALESCE(fmp.gold_yoy_change_pct, 0) * 0.4) +
        (COALESCE(fmp.un_divergence_score, 0) * 0.2),
        2
    ) AS composite_risk_score
FROM
    fact_master_panel fmp
    INNER JOIN dim_country dc ON fmp.country_code = dc.country_code
WHERE
    fmp.sanctions_score >= 50
    OR (fmp.gold_yoy_change_pct > 5 AND fmp.sanctions_score >= 30)
ORDER BY
    composite_risk_score DESC,
    fmp.year DESC;

-- ============================================================================
-- QUERY 5: Year-over-Year Gold Purchase Acceleration (3-Year Trend)
-- ============================================================================
-- Purpose: Identify accelerating gold buying behavior (momentum indicator)
--          Detect trend reversals and increasing commitment to gold
-- Use Case: Early warning system for major reserve compositional shifts
-- ============================================================================

WITH gold_trends AS (
    SELECT
        fgr.country_code,
        dc.country_name,
        dc.geo_bloc,
        fgr.year,
        fgr.gold_yoy_change_pct,
        fgr.is_accumulating,
        LAG(fgr.gold_yoy_change_pct) OVER (
            PARTITION BY fgr.country_code ORDER BY fgr.year
        ) AS gold_yoy_prev_year,
        LAG(fgr.gold_yoy_change_pct, 2) OVER (
            PARTITION BY fgr.country_code ORDER BY fgr.year
        ) AS gold_yoy_2yr_ago
    FROM
        fact_gold_reserves fgr
        INNER JOIN dim_country dc ON fgr.country_code = dc.country_code
    WHERE
        fgr.year >= 2020
)
SELECT
    country_code,
    country_name,
    geo_bloc,
    year,
    gold_yoy_change_pct AS current_yoy,
    gold_yoy_prev_year,
    gold_yoy_2yr_ago,
    ROUND((gold_yoy_change_pct - COALESCE(gold_yoy_prev_year, 0)), 2) AS acceleration_this_year,
    ROUND((gold_yoy_change_pct - COALESCE(gold_yoy_2yr_ago, 0)), 2) AS acceleration_2yr,
    CASE
        WHEN gold_yoy_change_pct > 5 AND gold_yoy_prev_year > 5 AND gold_yoy_2yr_ago > 5 THEN 'Strong Consistent'
        WHEN gold_yoy_change_pct > 5 AND (gold_yoy_prev_year IS NULL OR gold_yoy_prev_year <= 5) THEN 'Accelerating'
        WHEN gold_yoy_change_pct > 0 AND gold_yoy_change_pct <= 5 THEN 'Modest Growth'
        WHEN gold_yoy_change_pct <= 0 THEN 'Declining'
    END AS trend_classification
FROM
    gold_trends
WHERE
    gold_yoy_change_pct IS NOT NULL
    AND (gold_yoy_change_pct > 0 OR is_accumulating = TRUE)
ORDER BY
    year DESC,
    acceleration_this_year DESC
LIMIT 50;

-- ============================================================================
-- QUERY 6: USD Dominance Trend by Year
-- ============================================================================
-- Purpose: Track the global decline in USD's share of reserves over time
--          Measure the pace and magnitude of de-dollarization
-- Use Case: Macro trend analysis, investor briefings, policy impact assessment
-- ============================================================================

SELECT
    year,
    usd_share_pct,
    LAG(usd_share_pct) OVER (ORDER BY year) AS previous_year_usd_share,
    ROUND(usd_share_pct - LAG(usd_share_pct) OVER (ORDER BY year), 2) AS yoy_change_pct,
    usd_share_drawdown_pct,
    world_gold_value_bn,
    world_gold_share_pct,
    world_total_reserves_bn,
    us_total_reserves_bn,
    us_gold_value_bn,
    ROUND((us_gold_value_bn / us_total_reserves_bn) * 100, 2) AS us_gold_share_of_total,
    world_gdp_bn,
    us_gdp_share_pct,
    ROUND(us_gdp_bn, 2) AS us_gdp_bn,
    CASE
        WHEN usd_share_drawdown_pct < -2 THEN 'Rapid Decline'
        WHEN usd_share_drawdown_pct >= -2 AND usd_share_drawdown_pct < 0 THEN 'Gradual Decline'
        WHEN usd_share_drawdown_pct = 0 THEN 'Stable'
        ELSE 'Growing'
    END AS usd_trend
FROM
    fact_usd_dominance
WHERE
    year >= 2010
ORDER BY
    year DESC;

-- ============================================================================
-- QUERY 7: Regional Gold Accumulation Breakdown
-- ============================================================================
-- Purpose: Aggregate gold buying behavior by geographic region
--          Identify regional patterns in reserve diversification
-- Use Case: Understand geopolitical blocs' collective strategies
-- ============================================================================

SELECT
    dc.geo_bloc,
    dc.region,
    COUNT(DISTINCT dc.country_code) AS num_countries,
    COUNT(DISTINCT fgr.year) AS years_in_data,
    SUM(CASE WHEN fgr.is_accumulating THEN 1 ELSE 0 END) AS total_accumulating_years,
    COUNT(*) - SUM(CASE WHEN fgr.is_accumulating THEN 1 ELSE 0 END) AS total_non_accumulating_years,
    ROUND(AVG(fgr.gold_share_pct), 2) AS avg_gold_share_pct,
    ROUND(AVG(fgr.gold_yoy_change_pct), 2) AS avg_yoy_change_pct,
    SUM(fgr.gold_value_usd) AS total_regional_gold_value_usd,
    MAX(fgr.year) AS latest_year,
    ROUND(
        SUM(CASE WHEN fgr.is_accumulating THEN 1 ELSE 0 END)::NUMERIC /
        NULLIF(COUNT(*), 0) * 100, 2
    ) AS accumulation_frequency_pct
FROM
    fact_gold_reserves fgr
    INNER JOIN dim_country dc ON fgr.country_code = dc.country_code
WHERE
    fgr.year >= 2015
GROUP BY
    dc.geo_bloc,
    dc.region
HAVING
    COUNT(DISTINCT fgr.year) > 0
ORDER BY
    total_regional_gold_value_usd DESC,
    accumulation_frequency_pct DESC;

-- ============================================================================
-- QUERY 8: Countries That Reversed from Selling to Buying (Momentum Shift)
-- ============================================================================
-- Purpose: Identify policy reversals - countries that stopped selling gold
--          and started accumulating (strategic inflection points)
-- Use Case: Detect major shifts in central bank behavior and monetary policy
-- ============================================================================

WITH selling_periods AS (
    SELECT
        fgr.country_code,
        dc.country_name,
        fgr.year,
        fgr.gold_yoy_change_pct,
        fgr.is_accumulating,
        LAG(fgr.is_accumulating) OVER (
            PARTITION BY fgr.country_code ORDER BY fgr.year
        ) AS prev_is_accumulating,
        LAG(fgr.gold_yoy_change_pct) OVER (
            PARTITION BY fgr.country_code ORDER BY fgr.year
        ) AS prev_yoy_change
    FROM
        fact_gold_reserves fgr
        INNER JOIN dim_country dc ON fgr.country_code = dc.country_code
    WHERE
        fgr.year >= 2010
)
SELECT
    country_code,
    country_name,
    year,
    gold_yoy_change_pct,
    is_accumulating,
    prev_is_accumulating,
    prev_yoy_change,
    CASE
        WHEN prev_is_accumulating = FALSE AND is_accumulating = TRUE THEN 'Sell→Buy Reversal'
        WHEN is_accumulating = TRUE AND prev_yoy_change > 0 THEN 'Continued Buying'
        ELSE 'Other'
    END AS momentum_event
FROM
    selling_periods
WHERE
    (prev_is_accumulating = FALSE AND is_accumulating = TRUE)
    OR (prev_is_accumulating = TRUE AND is_accumulating = FALSE)
ORDER BY
    year DESC,
    country_code ASC;

-- ============================================================================
-- QUERY 9: ML Prediction Leaderboard for 2026 with Confidence Tiers
-- ============================================================================
-- Purpose: Display top predicted gold accumulators for 2026 with component scores
--          Assess confidence based on consistency and geopolitical factors
-- Use Case: Forward-looking analysis, investment thesis validation
-- ============================================================================

SELECT
    mp.country_code,
    dc.country_name,
    dc.geo_bloc,
    mp.gold_accumulation_score,
    CASE
        WHEN mp.gold_accumulation_score >= 85 THEN 'Very High'
        WHEN mp.gold_accumulation_score >= 70 THEN 'High'
        WHEN mp.gold_accumulation_score >= 55 THEN 'Medium'
        WHEN mp.gold_accumulation_score >= 40 THEN 'Low'
        ELSE 'Very Low'
    END AS confidence_tier,
    mp.pillar_momentum,
    mp.pillar_consistency,
    mp.pillar_geo,
    mp.pillar_alloc,
    mp.sanctions_bonus,
    mp.gold_share_pct,
    mp.gold_tonnes_yoy,
    mp.accumulation_streak,
    mp.geo_risk_tier,
    ROUND(
        (mp.pillar_momentum + mp.pillar_consistency + mp.pillar_geo + mp.pillar_alloc) / 4.0,
        2
    ) AS avg_pillar_score,
    CASE
        WHEN mp.pillar_consistency >= 75 THEN 'Very Consistent'
        WHEN mp.pillar_consistency >= 60 THEN 'Consistent'
        ELSE 'Volatile'
    END AS behavior_consistency
FROM
    ml_predictions mp
    INNER JOIN dim_country dc ON mp.country_code = dc.country_code
WHERE
    mp.prediction_year = 2026
ORDER BY
    mp.gold_accumulation_score DESC
LIMIT 20;

-- ============================================================================
-- QUERY 10: Countries Where Gold Share > 50% of Reserves (Gold-Heavy Portfolio)
-- ============================================================================
-- Purpose: Identify countries with concentrated gold holdings
--          Unusual because most modern reserves are diversified
-- Use Case: Risk analysis, historical perspective, policy examination
-- ============================================================================

SELECT
    dc.country_code,
    dc.country_name,
    dc.geo_bloc,
    dc.region,
    fgr.year,
    fgr.total_reserves_usd,
    fgr.gold_value_usd,
    fgr.gold_share_pct,
    fgr.reserves_excl_gold_usd,
    fgr.accumulation_streak,
    fgr.gold_rank,
    COUNT(*) OVER (
        PARTITION BY fgr.country_code
        ORDER BY fgr.year
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS consecutive_years_gold_heavy,
    LAG(fgr.gold_share_pct) OVER (
        PARTITION BY fgr.country_code ORDER BY fgr.year
    ) AS previous_year_gold_share,
    ROUND(
        fgr.gold_share_pct - LAG(fgr.gold_share_pct) OVER (
            PARTITION BY fgr.country_code ORDER BY fgr.year
        ), 2
    ) AS share_change_pct
FROM
    fact_gold_reserves fgr
    INNER JOIN dim_country dc ON fgr.country_code = dc.country_code
WHERE
    fgr.gold_share_pct > 50
    AND fgr.year >= 2000
ORDER BY
    fgr.year DESC,
    fgr.gold_share_pct DESC,
    dc.country_name ASC;

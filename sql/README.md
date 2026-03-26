# Gold Reserve Platform - PostgreSQL Database Layer

Professional-grade PostgreSQL database schema and analytical queries for the gold reserve analysis platform.

## Overview

This database layer provides a normalized, well-indexed data warehouse design optimized for:
- Time-series analysis of gold reserves
- Geopolitical risk assessment
- Machine learning scoring and predictions
- Complex analytical queries

## Files

### 1. `schema.sql` - Database Schema (306 lines)

Complete PostgreSQL schema with:

#### Dimension Tables
- **`dim_country`** - Static country master data with geographic classifications

#### Fact Tables (Time-Series)
- **`fact_gold_reserves`** - Core gold holdings and reserve composition by country-year
- **`fact_usd_dominance`** - Global USD share metrics and world gold valuations
- **`fact_geopolitical`** - UN alignment, sanctions, and geopolitical risk scores
- **`fact_master_panel`** - Denormalized comprehensive fact table combining all metrics
- **`ml_predictions`** - ML model predictions with component scores and feature importance

#### Analytical Views
- **`v_top_accumulators`** - Ranked top gold-buying countries with all key metrics

#### Features
- Proper PRIMARY KEYS on all tables
- FOREIGN KEY constraints ensuring referential integrity
- UNIQUE constraints on (country_code, year) pairs where applicable
- NOT NULL constraints on critical dimensions
- CHECK constraints for data validation (year ranges, percentage bounds)
- Strategic indexes on frequently queried columns:
  - country_code, year combinations
  - accumulation flags and status columns
  - gold_share_pct for ranking queries
  - geo_bloc for regional analysis
- Automatic timestamp tracking (created_at, updated_at)

### 2. `queries.sql` - Analytical Queries (447 lines)

10 production-ready SQL queries demonstrating advanced analytics:

#### Query 1: Top 10 Gold Accumulators (2020-2025)
- Identifies major gold buyers in the post-pandemic/de-dollarization era
- Shows total gold added, accumulation frequency, and streaks
- Sorted by total gold value added

#### Query 2: De-Dollarization Signal
- Countries buying gold while USD is declining
- Uses CTE to identify USD decline years
- Classifies strategies as "Strategic De-Dollar" vs "Market Opportunistic"
- Includes geopolitical context (UN divergence, sanctions)

#### Query 3: G20 Gold Share Trends
- Tracks reserve composition changes among major economies
- Year-over-year percentage changes
- Ranking by gold share within each year
- Enables comparison of central bank policies

#### Query 4: Sanctions-Driven Gold Buying
- Identifies sanctioned nations increasing gold reserves
- Composite risk scoring combining sanctions, gold purchases, and UN divergence
- Classification tiers: "High Risk Accumulator", "Sanctioned Buyer", etc.

#### Query 5: Gold Purchase Acceleration (3-Year Momentum)
- Detects accelerating buying behavior (trend indicator)
- Lag comparisons for acceleration measurement
- Classifies trends: "Strong Consistent", "Accelerating", "Modest Growth", "Declining"

#### Query 6: USD Dominance Trends
- Global USD share decline tracking by year
- Includes world GDP context and US reserve holdings
- Classification of decline rates (Rapid/Gradual/Stable/Growing)

#### Query 7: Regional Gold Accumulation
- Aggregates by geographic bloc and region
- Shows accumulation frequency percentage
- Ranks regions by total gold value held

#### Query 8: Sell-to-Buy Reversals
- Policy inflection points where countries stopped selling/started buying
- Momentum shift detection using lag comparisons
- Historical perspective on strategic changes

#### Query 9: ML Prediction Leaderboard (2026)
- Forward-looking predictions with confidence tiers
- Component pillar scores (momentum, consistency, geo, allocation)
- Behavioral consistency assessment
- Top 20 predicted accumulators

#### Query 10: Gold-Heavy Portfolios (>50% Gold)
- Identifies concentrated gold holdings (unusual in modern reserves)
- Tracks consecutive years of gold-heavy status
- Shows historical shifts in portfolio composition

## Features

### Schema Design Principles
- **Star Schema** - Fact tables with foreign keys to dimensions
- **Normalization** - Eliminates redundancy while maintaining query performance
- **Denormalization** - Master panel combines key metrics for efficiency
- **Temporal** - Year-based fact tables support time-series analysis
- **Indexing Strategy** - Covers common query patterns (country+year, year alone, rankings)

### Data Quality
- CHECK constraints validate ranges for percentages and scores (0-100)
- Year constraints ensure data quality (2000-2100 range)
- Non-negative value constraints on financial data
- UNIQUE constraints prevent duplicate country-year combinations

### Query Optimization
- CTEs (Common Table Expressions) for readable, maintainable complex queries
- Window functions for ranking and trending
- Strategic JOINs with indexed lookup tables
- Aggregation functions with HAVING clauses for filtering

## Loading Data

### Using `load_to_postgres.py`

```bash
# Set environment variable
export DATABASE_URL="postgresql://user:password@localhost:5432/gold_reserve"

# Run the loader
python3 src/db/load_to_postgres.py
```

**Note**: Ensure the database is created and `schema.sql` has been executed first:
```bash
psql -U user -d gold_reserve -f sql/schema.sql
```

### Data Sources Loaded

1. **master_panel_nlp.csv** → `fact_master_panel`
   - Master panel with all integrated metrics and NLP features
   - Rows: 1000+ country-years

2. **ml_country_scores.csv** → `ml_predictions`
   - ML model predictions for gold accumulation propensity
   - Rows: 100+ countries with prediction scores

### Upsert Logic

The loader implements INSERT ... ON CONFLICT DO UPDATE:
- Unique constraint: (country_code, year) or (country_code, prediction_year)
- Updates existing records with new data
- Maintains automatic timestamps (created_at, updated_at)
- Batch processing for performance (1000 rows per batch)

## Portfolio Value

This database layer demonstrates:

### Data Engineering Excellence
- Professional schema design with proper normalization
- Comprehensive indexing strategy for production systems
- Batch upsert logic with conflict handling
- Proper error handling and logging in Python loader

### SQL Mastery
- Complex window functions and CTEs
- Multi-table JOINs with date-based filtering
- Aggregate functions with grouping and filtering
- Ranking and lag/lead for trend analysis
- Classification logic within queries (CASE WHEN)

### Business Intelligence
- 10 distinct analytical use cases
- Clear query documentation for stakeholders
- Scalable design supporting growth to 100K+ rows
- Geopolitical and financial intelligence queries

## Performance Considerations

### Indexes
- `idx_fact_gold_reserves_country_year` - Most common query pattern
- `idx_fact_gold_reserves_year` - Time-based filtering
- `idx_fact_gold_reserves_accumulating` - Boolean status queries
- `idx_fact_gold_reserves_gold_share` - Ranking queries (DESC order)
- `idx_fact_master_panel_*` - Multiple indexes for comprehensive queries

### Query Optimization Tips

1. **Use JOINs with indexed columns**: country_code, year
2. **Filter early**: WHERE clauses on indexed columns
3. **Aggregate efficiently**: GROUP BY on low-cardinality columns
4. **Consider partitioning**: By year for very large datasets
5. **Monitor with EXPLAIN ANALYZE**: Identify slow queries

## Maintenance

### Regular Tasks
```bash
# Vacuum to maintain index efficiency
VACUUM ANALYZE fact_gold_reserves;
VACUUM ANALYZE fact_master_panel;

# Check index sizes
SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Data Updates
Use the provided `load_to_postgres.py` script which handles:
- Duplicate key detection
- Update vs insert decisions
- Transactional consistency
- Batch processing for performance

## Example Usage

### Connect to Database
```bash
psql -U user -d gold_reserve -h localhost
```

### View Top Accumulators
```sql
SELECT * FROM v_top_accumulators LIMIT 10;
```

### Get Recent Year Data
```sql
SELECT country_code, country_name, gold_share_pct, accumulation_streak
FROM fact_gold_reserves
WHERE year = 2025
ORDER BY gold_value_usd DESC;
```

### Check ML Predictions
```sql
SELECT * FROM ml_predictions
WHERE prediction_year = 2026
AND gold_accumulation_score > 80
ORDER BY gold_accumulation_score DESC;
```

## Dependencies

### PostgreSQL (Database)
- Version: 12.0 or higher
- Extensions: None required

### Python (Data Loading)
- psycopg2: PostgreSQL adapter
- sqlalchemy: SQL toolkit
- pandas: Data manipulation
- python-dotenv: Environment variables

Install with:
```bash
pip install psycopg2-binary sqlalchemy pandas python-dotenv
```

## Security Considerations

1. **Connection String**: Store DATABASE_URL in `.env` (never commit)
2. **Row-Level Security**: Can be added for multi-tenant support
3. **Audit Trails**: created_at/updated_at timestamps enable change tracking
4. **Constraints**: Prevent invalid data insertion at database level
5. **User Permissions**: Apply least-privilege access (GRANT SELECT for read users)

## Future Enhancements

1. **Materialized Views**: Pre-aggregate common queries for speed
2. **Partitioning**: By year for fact tables (improves query speed)
3. **Triggers**: Automatic validation and cascade updates
4. **Change Data Capture**: Track all modifications for auditing
5. **Time Series Extensions**: timescaledb for advanced temporal queries
6. **Archive Tables**: Move historical data (pre-2015) to separate storage

## Contact & Support

For questions about:
- Schema design: Review CREATE TABLE statements with column comments
- Query performance: Use EXPLAIN ANALYZE on the query
- Data loading: Check load_to_postgres.py logs for detailed messages

---

**Created**: March 2026
**Version**: 1.0
**Status**: Production-Ready

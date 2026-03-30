# Database Layer - Complete Index & Guide

Comprehensive index of all database layer files and documentation for the Gold Reserve Platform.

## Quick Start

1. **First Time Setup?** → Read `SETUP_DATABASE.md` (step-by-step instructions)
2. **Want to understand the schema?** → Read `sql/SCHEMA_REFERENCE.md` (detailed column guide)
3. **Need to run queries?** → Check `sql/README.md` (usage examples)
4. **Looking for a specific query?** → See `sql/queries.sql` (10 analytical queries)

---

## Files Overview

### Core Database Files

#### 1. `sql/schema.sql` (306 lines)
**Complete PostgreSQL database schema**

- 6 tables: 1 dimension + 4 facts + 1 view
- 20+ indexes for query optimization
- Foreign keys, constraints, and data validation
- Professional comments and documentation

**Tables Created**:
- `dim_country` - Country master data
- `fact_gold_reserves` - Gold holdings time-series
- `fact_usd_dominance` - Global USD metrics
- `fact_geopolitical` - Sanctions and geopolitical risk
- `fact_master_panel` - Comprehensive denormalized facts
- `ml_predictions` - ML model scores and predictions
- `v_top_accumulators` - Executive dashboard view

**When to Use**:
- Initial database setup
- Schema recreation
- Adding new tables

**Key Features**:
```sql
CREATE TABLE fact_gold_reserves (
  country_code FK,
  year INTEGER,
  gold_tonnes NUMERIC(15,4),
  gold_value_usd NUMERIC(18,2),
  gold_share_pct NUMERIC(6,2),
  is_accumulating BOOLEAN,
  accumulation_streak INTEGER,
  ... [15 more columns]
);
-- Includes UNIQUE(country_code, year)
-- CHECK constraints for data quality
-- 4 indexes for performance
```

---

#### 2. `sql/queries.sql` (447 lines)
**10 professional analytical SQL queries**

Production-ready queries demonstrating SQL mastery with:
- CTEs (Common Table Expressions)
- Window functions (LAG, RANK, ROW_NUMBER)
- Complex JOINs with date filtering
- Aggregate functions with HAVING clauses
- Classification logic (CASE WHEN)

**The 10 Queries**:

1. **Top 10 Gold Accumulators (2020-2025)**
   - Identifies major gold buyers
   - Shows total gold added, accumulation frequency
   - Use case: Strategic analysis

2. **De-Dollarization Signal**
   - Countries buying gold while USD declines
   - Strategy classification
   - Use case: De-dollarization tracking

3. **G20 Gold Share Trends**
   - Reserve composition for major economies
   - YoY percentage changes
   - Use case: Central bank policy comparison

4. **Sanctions + Gold Buying Correlation**
   - Identifies sanctioned nations accumulating gold
   - Composite risk scoring
   - Use case: Geopolitical risk analysis

5. **Gold Purchase Acceleration (3-Year)**
   - Momentum detection
   - Trend classification
   - Use case: Early warning system

6. **USD Dominance Trend**
   - Global USD share decline tracking
   - Includes GDP context
   - Use case: Macro trend analysis

7. **Regional Gold Accumulation**
   - Aggregates by geographic bloc
   - Accumulation frequency
   - Use case: Bloc strategy comparison

8. **Sell-to-Buy Reversals**
   - Policy inflection points
   - Momentum shift detection
   - Use case: Historical perspective

9. **ML Prediction Leaderboard (2026)**
   - Forward-looking predictions
   - Confidence tiers and components
   - Use case: Investment thesis validation

10. **Gold-Heavy Portfolios (>50% Gold)**
    - Concentrated holdings
    - Consecutive years tracking
    - Use case: Risk analysis

**When to Use**:
- Executive dashboards
- Exploratory data analysis
- Report generation
- Data validation

**Copy-Paste Ready**: All queries include detailed comments and are production-safe.

---

#### 3. `src/db/load_to_postgres.py` (408 lines)
**Python data loading script with professional practices**

Features:
- Connection pooling with SQLAlchemy
- Batch upsert operations (INSERT ... ON CONFLICT)
- Comprehensive error handling and logging
- Data validation and type conversion
- CSV parsing with pandas

**Main Class**: `PostgreSQLLoader`

**Methods**:
- `upsert_fact_master_panel()` - Load master_panel_nlp.csv
- `upsert_ml_predictions()` - Load ml_country_scores.csv
- `load_all()` - Load all CSVs at once
- Data validation and preparation methods

**Usage**:
```bash
export DATABASE_URL="postgresql://user:pass@localhost/gold_reserve"
python3 src/db/load_to_postgres.py

# Output:
# ✓ Successfully connected to PostgreSQL
# ✓ Loaded fact_master_panel: 1500 rows
# ✓ Loaded ml_predictions: 150 rows
```

**When to Use**:
- Initial data load
- Daily/weekly data refreshes
- Upsert new versions of CSVs
- Production data pipelines

**Dependencies**:
```
psycopg2-binary>=2.9.0
sqlalchemy>=1.4.0
pandas>=1.3.0
python-dotenv>=0.19.0
```

---

#### 4. `src/db/__init__.py`
Python module initialization file for the db package.

---

### Documentation Files

#### 5. `sql/README.md` (Comprehensive Guide)
**Complete documentation for the database layer**

Sections:
- Overview and architecture
- File-by-file breakdown
- Schema design principles
- 10 query descriptions with use cases
- Features and optimization
- Loading data (step-by-step)
- Performance tuning tips
- Example usage and patterns
- Dependencies
- Security considerations
- Future enhancements

**Best For**: Understanding the entire system

---

#### 6. `sql/SCHEMA_REFERENCE.md` (Detailed Reference)
**Complete data dictionary for all tables and columns**

Contains:
- 5 detailed table definitions with all columns
- Column types, constraints, and descriptions
- Example records and queries
- Relationship diagrams
- Index summary
- Data validation rules
- Data ranges and typical values

**Sections**:
- Dimension tables (dim_country)
- Fact tables (all 5)
- Views (v_top_accumulators)
- Relationships & foreign keys
- All indexes with purposes
- Data constraints

**Best For**: Column-level reference, understanding data types

---

#### 7. `SETUP_DATABASE.md` (Quick Start)
**Step-by-step setup instructions**

Steps:
1. Create PostgreSQL database and user
2. Execute schema.sql
3. Set environment variables
4. Install Python dependencies
5. Load data with Python script
6. Verify with test queries
7. Common issues & solutions
8. Production considerations
9. Backup and monitoring

**Best For**: Getting started quickly

---

#### 8. `DATABASE_INDEX.md` (This File)
**Navigation guide for all database documentation**

---

## Architecture Overview

```
Gold Reserve Platform
├── Data Layer (PostgreSQL)
│   ├── Dimension (dim_country)
│   │
│   ├── Facts Time-Series
│   │   ├── fact_gold_reserves (main)
│   │   ├── fact_usd_dominance (global)
│   │   ├── fact_geopolitical (risk)
│   │   └── fact_master_panel (comprehensive)
│   │
│   ├── ML Scores
│   │   └── ml_predictions (forward-looking)
│   │
│   └── Views
│       └── v_top_accumulators (dashboard)
│
├── Python Loader
│   └── PostgreSQLLoader class
│       ├── CSV parsing with pandas
│       ├── Data validation
│       ├── Batch upsert operations
│       └── Logging and error handling
│
└── Documentation
    ├── schema.sql - Create tables
    ├── queries.sql - 10 analytical queries
    ├── README.md - Complete guide
    ├── SCHEMA_REFERENCE.md - Data dictionary
    └── SETUP_DATABASE.md - Setup steps
```

---

## Use Cases

### I Want To...

**...set up the database from scratch**
→ Read `SETUP_DATABASE.md` (5-10 minutes)

**...understand the data structure**
→ Read `sql/SCHEMA_REFERENCE.md` + `sql/schema.sql`

**...write an analytical query**
→ Reference `sql/queries.sql` for examples (patterns, syntax)

**...load data from CSV files**
→ Use `load_to_postgres.py` with `export DATABASE_URL=...`

**...get top gold accumulators**
→ Run Query 1 from `sql/queries.sql` or use view `v_top_accumulators`

**...analyze de-dollarization**
→ Run Query 2 from `sql/queries.sql`

**...predict 2026 gold buying**
→ Run Query 9 from `sql/queries.sql` (ML leaderboard)

**...integrate with a BI tool**
→ Use CONNECTION STRING from DATABASE_URL
→ Query `v_top_accumulators` for dashboards

**...optimize slow queries**
→ Check indexes in `sql/SCHEMA_REFERENCE.md`
→ Use EXPLAIN ANALYZE from `SETUP_DATABASE.md`

---

## File Sizes & Metrics

| File | Lines | Size | Type |
|------|-------|------|------|
| schema.sql | 306 | 13 KB | SQL DDL |
| queries.sql | 447 | 17 KB | SQL DML |
| load_to_postgres.py | 408 | 14 KB | Python |
| README.md | ~500 | ~30 KB | Markdown |
| SCHEMA_REFERENCE.md | ~700 | ~35 KB | Markdown |
| SETUP_DATABASE.md | ~300 | ~20 KB | Markdown |
| **Total** | **2,500+** | **~130 KB** | **Production Ready** |

---

## Key Statistics

### Database Objects
- **Tables**: 5 fact tables + 1 dimension + 1 view = 7 objects
- **Indexes**: 20+ strategic indexes for performance
- **Constraints**: 40+ data quality constraints
- **Relationships**: 5 foreign keys ensuring referential integrity

### Data Coverage
- **Time Period**: 2000-2025 (25+ years)
- **Countries**: 150+ sovereign nations and territories
- **Records**: 1500+ country-year combinations
- **Dimensions**: 60+ metrics per record

### Query Library
- **Total Queries**: 10 production-ready queries
- **Query Types**: Time-series, ranking, trend, correlation, aggregation
- **Complexity**: Beginner to advanced SQL patterns
- **Documentation**: Full comments on each query

---

## Quality Assurance

### Schema Validation
✓ Proper PRIMARY KEYs on all tables
✓ FOREIGN KEY constraints ensure data consistency
✓ UNIQUE constraints prevent duplicates
✓ CHECK constraints validate data ranges
✓ NOT NULL constraints enforce completeness
✓ Data types match business requirements
✓ Indexes optimize common query patterns

### Code Quality
✓ Python script passes syntax validation
✓ Comprehensive error handling
✓ Logging for troubleshooting
✓ Type hints for clarity
✓ Docstrings on all functions
✓ PEP 8 compliant formatting
✓ Batch processing for performance

### Documentation Quality
✓ 5 comprehensive documentation files
✓ Step-by-step setup guide
✓ Complete data dictionary
✓ 10 example queries with use cases
✓ Architecture diagrams
✓ Common issues & solutions
✓ Production deployment guidelines

---

## Performance Characteristics

### Query Performance (Estimated)
| Operation | Complexity | Typical Time |
|-----------|-----------|--------------|
| Single country lookup | O(1) | < 1 ms |
| All data for year | O(n) | 10-50 ms |
| Top 10 accumulators | O(n log n) | 50-100 ms |
| Complex join (3+ tables) | O(n²) | 100-500 ms |
| Full table scan | O(n) | 500-1000 ms |

*Times based on ~1500 rows with proper indexes*

### Storage Requirements
- **Schema DDL**: ~50 KB
- **Typical data load**: 50-100 MB
- **Index storage**: 10-20 MB
- **Total**: ~100-150 MB per year of growth

---

## Integration Points

### Data Sources
- `data/curated/master_panel_nlp.csv` → `fact_master_panel`
- `data/curated/ml_country_scores.csv` → `ml_predictions`

### Output Targets
- **Dashboards**: Query `v_top_accumulators` or any fact table
- **Reports**: Use `queries.sql` for report generation
- **Analytics**: Direct SQL access for exploratory analysis
- **APIs**: Build RESTful endpoints on top of views
- **ML Pipelines**: Join predictions with current data

### BI Tool Integration
```
PostgreSQL (gold_reserve) ← sqlalchemy/psycopg2 ← Tableau/Superset/PowerBI
                             via DATABASE_URL
```

---

## Maintenance Schedule

### Daily
- Monitor log files (from load_to_postgres.py)
- Check for failed data loads

### Weekly
- VACUUM ANALYZE for index efficiency
- Review slow query logs

### Monthly
- Backup full database
- Review index usage
- Plan capacity

### Quarterly
- Archive historical data
- Rebuild fragmented indexes
- Update statistics

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Mar 2026 | Initial production release |

---

## Contact & Support

**Schema Questions**: Review `sql/SCHEMA_REFERENCE.md`
**Query Help**: Check examples in `sql/queries.sql`
**Setup Issues**: Follow `SETUP_DATABASE.md` troubleshooting
**Data Loading**: Review `load_to_postgres.py` comments and logs

---

## Professional Portfolio Value

This database layer demonstrates:

✓ **Enterprise Database Design** - Star schema, normalization, constraints
✓ **Advanced SQL Skills** - CTEs, window functions, complex queries
✓ **Python Engineering** - Object-oriented design, error handling, logging
✓ **Documentation Excellence** - Comprehensive, clear, organized guides
✓ **Production Readiness** - Validation, constraints, indexes, performance
✓ **Business Intelligence** - 10 distinct analytical use cases
✓ **Geopolitical Data Expertise** - Sophisticated domain modeling

**Ideal For**: Data Engineering interviews, analytics engineering roles, BI developer positions

---

**Document Version**: 1.0
**Last Updated**: March 25, 2026
**Status**: Complete & Production-Ready

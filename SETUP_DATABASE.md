# Database Setup Guide - Gold Reserve Platform

Quick-start guide for setting up the PostgreSQL database layer.

## Prerequisites

- PostgreSQL 12+ installed and running
- Python 3.7+
- pip package manager

## Step 1: Create Database and User

```bash
# Connect to PostgreSQL as superuser
psql -U postgres

# In psql shell:
CREATE DATABASE gold_reserve;
CREATE USER gold_admin WITH PASSWORD 'your_secure_password';
ALTER ROLE gold_admin WITH CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE gold_reserve TO gold_admin;
\q
```

## Step 2: Create Schema

```bash
# Connect as the new user
psql -U gold_admin -d gold_reserve -h localhost

# Execute schema file
\i sql/schema.sql

# Verify tables were created
\dt
\dv

# Exit psql
\q
```

## Step 3: Set Environment Variables

Create or update `.env` file in project root:

```bash
# .env
DATABASE_URL="postgresql://gold_admin:your_secure_password@localhost:5432/gold_reserve"
```

Or set as shell environment variable:

```bash
export DATABASE_URL="postgresql://gold_admin:your_secure_password@localhost:5432/gold_reserve"
```

## Step 4: Install Python Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Or manually:
pip install psycopg2-binary sqlalchemy pandas python-dotenv
```

## Step 5: Load Data

```bash
# From project root
python3 src/db/load_to_postgres.py

# Expected output:
# 2026-03-25 21:45:00 - __main__ - INFO - Successfully connected to PostgreSQL database
# 2026-03-25 21:45:01 - __main__ - INFO - Loading data from: data/curated
# 2026-03-25 21:45:02 - __main__ - INFO - Prepared master_panel_nlp: 1500 rows
# 2026-03-25 21:45:03 - __main__ - INFO - Successfully upserted 1500 rows into fact_master_panel
# 2026-03-25 21:45:03 - __main__ - INFO - Prepared ml_predictions: 150 rows
# 2026-03-25 21:45:03 - __main__ - INFO - Successfully upserted 150 rows into ml_predictions
```

## Step 6: Verify Data Load

```bash
psql -U gold_admin -d gold_reserve -h localhost

-- Check row counts
SELECT COUNT(*) as fact_master_panel_count FROM fact_master_panel;
SELECT COUNT(*) as ml_predictions_count FROM ml_predictions;

-- View top accumulators
SELECT * FROM v_top_accumulators LIMIT 5;

-- Run a sample query
SELECT country_code, country_name, year, gold_share_pct
FROM fact_gold_reserves
WHERE year = 2025
ORDER BY gold_value_usd DESC
LIMIT 10;

\q
```

## Testing Queries

Run the analytical queries from `sql/queries.sql`:

```bash
# In psql:
psql -U gold_admin -d gold_reserve -h localhost < sql/queries.sql

# Or execute individual queries:
psql -U gold_admin -d gold_reserve -c "
  SELECT country_code, country_name, geo_bloc
  FROM v_top_accumulators
  LIMIT 10;
"
```

## Common Issues & Solutions

### Connection Refused

```
Error: could not translate host name "localhost" to address
```

**Solution**:
- Verify PostgreSQL is running: `pg_isready -h localhost`
- Check host parameter in DATABASE_URL (use `localhost` or `127.0.0.1`)
- Verify port 5432 is open

### Authentication Failed

```
FATAL: Ident authentication failed for user "gold_admin"
```

**Solution**:
- Check `/etc/postgresql/[version]/main/pg_hba.conf` has `md5` or `scram-sha-256` for local connections
- Use `psql -U gold_admin -h 127.0.0.1 -d gold_reserve` (force TCP connection)

### Schema Already Exists

```
ERROR: table "dim_country" already exists
```

**Solution**:
- The schema.sql file includes DROP commands
- Re-run: `psql -U gold_admin -d gold_reserve -f sql/schema.sql`
- Or delete and recreate database: `DROP DATABASE gold_reserve;`

### Data Load Fails

```
KeyError or ValueError in load_to_postgres.py
```

**Solution**:
- Check CSV files exist in `data/curated/`
- Verify column names match those in the script
- Check `requirements.txt` dependencies are installed
- Run with verbose logging: Add `logging.DEBUG` to script

## Production Considerations

### Security Hardening

```sql
-- Create read-only user for dashboards
CREATE USER dashboard_user WITH PASSWORD 'dashboard_password';
GRANT CONNECT ON DATABASE gold_reserve TO dashboard_user;
GRANT USAGE ON SCHEMA public TO dashboard_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dashboard_user;
GRANT SELECT ON ALL VIEWS IN SCHEMA public TO dashboard_user;

-- Revoke public schema permissions
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE gold_reserve FROM PUBLIC;
```

### Backup Strategy

```bash
# Daily backup
pg_dump -U gold_admin -d gold_reserve -Fc > backups/gold_reserve_$(date +%Y%m%d).dump

# Restore from backup
pg_restore -U gold_admin -d gold_reserve -Fc backups/gold_reserve_20260325.dump
```

### Performance Tuning

```sql
-- Rebuild indexes after large data loads
REINDEX TABLE fact_gold_reserves;
REINDEX TABLE fact_master_panel;

-- Vacuum to reclaim space
VACUUM ANALYZE;

-- Check query plans
EXPLAIN ANALYZE
SELECT * FROM v_top_accumulators LIMIT 10;
```

### Monitoring

```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check active connections
SELECT * FROM pg_stat_activity WHERE datname = 'gold_reserve';

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## Next Steps

1. **Connect Dashboard**: Update your BI tool (Tableau, Superset, etc.) with DATABASE_URL
2. **Schedule Data Loads**: Use cron or Airflow to run `load_to_postgres.py` daily
3. **Add Monitoring**: Set up database monitoring (pg_stat_statements, alerting)
4. **Version Control**: Commit schema and queries to git, exclude .env file
5. **Documentation**: Update your data dictionary and query documentation

## Resources

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- psycopg2 Guide: https://www.psycopg.org/
- SQL Best Practices: https://wiki.postgresql.org/wiki/Performance_Optimization

---

**Last Updated**: March 2026
**Database Version**: PostgreSQL 12+
**Schema Version**: 1.0

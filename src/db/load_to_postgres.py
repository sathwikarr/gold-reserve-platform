#!/usr/bin/env python3
"""
Gold Reserve Platform - PostgreSQL Data Loader

This module provides functionality to load curated CSV data into PostgreSQL tables.
Handles upsert operations with proper conflict resolution and provides detailed logging.

Dependencies:
    - psycopg2: PostgreSQL adapter for Python
    - sqlalchemy: SQL toolkit and ORM
    - pandas: Data manipulation library
    - python-dotenv: Environment variable management

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (format: postgresql://user:password@host:port/dbname)

Usage:
    python load_to_postgres.py
"""

import os
import sys
import logging
from typing import Dict, Tuple
from pathlib import Path
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_batch, execute_values
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    sys.exit(1)


class PostgreSQLLoader:
    """
    Handles loading and upserting data from CSV files into PostgreSQL.

    This class manages database connections, CSV parsing, and bulk insert/upsert
    operations with comprehensive error handling and logging.
    """

    def __init__(self, database_url: str):
        """
        Initialize the PostgreSQL loader.

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self.engine = None
        self.connection = None
        self._connect()

    def _connect(self) -> None:
        """
        Establish connection to PostgreSQL database.

        Raises:
            SystemExit: If connection fails
        """
        try:
            self.engine = create_engine(
                self.database_url,
                poolclass=NullPool,
                echo=False
            )
            self.connection = self.engine.connect()
            logger.info("Successfully connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            sys.exit(1)

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def _validate_dataframe(self, df: pd.DataFrame, table_name: str) -> bool:
        """
        Validate DataFrame before loading.

        Args:
            df: DataFrame to validate
            table_name: Target table name

        Returns:
            True if valid, False otherwise
        """
        if df.empty:
            logger.warning(f"DataFrame for {table_name} is empty")
            return False

        logger.info(f"Validated {table_name}: {len(df)} rows, {len(df.columns)} columns")
        return True

    def _prepare_fact_master_panel(self, csv_path: str) -> pd.DataFrame:
        """
        Load and prepare master_panel_nlp.csv for database insertion.

        Performs:
        - Data type conversion and validation
        - NULL handling for missing values
        - Column name validation

        Args:
            csv_path: Path to master_panel_nlp.csv

        Returns:
            Prepared DataFrame
        """
        logger.info(f"Loading master_panel_nlp.csv from {csv_path}")
        df = pd.read_csv(csv_path)

        # Ensure required columns exist
        required_cols = ['country', 'country_code', 'year']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return pd.DataFrame()

        # Data type conversions
        df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
        numeric_columns = [col for col in df.columns if col not in ['country', 'country_code', 'geo_bloc']]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Rename 'country' to match schema (if needed)
        if 'country' in df.columns:
            df = df.rename(columns={'country': 'country_name'})

        logger.info(f"Prepared master_panel_nlp: {len(df)} rows")
        return df

    def _prepare_ml_predictions(self, csv_path: str) -> pd.DataFrame:
        """
        Load and prepare ml_country_scores.csv for database insertion.

        Performs:
        - Data type conversion
        - Rename prediction_year column (prediction_year or year)
        - Score validation

        Args:
            csv_path: Path to ml_country_scores.csv

        Returns:
            Prepared DataFrame
        """
        logger.info(f"Loading ml_country_scores.csv from {csv_path}")
        df = pd.read_csv(csv_path)

        # Ensure required columns exist
        required_cols = ['country', 'country_code']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return pd.DataFrame()

        # Standardize prediction_year column
        if 'year' in df.columns and 'prediction_year' not in df.columns:
            df = df.rename(columns={'year': 'prediction_year'})
        elif 'prediction_year' not in df.columns:
            # Default to current year + 1 if not specified
            df['prediction_year'] = datetime.now().year + 1

        # Convert to appropriate data types
        df['prediction_year'] = pd.to_numeric(df['prediction_year'], errors='coerce').astype('Int64')
        numeric_columns = [col for col in df.columns if col not in ['country', 'country_code', 'geo_bloc', 'geo_risk_tier']]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"Prepared ml_predictions: {len(df)} rows")
        return df

    def upsert_fact_master_panel(self, df: pd.DataFrame, table_name: str = 'fact_master_panel') -> int:
        """
        Upsert data into fact_master_panel table.

        Uses INSERT ... ON CONFLICT DO UPDATE for conflict resolution.
        Matches on (country_code, year) unique constraint.

        Args:
            df: DataFrame to upsert
            table_name: Target table name

        Returns:
            Number of rows processed
        """
        if not self._validate_dataframe(df, table_name):
            return 0

        # Identify columns that exist in both DataFrame and table
        # We'll include all columns from the DataFrame
        columns = [col for col in df.columns if col not in ['country_name']]

        try:
            with self.connection.begin():
                # Build the upsert query
                insert_cols = ','.join([f'"{col}"' for col in columns])
                placeholders = ','.join(['%s'] * len(columns))
                update_cols = ','.join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col not in ['country_code', 'year']])

                upsert_sql = f"""
                    INSERT INTO {table_name} ({insert_cols}, created_at, updated_at)
                    VALUES ({placeholders}, NOW(), NOW())
                    ON CONFLICT (country_code, year)
                    DO UPDATE SET
                        {update_cols},
                        updated_at = NOW()
                """

                # Prepare data tuples
                data = [tuple(row) for row in df[columns].values]

                # Execute batch insert
                with psycopg2.connect(self.database_url) as conn:
                    with conn.cursor() as cur:
                        execute_batch(cur, upsert_sql, data, page_size=1000)
                    conn.commit()

                logger.info(f"Successfully upserted {len(data)} rows into {table_name}")
                return len(data)

        except Exception as e:
            logger.error(f"Error during upsert to {table_name}: {str(e)}")
            return 0

    def upsert_ml_predictions(self, df: pd.DataFrame, table_name: str = 'ml_predictions') -> int:
        """
        Upsert data into ml_predictions table.

        Uses INSERT ... ON CONFLICT DO UPDATE for conflict resolution.
        Matches on (country_code, prediction_year) unique constraint.

        Args:
            df: DataFrame to upsert
            table_name: Target table name

        Returns:
            Number of rows processed
        """
        if not self._validate_dataframe(df, table_name):
            return 0

        # Filter to relevant columns for ml_predictions table
        ml_columns = [
            'country_code', 'prediction_year',
            'gold_accumulation_score', 'pillar_momentum', 'pillar_consistency',
            'pillar_geo', 'pillar_alloc', 'sanctions_bonus',
            'gold_share_pct', 'gold_tonnes_yoy', 'buy_frequency_5yr',
            'accumulation_streak', 'gold_share_3yr_trend', 'un_divergence_score',
            'sanctions_score', 'geo_risk_tier', 'geo_bloc'
        ]

        # Only include columns that exist in the DataFrame
        columns = [col for col in ml_columns if col in df.columns]

        try:
            with self.connection.begin():
                # Build the upsert query
                insert_cols = ','.join([f'"{col}"' for col in columns])
                placeholders = ','.join(['%s'] * len(columns))
                update_cols = ','.join(
                    [f'"{col}" = EXCLUDED."{col}"' for col in columns if col not in ['country_code', 'prediction_year']]
                )

                upsert_sql = f"""
                    INSERT INTO {table_name} ({insert_cols}, created_at, updated_at)
                    VALUES ({placeholders}, NOW(), NOW())
                    ON CONFLICT (country_code, prediction_year)
                    DO UPDATE SET
                        {update_cols},
                        updated_at = NOW()
                """

                # Prepare data tuples
                data = [tuple(row) for row in df[columns].values]

                # Execute batch insert
                with psycopg2.connect(self.database_url) as conn:
                    with conn.cursor() as cur:
                        execute_batch(cur, upsert_sql, data, page_size=1000)
                    conn.commit()

                logger.info(f"Successfully upserted {len(data)} rows into {table_name}")
                return len(data)

        except Exception as e:
            logger.error(f"Error during upsert to {table_name}: {str(e)}")
            return 0

    def load_all(self, data_dir: str = 'data/curated') -> Dict[str, int]:
        """
        Load all curated CSV files into PostgreSQL.

        Args:
            data_dir: Path to curated data directory

        Returns:
            Dictionary with load statistics for each table
        """
        results = {
            'fact_master_panel': 0,
            'ml_predictions': 0,
            'total_rows': 0
        }

        data_path = Path(data_dir)

        # Load master_panel_nlp.csv → fact_master_panel
        master_panel_file = data_path / 'master_panel_nlp.csv'
        if master_panel_file.exists():
            df_master = self._prepare_fact_master_panel(str(master_panel_file))
            rows = self.upsert_fact_master_panel(df_master)
            results['fact_master_panel'] = rows
            results['total_rows'] += rows
        else:
            logger.warning(f"File not found: {master_panel_file}")

        # Load ml_country_scores.csv → ml_predictions
        ml_scores_file = data_path / 'ml_country_scores.csv'
        if ml_scores_file.exists():
            df_ml = self._prepare_ml_predictions(str(ml_scores_file))
            rows = self.upsert_ml_predictions(df_ml)
            results['ml_predictions'] = rows
            results['total_rows'] += rows
        else:
            logger.warning(f"File not found: {ml_scores_file}")

        return results


def main():
    """
    Main entry point for the data loading script.

    Orchestrates database connection, data loading, and cleanup.
    """
    logger.info("=" * 70)
    logger.info("Gold Reserve Platform - PostgreSQL Data Loader")
    logger.info("=" * 70)

    loader = None
    try:
        # Initialize loader
        loader = PostgreSQLLoader(DATABASE_URL)

        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / 'data' / 'curated'

        if not data_dir.exists():
            logger.error(f"Data directory not found: {data_dir}")
            sys.exit(1)

        logger.info(f"Loading data from: {data_dir}")

        # Load all data
        results = loader.load_all(str(data_dir))

        # Print summary
        logger.info("=" * 70)
        logger.info("DATA LOAD SUMMARY")
        logger.info("=" * 70)
        for table, row_count in results.items():
            logger.info(f"{table:<30} {row_count:>10} rows")
        logger.info("=" * 70)

        if results['total_rows'] > 0:
            logger.info("Data loading completed successfully")
            return 0
        else:
            logger.warning("No data was loaded")
            return 1

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1

    finally:
        if loader:
            loader.close()


if __name__ == '__main__':
    sys.exit(main())

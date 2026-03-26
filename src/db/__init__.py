"""
Gold Reserve Platform - Database Module

Provides PostgreSQL data loading and management utilities for the gold reserve
analysis platform.

Modules:
    - load_to_postgres: Main data loading functionality
"""

from .load_to_postgres import PostgreSQLLoader

__all__ = ['PostgreSQLLoader']

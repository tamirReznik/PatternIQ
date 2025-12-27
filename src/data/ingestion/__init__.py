# src/data/ingestion/__init__.py

"""
Data ingestion module for PatternIQ

This module handles the complete data ingestion pipeline including:
- Market data fetching
- Database storage
- Corporate actions
- Universe management
"""

from .pipeline import run_data_ingestion_pipeline

__all__ = ['run_data_ingestion_pipeline']


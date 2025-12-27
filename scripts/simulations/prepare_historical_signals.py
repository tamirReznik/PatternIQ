#!/usr/bin/env python3
"""
Prepare Historical Signals
Pre-generates signals for a date range before running retrospective simulation.
This ensures all signals exist in the database for the simulation period.
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Optional

# Check if running in venv
def check_venv():
    """Check if running in virtual environment and provide helpful error if not"""
    in_venv = (
        hasattr(sys, 'real_prefix') or 
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )
    
    # Also check if venv path is in Python executable
    python_path = sys.executable
    venv_indicators = ['venv', 'virtualenv', '.venv']
    path_has_venv = any(indicator in python_path for indicator in venv_indicators)
    
    if not in_venv and not path_has_venv:
        print("❌ ERROR: Virtual environment not activated!")
        print("")
        print("Please activate the virtual environment first:")
        print("  source venv/bin/activate")
        print("")
        print("Or use the wrapper script:")
        print("  bash scripts/simulations/prepare_historical_signals.sh --start 2020-01-01 --end 2025-12-31")
        print("")
        sys.exit(1)

# Check venv before importing dependencies
check_venv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.ingestion.pipeline import run_data_ingestion_pipeline
from src.features.momentum import calculate_momentum_features
from src.signals.blend import blend_signals_ic_weighted
from src.common.db_manager import db_manager
from sqlalchemy import text


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def parse_date_range(years: Optional[int] = None, start: Optional[str] = None, end: Optional[str] = None) -> tuple[date, date]:
    """Parse date range from arguments"""
    if start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    elif years:
        end_date = date.today()
        start_date = date(end_date.year - years, end_date.month, end_date.day)
    else:
        # Default: last 5 years
        end_date = date.today()
        start_date = date(end_date.year - 5, end_date.month, end_date.day)
    
    return start_date, end_date


def get_trading_days(start_date: date, end_date: date) -> list[date]:
    """Get list of trading days in date range"""
    engine = db_manager.get_engine()
    is_sqlite = 'sqlite' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if is_sqlite:
            query = """
                SELECT DISTINCT DATE(t) as trade_date
                FROM bars_1d
                WHERE DATE(t) BETWEEN :start_date AND :end_date
                ORDER BY trade_date
            """
            result = conn.execute(text(query), {
                "start_date": start_date,
                "end_date": end_date
            })
        else:
            query = """
                SELECT DISTINCT t::date as trade_date
                FROM bars_1d
                WHERE t::date BETWEEN :start_date AND :end_date
                ORDER BY trade_date
            """
            result = conn.execute(text(query), {
                "start_date": start_date,
                "end_date": end_date
            })
        
        dates = [row[0] for row in result.fetchall()]
        if dates and isinstance(dates[0], str):
            dates = [datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
        return dates


def check_signals_exist(signal_date: date) -> bool:
    """Check if signals exist for a given date"""
    engine = db_manager.get_engine()
    is_sqlite = 'sqlite' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if is_sqlite:
            query = """
                SELECT COUNT(*)
                FROM signals_daily
                WHERE DATE(d) = :signal_date
            """
        else:
            query = """
                SELECT COUNT(*)
                FROM signals_daily
                WHERE d::date = :signal_date
            """
        
        result = conn.execute(text(query), {"signal_date": signal_date})
        count = result.fetchone()[0]
        return count > 0


def generate_signals_for_date(signal_date: date, logger: logging.Logger) -> bool:
    """Generate signals for a specific date"""
    try:
        from src.signals.rules import RuleBasedSignals
        
        # Get symbols that have features for this date
        engine = db_manager.get_engine()
        is_sqlite = 'sqlite' in str(engine.url).lower()
        
        with engine.connect() as conn:
            if is_sqlite:
                query = """
                    SELECT DISTINCT symbol
                    FROM features_daily
                    WHERE DATE(d) = :signal_date
                """
            else:
                query = """
                    SELECT DISTINCT symbol
                    FROM features_daily
                    WHERE d::date = :signal_date
                """
            
            result = conn.execute(text(query), {"signal_date": signal_date})
            symbols = [row[0] for row in result.fetchall()]
        
        if not symbols:
            logger.warning(f"No symbols with features found for {signal_date}")
            return False
        
        # Generate signals using RuleBasedSignals
        logger.debug(f"Generating signals for {len(symbols)} symbols on {signal_date}...")
        signal_engine = RuleBasedSignals()
        signal_engine.compute_all_signals(symbols, signal_date)
        
        # Blend signals
        logger.debug(f"Blending signals for {signal_date}...")
        blend_signals_ic_weighted(signal_date.strftime('%Y-%m-%d'))
        
        return True
    except Exception as e:
        logger.error(f"Error generating signals for {signal_date}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Pre-generate signals for a date range before running retrospective simulation"
    )
    parser.add_argument(
        '--start',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end',
        type=str,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--years',
        type=int,
        help='Number of years to go back from today'
    )
    parser.add_argument(
        '--skip-data-ingestion',
        action='store_true',
        help='Skip data ingestion step (assume data already exists)'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip dates that already have signals'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose logging'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger("PrepareHistoricalSignals")
    
    # Parse date range
    start_date, end_date = parse_date_range(args.years, args.start, args.end)
    logger.info(f"Preparing signals for date range: {start_date} to {end_date}")
    
    # Step 1: Data ingestion (if not skipped)
    if not args.skip_data_ingestion:
        logger.info("Step 1: Running data ingestion pipeline...")
        try:
            run_data_ingestion_pipeline()
            logger.info("✅ Data ingestion completed")
        except Exception as e:
            logger.error(f"❌ Data ingestion failed: {e}")
            logger.warning("Continuing with signal generation (assuming data exists)...")
    else:
        logger.info("Skipping data ingestion (--skip-data-ingestion)")
    
    # Step 2: Get trading days
    logger.info("Step 2: Getting trading days...")
    trading_days = get_trading_days(start_date, end_date)
    logger.info(f"Found {len(trading_days)} trading days")
    
    if not trading_days:
        logger.error("No trading days found in date range")
        sys.exit(1)
    
    # Step 3: Generate signals for each trading day
    logger.info("Step 3: Generating signals for each trading day...")
    signals_generated = 0
    signals_skipped = 0
    signals_failed = 0
    
    for i, signal_date in enumerate(trading_days):
        if i % 50 == 0:
            logger.info(f"Processing day {i+1}/{len(trading_days)}: {signal_date}")
        
        # Check if signals already exist
        if args.skip_existing and check_signals_exist(signal_date):
            signals_skipped += 1
            continue
        
        # Generate signals for this date
        if generate_signals_for_date(signal_date, logger):
            signals_generated += 1
        else:
            signals_failed += 1
    
    # Summary
    logger.info("=" * 60)
    logger.info("Signal Generation Summary:")
    logger.info(f"  Trading days processed: {len(trading_days)}")
    logger.info(f"  Signals generated: {signals_generated}")
    logger.info(f"  Signals skipped (already exist): {signals_skipped}")
    logger.info(f"  Signals failed: {signals_failed}")
    logger.info("=" * 60)
    
    if signals_failed > 0:
        logger.warning(f"⚠️  {signals_failed} dates failed signal generation")
        sys.exit(1)
    else:
        logger.info("✅ All signals generated successfully")


if __name__ == '__main__':
    main()


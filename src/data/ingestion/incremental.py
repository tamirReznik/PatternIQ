#!/usr/bin/env python3
"""
Incremental Data Ingestion Module
Handles gap detection and incremental backfill of historical data
"""

import logging
from datetime import date, timedelta
from typing import List, Tuple, Optional
from sqlalchemy import create_engine, text

logger = logging.getLogger("IncrementalIngestion")

def get_data_gaps(engine, symbol: str, target_start: date, target_end: date) -> List[Tuple[date, date]]:
    """
    Detect gaps in existing data for a symbol
    
    Returns:
        List of (gap_start, gap_end) tuples representing missing date ranges
    """
    is_sqlite = 'sqlite' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if is_sqlite:
            query = text("""
                SELECT DATE(t) as d
                FROM bars_1d
                WHERE symbol = :symbol
                AND DATE(t) BETWEEN :start_date AND :end_date
                ORDER BY d
            """)
        else:
            query = text("""
                SELECT t::date as d
                FROM bars_1d
                WHERE symbol = :symbol
                AND t::date BETWEEN :start_date AND :end_date
                ORDER BY d
            """)
        
        result = conn.execute(query, {
            "symbol": symbol,
            "start_date": target_start,
            "end_date": target_end
        })
        
        existing_dates = {date.fromisoformat(str(row[0])) for row in result.fetchall()}
    
    # Generate all trading days in range (simplified - excludes weekends/holidays)
    all_dates = set()
    current = target_start
    while current <= target_end:
        # Skip weekends (simplified - real implementation should use trading calendar)
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            all_dates.add(current)
        current += timedelta(days=1)
    
    # Find missing dates
    missing_dates = sorted(all_dates - existing_dates)
    
    if not missing_dates:
        return []
    
    # Group consecutive missing dates into gaps
    gaps = []
    gap_start = missing_dates[0]
    gap_end = missing_dates[0]
    
    for d in missing_dates[1:]:
        if d == gap_end + timedelta(days=1):
            gap_end = d
        else:
            gaps.append((gap_start, gap_end))
            gap_start = d
            gap_end = d
    
    gaps.append((gap_start, gap_end))
    return gaps

def get_existing_date_range(engine, symbol: str) -> Tuple[Optional[date], Optional[date]]:
    """Get existing date range for a symbol in the database"""
    is_sqlite = 'sqlite' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if is_sqlite:
            query = text("""
                SELECT MIN(DATE(t)) as first_date, MAX(DATE(t)) as last_date
                FROM bars_1d
                WHERE symbol = :symbol
            """)
        else:
            query = text("""
                SELECT MIN(t::date) as first_date, MAX(t::date) as last_date
                FROM bars_1d
                WHERE symbol = :symbol
            """)
        
        result = conn.execute(query, {"symbol": symbol})
        row = result.fetchone()
        
        if row and row[0] and row[1]:
            return date.fromisoformat(str(row[0])), date.fromisoformat(str(row[1]))
        return None, None

def get_symbols_needing_update(engine, target_start: date, target_end: date) -> List[str]:
    """
    Get list of symbols that need data updates
    Returns symbols that either:
    1. Don't exist in database
    2. Have gaps in the target date range
    3. Don't have data up to target_end
    """
    is_sqlite = 'sqlite' in str(engine.url).lower()
    
    with engine.connect() as conn:
        # Get all symbols in database
        result = conn.execute(text("SELECT DISTINCT symbol FROM bars_1d"))
        existing_symbols = {row[0] for row in result.fetchall()}
        
        # Get symbols with incomplete data
        if is_sqlite:
            query = text("""
                SELECT symbol, MAX(DATE(t)) as last_date
                FROM bars_1d
                GROUP BY symbol
                HAVING MAX(DATE(t)) < :target_end
            """)
        else:
            query = text("""
                SELECT symbol, MAX(t::date) as last_date
                FROM bars_1d
                GROUP BY symbol
                HAVING MAX(t::date) < :target_end
            """)
        
        result = conn.execute(query, {"target_end": target_end})
        incomplete_symbols = {row[0] for row in result.fetchall()}
    
    # Return symbols that need updates
    # Note: This is a simplified version - in practice, you'd want to check for gaps too
    return list(incomplete_symbols)

def incremental_backfill(
    engine,
    symbols: List[str],
    target_start: date,
    target_end: date,
    provider,
    max_workers: int = 10
) -> dict:
    """
    Perform incremental backfill for symbols
    
    Args:
        engine: Database engine
        symbols: List of symbols to backfill
        target_start: Target start date
        target_end: Target end date
        provider: Data provider instance
        max_workers: Number of parallel workers
    
    Returns:
        Dictionary with statistics about the backfill
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from src.data.ingestion.pipeline import _process_single_symbol, setup_database
    from sqlalchemy.orm import sessionmaker
    
    logger.info(f"Starting incremental backfill for {len(symbols)} symbols")
    logger.info(f"Target date range: {target_start} to {target_end}")
    
    # Get symbols that need updates
    symbols_to_update = []
    for symbol in symbols:
        existing_start, existing_end = get_existing_date_range(engine, symbol)
        
        if existing_start is None or existing_end is None:
            # No data exists, need full range
            symbols_to_update.append((symbol, target_start, target_end))
        elif existing_end < target_end:
            # Need to extend forward
            symbols_to_update.append((symbol, existing_end + timedelta(days=1), target_end))
        elif existing_start > target_start:
            # Need to extend backward
            symbols_to_update.append((symbol, target_start, existing_start - timedelta(days=1)))
        else:
            # Check for gaps
            gaps = get_data_gaps(engine, symbol, target_start, target_end)
            if gaps:
                # Process largest gap first
                largest_gap = max(gaps, key=lambda g: (g[1] - g[0]).days)
                symbols_to_update.append((symbol, largest_gap[0], largest_gap[1]))
    
    if not symbols_to_update:
        logger.info("No symbols need updates")
        return {
            "symbols_processed": 0,
            "symbols_updated": 0,
            "total_bars": 0
        }
    
    logger.info(f"Found {len(symbols_to_update)} symbols needing updates")
    
    # Process updates in parallel
    db_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    total_bars = 0
    updated_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(
                _process_single_symbol,
                sym,
                provider,
                start.strftime("%Y-%m-%d"),
                end.strftime("%Y-%m-%d"),
                engine,
                db_session_factory
            ): sym
            for sym, start, end in symbols_to_update
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result_symbol, bars_count, error = future.result()
                if not error and bars_count > 0:
                    total_bars += bars_count
                    updated_count += 1
                    logger.info(f"Updated {result_symbol}: {bars_count} bars")
                elif error:
                    logger.warning(f"Error updating {result_symbol}: {error}")
            except Exception as e:
                logger.error(f"Exception updating {symbol}: {e}")
    
    return {
        "symbols_processed": len(symbols_to_update),
        "symbols_updated": updated_count,
        "total_bars": total_bars
    }


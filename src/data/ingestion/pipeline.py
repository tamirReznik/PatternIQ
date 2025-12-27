# src/data/ingestion/pipeline.py - Data ingestion pipeline

import logging
import os
import uuid
import json
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional

# Import our modules
from src.providers.sp500_provider import SP500Provider
from src.providers.multi_asset_provider import MultiAssetProvider
from src.data.models import Instrument, Bars1d, Base

# #region agent log
DEBUG_LOG_PATH = "/Users/tamirreznik/code/private/PatternIQ/.cursor/debug.log"
def _debug_log(location, message, data, hypothesis_id=None):
    try:
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(datetime.now().timestamp() * 1000)
            }) + "\n")
    except: pass
# #endregion

def setup_database():
    """Setup database connection and create tables"""
    # Use the database manager instead of hardcoded URL
    from src.common.db_manager import db_manager
    engine = db_manager.get_engine()
    print(f"Connecting to database: {engine.url}")

    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine

def _get_existing_date_range(engine, symbol: str) -> Tuple[Optional[date], Optional[date]]:
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

def _process_single_symbol(
    symbol: str,
    provider: MultiAssetProvider,
    start_date: str,
    end_date: str,
    engine,
    db_session_factory
) -> Tuple[str, int, Optional[str]]:
    """
    Process a single symbol: fetch data and save to database
    Returns: (symbol, bars_count, error_message)
    """
    try:
        # Create a new session for this thread
        db = db_session_factory()
        
        # Fetch bars
        bars = provider.get_bars(symbol, "1d", start_date, end_date)
        if not bars:
            db.close()
            return (symbol, 0, None)
        
        # Check data quality
        quality_report = provider._validate_data_quality(symbol, bars)
        quality_issues = []
        if quality_report.get('quality_score', 100) < 70:
            quality_issues.append({
                'symbol': symbol,
                'score': quality_report.get('quality_score', 0),
                'issues': quality_report.get('issues', [])
            })
        
        # Get asset class metadata
        asset_metadata = None
        if hasattr(provider, 'get_symbol_metadata'):
            asset_metadata = provider.get_symbol_metadata(symbol)
        
        # Determine sector/asset class
        if asset_metadata:
            sector = asset_metadata.get('sector', 'Unknown')
            name = asset_metadata.get('description', f"{symbol} {asset_metadata.get('type', 'Security')}")
        else:
            # Fallback: try to detect from provider's internal dictionaries
            if hasattr(provider, 'sector_etfs') and symbol in provider.sector_etfs:
                sector = provider.sector_etfs[symbol]
                name = f"Sector ETF - {sector}"
            elif hasattr(provider, 'crypto_etfs') and symbol in provider.crypto_etfs:
                sector = "Cryptocurrency"
                name = f"Crypto ETF - {provider.crypto_etfs[symbol]}"
            elif hasattr(provider, 'international_etfs') and symbol in provider.international_etfs:
                sector = "International"
                name = f"International ETF - {provider.international_etfs[symbol]}"
            elif hasattr(provider, 'factor_etfs') and symbol in provider.factor_etfs:
                sector = "Factor"
                name = f"Factor ETF - {provider.factor_etfs[symbol]}"
            else:
                # Default for S&P 500 stocks
                sector = "Technology" if symbol in ['AAPL', 'MSFT', 'GOOGL'] else "Unknown"
                name = f"{symbol} Corporation"
        
        # Save instrument
        instrument = Instrument(
            symbol=symbol,
            name=name,
            is_active=True,
            first_seen=date.today(),
            sector=sector
        )
        try:
            db.add(instrument)
            db.flush()
        except IntegrityError:
            db.rollback()
        
        # Save bars
        for bar in bars:
            timestamp = bar["t"]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            bar_record = Bars1d(
                symbol=symbol,
                t=timestamp,
                o=bar["o"],
                h=bar["h"],
                l=bar["l"],
                c=bar["c"],
                v=bar["v"],
                adj_o=bar["o"],
                adj_h=bar["h"],
                adj_l=bar["l"],
                adj_c=bar["c"],
                adj_v=bar["v"],
                vendor=bar["vendor"]
            )
            db.merge(bar_record)
        
        db.commit()
        db.close()
        
        return (symbol, len(bars), None)
        
    except Exception as e:
        if 'db' in locals():
            db.rollback()
            db.close()
        return (symbol, 0, str(e))

def run_data_ingestion_pipeline(start_date: str = None, end_date: str = None, max_workers: int = 10):
    """
    Run the complete data ingestion pipeline for PatternIQ
    
    Args:
        start_date: Start date for data ingestion (YYYY-MM-DD format). 
                   If None, defaults to last 30 days.
        end_date: End date for data ingestion (YYYY-MM-DD format).
                 If None, defaults to today.
        max_workers: Number of parallel workers (default: 10)
    """
    print("🚀 PatternIQ Data Ingestion Pipeline")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Determine date range
    # Default to last 30 days for fast initial testing, can be overridden
    from datetime import date as date_type, timedelta
    end = date_type.today()
    
    if start_date is None and end_date is None:
        # Default: last 30 days for testing
        start = end - timedelta(days=30)
        start_date = start.strftime("%Y-%m-%d")
        end_date = end.strftime("%Y-%m-%d")
        print(f"📅 Using default date range: last 30 days ({start_date} to {end_date})")
    else:
        if start_date is None:
            # If only end_date provided, default to 5 years back
            start = date_type(end.year - 5, end.month, end.day)
            start_date = start.strftime("%Y-%m-%d")
        if end_date is None:
            end_date = end.strftime("%Y-%m-%d")
        print(f"📅 Data ingestion date range: {start_date} to {end_date}")
    
    # Initialize provider with volume filtering for mid/long-term trading
    # Use config values if available, otherwise use defaults
    try:
        from src.core.config import config
        min_volume = config.min_daily_volume
        min_mcap = config.min_market_cap
        min_days = config.min_days_listed
    except:
        # Fallback to environment variables or defaults
        min_volume = float(os.getenv('MIN_DAILY_VOLUME', '10000000'))
        min_mcap = float(os.getenv('MIN_MARKET_CAP', '1000000000'))
        min_days = int(os.getenv('MIN_DAYS_LISTED', '90'))
    
    # Use MultiAssetProvider to get S&P 500 stocks + ETFs (sector, crypto, international, factor)
    # MultiAssetProvider already includes S&P 500 symbols via _get_sp500_symbols()
    provider = MultiAssetProvider(
        min_daily_volume=min_volume,
        min_market_cap=min_mcap
    )
    db, engine = setup_database()
    
    try:
        # Step 1: Fetch multi-asset symbols (S&P 500 stocks + ETFs)
        print("\n📊 Step 1: Fetching Multi-Asset Universe")
        print("-" * 40)
        symbols = provider.list_symbols()
        print(f"✅ Fetched {len(symbols)} symbols (S&P 500 stocks + ETFs)")
        
        # Step 2: Process symbols
        # Check if we should process all symbols or just a subset
        process_all = os.getenv('PROCESS_ALL_SYMBOLS', 'false').lower() == 'true'
        if process_all:
            test_symbols = symbols
            print(f"\n📈 Step 2: Processing all {len(test_symbols)} symbols (parallel, {max_workers} workers)")
        else:
            test_symbols = symbols[:5]
            print(f"\n📈 Step 2: Processing {len(test_symbols)} symbols for demo (set PROCESS_ALL_SYMBOLS=true for all)")
        print("-" * 40)
        
        # Parallel processing
        total_bars = 0
        quality_issues = []
        errors = []
        completed = 0
        
        db_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(
                    _process_single_symbol,
                    symbol,
                    provider,
                    start_date,
                    end_date,
                    engine,
                    db_session_factory
                ): symbol
                for symbol in test_symbols
            }
            
            # Process completed tasks
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed += 1
                try:
                    result_symbol, bars_count, error = future.result()
                    if error:
                        errors.append((result_symbol, error))
                        print(f"  ❌ {result_symbol}: {error}")
                    else:
                        total_bars += bars_count
                        print(f"  ✅ [{completed}/{len(test_symbols)}] {result_symbol}: {bars_count} bars")
                except Exception as e:
                    errors.append((symbol, str(e)))
                    print(f"  ❌ {symbol}: {str(e)}")
        
        if errors:
            print(f"\n⚠️  {len(errors)} symbols had errors:")
            for sym, err in errors[:10]:  # Show first 10 errors
                print(f"    {sym}: {err}")
        
        # Step 3: Add universe membership data
        print(f"\n🌐 Step 3: Recording Universe Membership")
        print("-" * 40)
        
        is_sqlite = 'sqlite' in str(engine.url).lower()
        
        with engine.connect() as conn:
            for symbol in test_symbols:
                # Determine universe based on asset class
                asset_metadata = None
                if hasattr(provider, 'get_symbol_metadata'):
                    asset_metadata = provider.get_symbol_metadata(symbol)
                
                if asset_metadata:
                    asset_class = asset_metadata.get('asset_class', 'equity')
                    if asset_class == 'sector_etf':
                        universe = "SECTOR_ETF"
                    elif asset_class == 'crypto_etf':
                        universe = "CRYPTO_ETF"
                    elif asset_class == 'international_etf':
                        universe = "INTERNATIONAL_ETF"
                    elif asset_class == 'factor_etf':
                        universe = "FACTOR_ETF"
                    else:
                        universe = "SP500"
                else:
                    # Fallback: check provider dictionaries
                    if hasattr(provider, 'sector_etfs') and symbol in provider.sector_etfs:
                        universe = "SECTOR_ETF"
                    elif hasattr(provider, 'crypto_etfs') and symbol in provider.crypto_etfs:
                        universe = "CRYPTO_ETF"
                    elif hasattr(provider, 'international_etfs') and symbol in provider.international_etfs:
                        universe = "INTERNATIONAL_ETF"
                    elif hasattr(provider, 'factor_etfs') and symbol in provider.factor_etfs:
                        universe = "FACTOR_ETF"
                    else:
                        universe = "SP500"
                
                # Insert universe membership
                if is_sqlite:
                    conn.execute(text("""
                        INSERT OR IGNORE INTO universe_membership (symbol, universe, effective_from)
                        VALUES (:symbol, :universe, :effective_from)
                    """), {
                        "symbol": symbol,
                        "universe": universe,
                        "effective_from": start_date
                    })
                else:
                    conn.execute(text("""
                        INSERT INTO universe_membership (symbol, universe, effective_from)
                        VALUES (:symbol, :universe, :effective_from)
                        ON CONFLICT (symbol, universe, effective_from) DO NOTHING
                    """), {
                        "symbol": symbol,
                        "universe": universe,
                        "effective_from": start_date
                    })
            
            conn.commit()
        
        print(f"✅ Added universe membership for {len(test_symbols)} symbols")
        
        # Step 4: Add sample fundamental data (optional, can be enhanced later)
        print(f"\n📊 Step 4: Adding Fundamental Data (Sample)")
        print("-" * 40)
        
        # This is a placeholder - can be enhanced with real fundamental data providers
        sample_fundamentals = {}
        
        with engine.connect() as conn:
            for symbol, data in sample_fundamentals.items():
                if symbol in test_symbols:
                    conn.execute(
                        text("""
                        INSERT INTO fundamentals_snapshot (symbol, asof, market_cap, ttm_eps, pe)
                        VALUES (:symbol, :asof, :market_cap, :ttm_eps, :pe)
                        ON CONFLICT (symbol, asof) DO UPDATE SET
                            market_cap = EXCLUDED.market_cap,
                            ttm_eps = EXCLUDED.ttm_eps,
                            pe = EXCLUDED.pe
                        """),
                        {
                            "symbol": symbol,
                            "asof": end_date,
                            "market_cap": data.get("market_cap"),
                            "ttm_eps": data.get("ttm_eps"),
                            "pe": data.get("pe")
                        }
                    )
            conn.commit()
        
        print(f"✅ Added fundamental data for {len([s for s in sample_fundamentals.keys() if s in test_symbols])} symbols")
        
        # Summary
        print(f"\n🎉 Data Ingestion Completed!")
        print("=" * 60)
        print(f"✅ Processed {len(test_symbols)} symbols")
        print(f"✅ Stored {total_bars} daily bars")
        print(f"✅ Date range: {start_date} to {end_date}")
        if errors:
            print(f"⚠️  {len(errors)} symbols had errors")
        
        # Show sample data
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM instruments"))
            total_instruments = result.fetchone()[0]
            
            result = conn.execute(text("SELECT COUNT(*) FROM bars_1d"))
            total_bars_db = result.fetchone()[0]
            
            result = conn.execute(text("SELECT symbol, name, sector FROM instruments LIMIT 5"))
            sample_instruments = result.fetchall()
            
            result = conn.execute(text("SELECT symbol, t, c FROM bars_1d ORDER BY t DESC LIMIT 3"))
            sample_bars = result.fetchall()
        
        print(f"\n📊 Database Summary:")
        print(f"  Total instruments: {total_instruments}")
        print(f"  Total bars: {total_bars_db}")
        print(f"\n  Sample Instruments:")
        for symbol, name, sector in sample_instruments:
            print(f"    {symbol}: {name} ({sector})")
        
        print(f"\n  Recent Bars:")
        for symbol, timestamp, close in sample_bars:
            print(f"    {symbol} @ {timestamp}: ${close:.2f}")
        
    except Exception as e:
        print(f"\n❌ Error in full pipeline: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    run_data_ingestion_pipeline()

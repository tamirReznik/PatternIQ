# src/data/ingestion/pipeline.py - Data ingestion pipeline

import logging
import os
import uuid
import json
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

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

def run_data_ingestion_pipeline(start_date: str = None, end_date: str = None):
    """
    Run the complete data ingestion pipeline for PatternIQ
    
    Args:
        start_date: Start date for data ingestion (YYYY-MM-DD format). 
                   If None, defaults to 5 years back from today.
        end_date: End date for data ingestion (YYYY-MM-DD format).
                 If None, defaults to today.
    """
    print("🚀 PatternIQ Full Pipeline Demo")
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
    # #region agent log
    _debug_log("pipeline.py:39", "Database setup complete", {
        "engine_url": str(engine.url),
        "db_session_id": id(db),
        "engine_id": id(engine),
        "is_sqlite": "sqlite" in str(engine.url).lower()
    }, "A")
    # #endregion
    
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
            print(f"\n📈 Step 2: Processing all {len(test_symbols)} symbols")
        else:
            test_symbols = symbols[:5]
            print(f"\n📈 Step 2: Processing {len(test_symbols)} symbols for demo (set PROCESS_ALL_SYMBOLS=true for all)")
        print("-" * 40)
        
        total_bars = 0
        quality_issues = []
        for i, symbol in enumerate(test_symbols, 1):
            print(f"Processing {i}/{len(test_symbols)}: {symbol}")
            
            # Fetch bars (with automatic fallback and quality validation)
            # Use the provided date range (or default 5 years)
            bars = provider.get_bars(symbol, "1d", start_date, end_date)
            if bars:
                # Check data quality (already validated in get_bars, but log summary)
                quality_report = provider._validate_data_quality(symbol, bars)
                if quality_report.get('quality_score', 100) < 70:
                    quality_issues.append({
                        'symbol': symbol,
                        'score': quality_report.get('quality_score', 0),
                        'issues': quality_report.get('issues', [])
                    })
                # Get asset class metadata from provider
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
                    db.flush()  # ensure insert
                except IntegrityError:
                    db.rollback()  # already exists, ignore

                # Save bars
                for bar in bars:
                    # Convert timestamp to proper format for SQLite compatibility
                    timestamp = bar["t"]
                    if isinstance(timestamp, str):
                        # Parse string timestamp and convert to datetime
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                    bar_record = Bars1d(
                        symbol=symbol,
                        t=timestamp,
                        o=bar["o"],
                        h=bar["h"],
                        l=bar["l"],
                        c=bar["c"],
                        v=bar["v"],
                        adj_o=bar["o"],  # For now, same as raw
                        adj_h=bar["h"],
                        adj_l=bar["l"],
                        adj_c=bar["c"],
                        adj_v=bar["v"],
                        vendor=bar["vendor"]
                    )
                    db.merge(bar_record)
                
                # Commit after each symbol to release locks and avoid SQLite lock conflicts
                # #region agent log
                _debug_log("pipeline.py:127", "Committing after symbol bars", {
                    "symbol": symbol,
                    "bars_count": len(bars),
                    "db_session_id": id(db),
                    "pending_new": len(db.new) if hasattr(db, 'new') else 0,
                    "pending_dirty": len(db.dirty) if hasattr(db, 'dirty') else 0
                }, "A")
                # #endregion
                db.commit()  # Commit after each symbol to release SQLite locks
                
                total_bars += len(bars)
                print(f"  ✅ Saved {len(bars)} bars for {symbol}")
        
        # #region agent log
        _debug_log("pipeline.py:141", "All symbols processed, about to do universe membership", {
            "db_session_id": id(db),
            "total_bars": total_bars,
            "pending_new": len(db.new) if hasattr(db, 'new') else 0,
            "pending_dirty": len(db.dirty) if hasattr(db, 'dirty') else 0
        }, "A")
        # #endregion
        
        # Step 3: Add universe membership data
        # Close db session and use engine.connect() with a fresh connection to avoid lock conflicts
        print(f"\n🌐 Step 3: Recording Universe Membership")
        print("-" * 40)
        
        # Close the db session to release all locks before opening new connection
        db.close()
        
        # #region agent log
        _debug_log("pipeline.py:151", "db session closed, opening engine.connect()", {
            "engine_id": id(engine),
            "is_sqlite": "sqlite" in str(engine.url).lower()
        }, "A")
        # #endregion
        
        # Check if using SQLite or PostgreSQL
        is_sqlite = 'sqlite' in str(engine.url).lower()
        
        with engine.connect() as conn:
            for symbol in test_symbols:
                # #region agent log
                _debug_log("pipeline.py:162", "About to execute INSERT for universe_membership", {
                    "symbol": symbol,
                    "conn_id": id(conn),
                    "is_sqlite": is_sqlite
                }, "A")
                # #endregion
                
                # Determine universe based on asset class
                # Get asset metadata to determine universe
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
                        universe = "SP500"  # Default for stocks
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
                        universe = "SP500"  # Default for stocks
                
                if is_sqlite:
                    # SQLite: Use INSERT OR IGNORE (works with composite primary keys)
                    try:
                        conn.execute(
                            text("""
                            INSERT OR IGNORE INTO universe_membership (symbol, universe, effective_from, effective_to)
                            VALUES (:symbol, :universe, :effective_from, :effective_to)
                            """),
                            {"symbol": symbol, "universe": universe, "effective_from": date(2024, 1, 1), "effective_to": date(2024, 12, 31)}
                        )
                        # #region agent log
                        _debug_log("pipeline.py:174", "INSERT executed successfully", {
                            "symbol": symbol,
                            "conn_id": id(conn)
                        }, "A")
                        # #endregion
                    except Exception as e:
                        # #region agent log
                        _debug_log("pipeline.py:174", "INSERT failed", {
                            "symbol": symbol,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "conn_id": id(conn)
                        }, "A")
                        # #endregion
                        raise
                else:
                    # PostgreSQL: Use ON CONFLICT
                    conn.execute(
                        text("""
                        INSERT INTO universe_membership (symbol, universe, effective_from, effective_to)
                        VALUES (:symbol, :universe, :effective_from, :effective_to)
                        ON CONFLICT (symbol, universe, effective_from) DO NOTHING
                        """),
                        {"symbol": symbol, "universe": universe, "effective_from": date(2024, 1, 1), "effective_to": date(2024, 12, 31)}
                    )
            conn.commit()
        
        # Count symbols by universe
        with engine.connect() as conn:
            if is_sqlite:
                # SQLite: Use placeholders for IN clause
                placeholders = ','.join(['?' for _ in test_symbols])
                query = f"""
                    SELECT universe, COUNT(DISTINCT symbol) as count
                    FROM universe_membership
                    WHERE symbol IN ({placeholders})
                    GROUP BY universe
                """
                result = conn.execute(text(query), test_symbols)
            else:
                # PostgreSQL: Use ANY with array
                result = conn.execute(text("""
                    SELECT universe, COUNT(DISTINCT symbol) as count
                    FROM universe_membership
                    WHERE symbol = ANY(:symbols)
                    GROUP BY universe
                """), {"symbols": test_symbols})
            universe_counts = {row[0]: row[1] for row in result.fetchall()}
        
        print(f"✅ Added {len(test_symbols)} symbols to universes:")
        for uni, count in universe_counts.items():
            print(f"   {uni}: {count} symbols")
        
        # Step 4: Add sample fundamental data
        print(f"\n💰 Step 4: Adding Sample Fundamental Data")
        print("-" * 40)
        
        sample_fundamentals = {
            'MMM': {'market_cap': 70000000000, 'ttm_eps': 4.50, 'pe': 19.2},
            'AOS': {'market_cap': 12000000000, 'ttm_eps': 3.25, 'pe': 22.8},
            'ABT': {'market_cap': 190000000000, 'ttm_eps': 4.85, 'pe': 23.1}
        }
        
        # Use engine.connect() since db session is already closed
        # #region agent log
        _debug_log("pipeline.py:228", "Using engine.connect() for fundamentals_snapshot", {
            "engine_id": id(engine)
        }, "A")
        # #endregion
        
        with engine.connect() as conn:
            for symbol, data in sample_fundamentals.items():
                if symbol in test_symbols:
                    conn.execute(
                        text("""
                        INSERT INTO fundamentals_snapshot (symbol, asof, market_cap, ttm_eps, pe)
                        VALUES (:symbol, :asof, :market_cap, :ttm_eps, :pe)
                        """),
                        {"symbol": symbol, "asof": date(2024, 1, 1), "market_cap": data['market_cap'], "ttm_eps": data['ttm_eps'], "pe": data['pe']}
                    )
            conn.commit()
        
        print(f"✅ Added fundamental data for {len([s for s in sample_fundamentals.keys() if s in test_symbols])} symbols")

        # Log data quality summary
        if quality_issues:
            print(f"\n⚠️  Data Quality Issues Detected:")
            print("-" * 40)
            for issue in quality_issues:
                print(f"  {issue['symbol']}: Quality Score {issue['score']}/100")
                for problem in issue['issues'][:3]:  # Show first 3 issues
                    print(f"    - {problem}")
        else:
            print(f"\n✅ All data passed quality validation")

        # Step 5: Generate comprehensive report
        print(f"\n📋 Step 5: Pipeline Summary Report")
        print("-" * 40)
        
        # Count records in each table - use engine.connect() since db session is closed
        # #region agent log
        _debug_log("pipeline.py:250", "Using engine.connect() for read queries", {
            "engine_id": id(engine)
        }, "A")
        # #endregion
        
        tables_data = {}
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM instruments"))
            tables_data['instruments'] = result.fetchone()[0]
            
            result = conn.execute(text("SELECT COUNT(*) FROM bars_1d"))
            tables_data['bars_1d'] = result.fetchone()[0]
            
            result = conn.execute(text("SELECT COUNT(*) FROM universe_membership"))
            tables_data['universe_membership'] = result.fetchone()[0]
            
            result = conn.execute(text("SELECT COUNT(*) FROM fundamentals_snapshot"))
            tables_data['fundamentals_snapshot'] = result.fetchone()[0]
            
            # Sample queries
            result = conn.execute(text("SELECT symbol, name, sector FROM instruments LIMIT 5"))
            sample_instruments = result.fetchall()
            
            result = conn.execute(text("SELECT symbol, t, c FROM bars_1d ORDER BY t DESC LIMIT 3"))
            sample_bars = result.fetchall()
        print("📊 Database Summary:")
        for table, count in tables_data.items():
            print(f"  {table}: {count} records")
        
        print(f"\n📈 Sample Data:")
        print("  Recent Instruments:")
        for symbol, name, sector in sample_instruments:
            print(f"    {symbol}: {name} ({sector})")
        
        print("  Recent Bars:")
        for symbol, timestamp, close in sample_bars:
            print(f"    {symbol} @ {timestamp}: ${close:.2f}")
        
        print(f"\n🎉 Full Pipeline Demo Completed Successfully!")
        print(f"✅ Processed {len(test_symbols)} symbols")
        print(f"✅ Stored {total_bars} daily bars")
        print(f"✅ Populated 4 database tables")
        print(f"✅ Ready for feature engineering and signal generation!")
        
    except Exception as e:
        print(f"❌ Error in full pipeline: {e}")
        import traceback
        traceback.print_exc()
        try:
            if db and not db.is_closed if hasattr(db, 'is_closed') else db:
                db.rollback()
        except:
            pass
    finally:
        try:
            if db and not db.is_closed if hasattr(db, 'is_closed') else db:
                db.close()
        except:
            pass

if __name__ == "__main__":
    demo_full_data_ingestion()

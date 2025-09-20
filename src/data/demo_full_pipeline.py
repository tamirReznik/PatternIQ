# src/data/demo_full_pipeline.py - Comprehensive pipeline demo

import logging
import os
import uuid
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import our modules
from src.providers.sp500_provider import SP500Provider
from src.data.models import Instrument, Bars1d, Base

def setup_database():
    """Setup database connection and create tables"""
    db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
    print(f"Connecting to database: {db_url}")
    
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine

def demo_full_data_ingestion():
    """Demo: Comprehensive data ingestion pipeline"""
    print("🚀 PatternIQ Full Pipeline Demo")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    provider = SP500Provider()
    db, engine = setup_database()
    
    try:
        # Step 1: Fetch S&P 500 symbols
        print("\n📊 Step 1: Fetching S&P 500 Universe")
        print("-" * 40)
        symbols = provider.list_symbols()
        print(f"✅ Fetched {len(symbols)} S&P 500 symbols")
        
        # Step 2: Process first 5 symbols for demo
        test_symbols = symbols[:5]
        print(f"\n📈 Step 2: Processing {len(test_symbols)} symbols for demo")
        print("-" * 40)
        
        total_bars = 0
        for i, symbol in enumerate(test_symbols, 1):
            print(f"Processing {i}/{len(test_symbols)}: {symbol}")
            
            # Fetch bars
            bars = provider.get_bars(symbol, "1d", "2024-01-01", "2024-01-10")
            if bars:
                # Save instrument
                instrument = Instrument(
                    symbol=symbol,
                    name=f"{symbol} Corporation",
                    is_active=True,
                    first_seen=datetime.now().date(),
                    sector="Technology" if symbol in ['AAPL', 'MSFT', 'GOOGL'] else "Unknown"
                )
                db.merge(instrument)
                
                # Save bars
                for bar in bars:
                    bar_record = Bars1d(
                        symbol=symbol,
                        t=bar["t"],
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
                
                total_bars += len(bars)
                print(f"  ✅ Saved {len(bars)} bars for {symbol}")
        
        # Step 3: Add universe membership data
        print(f"\n🌐 Step 3: Recording Universe Membership")
        print("-" * 40)
        
        with engine.connect() as conn:
            for symbol in test_symbols:
                conn.execute(
                    text("""
                    INSERT INTO universe_membership (symbol, universe, effective_from, effective_to)
                    VALUES (:symbol, :universe, :effective_from, :effective_to)
                    ON CONFLICT (symbol, universe, effective_from) DO NOTHING
                    """),
                    {"symbol": symbol, "universe": "SP500", "effective_from": date(2024, 1, 1), "effective_to": date(2024, 12, 31)}
                )
            conn.commit()
        
        print(f"✅ Added {len(test_symbols)} symbols to S&P 500 universe")
        
        # Step 4: Add sample fundamental data
        print(f"\n💰 Step 4: Adding Sample Fundamental Data")
        print("-" * 40)
        
        sample_fundamentals = {
            'MMM': {'market_cap': 70000000000, 'ttm_eps': 4.50, 'pe': 19.2},
            'AOS': {'market_cap': 12000000000, 'ttm_eps': 3.25, 'pe': 22.8},
            'ABT': {'market_cap': 190000000000, 'ttm_eps': 4.85, 'pe': 23.1}
        }
        
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

        # Commit all changes
        db.commit()
        
        # Step 5: Generate comprehensive report
        print(f"\n📋 Step 5: Pipeline Summary Report")
        print("-" * 40)
        
        # Count records in each table
        with engine.connect() as conn:
            tables_data = {}
            
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
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    demo_full_data_ingestion()

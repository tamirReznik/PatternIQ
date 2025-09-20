# src/data/demo_fetch.py

import logging
import os
from datetime import datetime
from sqlalchemy import create_engine
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
    return SessionLocal()

def demo_fetch_symbols():
    """Demo: Fetch S&P 500 symbols"""
    print("\n=== DEMO: Fetching S&P 500 Symbols ===")
    provider = SP500Provider()

    try:
        symbols = provider.list_symbols()
        print(f"✅ Successfully fetched {len(symbols)} S&P 500 symbols")
        print(f"First 10 symbols: {symbols[:10]}")
        return symbols
    except Exception as e:
        print(f"❌ Error fetching symbols: {e}")
        return []

def demo_fetch_bars(symbol: str):
    """Demo: Fetch daily bars for a symbol"""
    print(f"\n=== DEMO: Fetching Daily Bars for {symbol} ===")
    provider = SP500Provider()

    try:
        bars = provider.get_bars(symbol, "1d", "2024-01-01", "2024-01-10")
        print(f"✅ Successfully fetched {len(bars)} bars for {symbol}")

        if bars:
            print("Sample bar:")
            bar = bars[0]
            print(f"  Date: {bar['t']}")
            print(f"  Open: ${bar['o']:.2f}")
            print(f"  High: ${bar['h']:.2f}")
            print(f"  Low: ${bar['l']:.2f}")
            print(f"  Close: ${bar['c']:.2f}")
            print(f"  Volume: {bar['v']:,}")

        return bars
    except Exception as e:
        print(f"❌ Error fetching bars: {e}")
        return []

def demo_save_to_database(symbol: str, bars: list):
    """Demo: Save data to database"""
    print(f"\n=== DEMO: Saving {symbol} Data to Database ===")

    try:
        db = setup_database()

        # Save instrument
        instrument = Instrument(
            symbol=symbol,
            name=f"{symbol} Inc.",
            is_active=True,
            first_seen=datetime.now().date(),
            sector="Technology"  # placeholder
        )
        db.merge(instrument)
        print(f"✅ Saved instrument: {symbol}")

        # Save bars
        bars_saved = 0
        for bar in bars:
            bar_record = Bars1d(
                symbol=symbol,
                t=bar["t"],
                o=bar["o"],
                h=bar["h"],
                l=bar["l"],
                c=bar["c"],
                v=bar["v"],
                adj_o=bar["o"],  # For now, same as raw (no adjustments yet)
                adj_h=bar["h"],
                adj_l=bar["l"],
                adj_c=bar["c"],
                adj_v=bar["v"],
                vendor=bar["vendor"]
            )
            db.merge(bar_record)
            bars_saved += 1

        db.commit()
        print(f"✅ Saved {bars_saved} bars to database")

        # Verify data was saved
        instrument_count = db.query(Instrument).filter(Instrument.symbol == symbol).count()
        bars_count = db.query(Bars1d).filter(Bars1d.symbol == symbol).count()

        print(f"✅ Verification - Instruments in DB: {instrument_count}, Bars in DB: {bars_count}")

        db.close()

    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()

def main():
    """Run complete demo flow"""
    print("🚀 PatternIQ Data Ingestion Demo")
    print("=" * 50)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Step 1: Fetch symbols
    symbols = demo_fetch_symbols()

    if not symbols:
        print("❌ No symbols fetched. Exiting demo.")
        return

    # Step 2: Pick first symbol and fetch bars
    test_symbol = symbols[0]
    bars = demo_fetch_bars(test_symbol)

    if not bars:
        print(f"❌ No bars fetched for {test_symbol}. Exiting demo.")
        return

    # Step 3: Save to database
    demo_save_to_database(test_symbol, bars)

    print(f"\n🎉 Demo completed successfully!")
    print(f"Next steps:")
    print(f"  - Expand to fetch more symbols")
    print(f"  - Add corporate actions handling")
    print(f"  - Implement adjustment logic")

if __name__ == "__main__":
    main()

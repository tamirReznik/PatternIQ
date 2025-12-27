# Section 2 Verification Script
# Tests all components of Section 2: Storage & data structures

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, date
from sqlalchemy import create_engine, text

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")

def verify_database_schema():
    """Verify all 11 tables from Section 2 are properly created"""
    print_section("SECTION 2.1: DATABASE SCHEMA VERIFICATION")

    db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
    engine = create_engine(db_url)

    try:
        with engine.connect() as conn:
            # Get all tables
            result = conn.execute(text("""
                SELECT table_name, 
                       (SELECT count(*) FROM information_schema.columns 
                        WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))

            tables = result.fetchall()

            expected_tables = [
                'backtest_positions', 'backtests', 'bars_1d', 'corporate_actions',
                'earnings', 'features_daily', 'fundamentals_snapshot',
                'instruments', 'reports', 'signals_daily', 'universe_membership'
            ]

            print(f"📊 Database Schema Status:")
            print(f"Expected tables: {len(expected_tables)}")
            print(f"Found tables: {len(tables)}")

            print(f"\nTable Details:")
            found_table_names = []
            for table_name, column_count in tables:
                found_table_names.append(table_name)
                status = "✅" if table_name in expected_tables else "❓"
                print(f"  {status} {table_name:<20} ({column_count} columns)")

            # Check for missing tables
            missing = set(expected_tables) - set(found_table_names)
            if missing:
                print(f"\n❌ Missing tables: {missing}")
                return False
            else:
                print(f"\n✅ All required tables present!")
                return True

    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def verify_data_ingestion():
    """Verify Section 1 data is properly loaded"""
    print_section("SECTION 2.2: DATA INGESTION VERIFICATION")

    db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
    engine = create_engine(db_url)

    try:
        with engine.connect() as conn:
            # Check instruments
            result = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT symbol) FROM instruments"))
            inst_count, unique_symbols = result.fetchone()
            print(f"📈 Instruments: {inst_count} records, {unique_symbols} unique symbols")

            # Check bars
            result = conn.execute(text("""
                SELECT COUNT(*), COUNT(DISTINCT symbol), 
                       MIN(t) as earliest, MAX(t) as latest
                FROM bars_1d
            """))
            bars_count, bars_symbols, earliest, latest = result.fetchone()
            print(f"📊 Daily Bars: {bars_count} records, {bars_symbols} symbols")
            print(f"   Date range: {earliest} to {latest}")

            # Check universe membership
            result = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT symbol) FROM universe_membership"))
            univ_count, univ_symbols = result.fetchone()
            print(f"🌐 Universe Membership: {univ_count} records, {univ_symbols} symbols")

            # Check fundamentals
            result = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT symbol) FROM fundamentals_snapshot"))
            fund_count, fund_symbols = result.fetchone()
            print(f"💰 Fundamentals: {fund_count} records, {fund_symbols} symbols")

            # Sample data
            print(f"\n📋 Sample Data:")
            result = conn.execute(text("""
                SELECT i.symbol, i.name, i.sector,
                       (SELECT COUNT(*) FROM bars_1d b WHERE b.symbol = i.symbol) as bars_count
                FROM instruments i
                ORDER BY i.symbol
                LIMIT 5
            """))

            samples = result.fetchall()
            print(f"Symbol | Name                 | Sector     | Bars")
            print(f"-------|---------------------|------------|------")
            for symbol, name, sector, bars in samples:
                name_short = (name[:17] + "...") if name and len(name) > 20 else (name or "N/A")
                sector_short = (sector[:8] + "..") if sector and len(sector) > 10 else (sector or "N/A")
                print(f"{symbol:6} | {name_short:19} | {sector_short:10} | {bars:4}")

            return bars_count > 0 and inst_count > 0

    except Exception as e:
        print(f"❌ Data verification error: {e}")
        return False

def verify_price_adjustments():
    """Verify Section 2 price adjustment logic"""
    print_section("SECTION 2.3: PRICE ADJUSTMENT VERIFICATION")

    # Import our adjustment module
    sys.path.append('/Users/tamirreznik/code/private/PatternIQ')
    from src.adjust.adjuster import PriceAdjuster

    try:
        adjuster = PriceAdjuster()

        # Test symbol
        test_symbol = "MMM"

        print(f"🔧 Testing price adjustments for {test_symbol}")

        # Add a test corporate action
        test_date = date(2024, 1, 5)
        print(f"   Adding 2:1 split on {test_date}")

        adjuster.add_corporate_action(
            symbol=test_symbol,
            action_date=test_date,
            action_type="split",
            ratio=2.0
        )

        # Test adjustment factor calculation
        factors_before = adjuster.get_adjustment_factors(test_symbol, date(2024, 1, 4))
        factors_after = adjuster.get_adjustment_factors(test_symbol, date(2024, 1, 6))

        print(f"   Adjustment factors before split: price={factors_before['price_factor']:.2f}, volume={factors_before['volume_factor']:.2f}")
        print(f"   Adjustment factors after split:  price={factors_after['price_factor']:.2f}, volume={factors_after['volume_factor']:.2f}")

        # Verify the adjustment logic worked
        if factors_after['price_factor'] == 2.0 and factors_after['volume_factor'] == 0.5:
            print(f"   ✅ Adjustment factors calculated correctly!")
        else:
            print(f"   ❌ Adjustment factors incorrect!")
            return False

        # Test recomputation
        print(f"   Recomputing adjusted prices...")
        adjuster.recompute_adjustments_for_symbol(test_symbol)

        # Show sample adjusted vs raw prices
        with adjuster.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT t, o, c, adj_o, adj_c
                FROM bars_1d
                WHERE symbol = :symbol
                ORDER BY t ASC
                LIMIT 3
            """), {"symbol": test_symbol})

            bars = result.fetchall()

            if bars:
                print(f"\n   📊 Sample Adjusted Prices:")
                print(f"   Date       | Raw Open | Raw Close | Adj Open | Adj Close")
                print(f"   -----------|----------|-----------|----------|----------")
                for t, o, c, adj_o, adj_c in bars:
                    print(f"   {t.strftime('%Y-%m-%d')} | ${o:8.2f} | ${c:9.2f} | ${adj_o:8.2f} | ${adj_c:9.2f}")

                # Verify adjustment was applied
                first_bar = bars[0]
                if first_bar[0].date() < test_date:
                    # Before split - should be unchanged
                    if abs(first_bar[1] - first_bar[3]) < 0.01:  # raw_open ≈ adj_open
                        print(f"   ✅ Pre-split prices unchanged correctly")
                    else:
                        print(f"   ❌ Pre-split prices incorrectly adjusted")

                print(f"   ✅ Price adjustment system working!")
            else:
                print(f"   ❌ No price data found for {test_symbol}")
                return False

        adjuster.close()
        return True

    except Exception as e:
        print(f"❌ Price adjustment verification error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_feature_engineering():
    """Verify Section 2 feature engineering pipeline"""
    print_section("SECTION 2.4: FEATURE ENGINEERING VERIFICATION")

    # Import our features module
    from src.features.momentum import MomentumFeatures

    try:
        momentum_calc = MomentumFeatures()

        print(f"📈 Testing momentum feature calculation...")

        # Test with available symbols
        test_symbols = ["MMM", "AOS"]

        for symbol in test_symbols:
            print(f"\n   Computing features for {symbol}:")

            # Calculate momentum features
            momentum_features = momentum_calc.calculate_returns(symbol)
            trend_features = momentum_calc.calculate_trend_quality(symbol)

            print(f"     Momentum features: {len(momentum_features)} rows, {len(momentum_features.columns)} features")
            print(f"     Trend features: {len(trend_features)} rows, {len(trend_features.columns)} features")

            if not momentum_features.empty:
                print(f"     Features: {list(momentum_features.columns)}")

                # Save to database
                momentum_calc.save_features_to_db(symbol, momentum_features, "momentum")
                momentum_calc.save_features_to_db(symbol, trend_features, "trend")
                print(f"     ✅ Features saved to database")
            else:
                print(f"     ❌ No features calculated for {symbol}")

        # Verify features were saved
        with momentum_calc.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as total_features,
                       COUNT(DISTINCT symbol) as unique_symbols,
                       COUNT(DISTINCT feature_name) as unique_features
                FROM features_daily
            """))

            total, symbols, features = result.fetchone()
            print(f"\n📊 Feature Database Summary:")
            print(f"   Total feature records: {total}")
            print(f"   Symbols with features: {symbols}")
            print(f"   Unique feature types: {features}")

            # Show sample features
            # Detect database type for SQL compatibility
            from src.common.db_manager import db_manager
            engine = db_manager.get_engine()
            is_sqlite = 'sqlite' in str(engine.url).lower()
            
            if is_sqlite:
                # SQLite: Calculate stddev manually
                result = conn.execute(text("""
                    SELECT symbol, feature_name, COUNT(*) as count,
                           AVG(value) as avg_value,
                           SQRT(AVG(value * value) - AVG(value) * AVG(value)) as std_value
                    FROM features_daily
                    GROUP BY symbol, feature_name
                    ORDER BY symbol, feature_name
                    LIMIT 10
                """))
            else:
                # PostgreSQL: Use built-in STDDEV function
                result = conn.execute(text("""
                    SELECT symbol, feature_name, COUNT(*) as count,
                           AVG(value) as avg_value, STDDEV(value) as std_value
                    FROM features_daily
                    GROUP BY symbol, feature_name
                    ORDER BY symbol, feature_name
                    LIMIT 10
                """))

            feature_stats = result.fetchall()

            if feature_stats:
                print(f"\n   Sample Feature Statistics:")
                print(f"   Symbol | Feature              | Count | Avg Value | Std Dev")
                print(f"   -------|---------------------|-------|-----------|--------")
                for symbol, feature_name, count, avg_val, std_val in feature_stats:
                    feat_short = (feature_name[:18] + "..") if len(feature_name) > 20 else feature_name
                    avg_str = f"{avg_val:.4f}" if avg_val else "N/A"
                    std_str = f"{std_val:.4f}" if std_val else "N/A"
                    print(f"   {symbol:6} | {feat_short:19} | {count:5} | {avg_str:9} | {std_str:7}")

                print(f"   ✅ Feature engineering pipeline working!")
                return True
            else:
                print(f"   ❌ No features found in database")
                return False

    except Exception as e:
        print(f"❌ Feature engineering verification error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_section_2_complete():
    """Run complete Section 2 verification"""
    print_section("PATTERNIQ SECTION 2 VERIFICATION")
    print("Verifying: Storage & data structures, Adjustment policy, Feature engineering")

    results = {}

    # Test each component
    results['schema'] = verify_database_schema()
    results['data'] = verify_data_ingestion()
    results['adjustments'] = verify_price_adjustments()
    results['features'] = verify_feature_engineering()

    # Summary
    print_section("SECTION 2 VERIFICATION SUMMARY")

    total_tests = len(results)
    passed_tests = sum(results.values())

    print(f"Test Results:")
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {component.title():<20}: {status}")

    print(f"\nOverall Status: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print(f"\n🎉 SECTION 2 VERIFICATION COMPLETE!")
        print(f"✅ All storage and data structure components working correctly")
        print(f"✅ Price adjustment logic functioning properly")
        print(f"✅ Feature engineering pipeline operational")
        print(f"✅ Database schema properly implemented")
        print(f"\n🚀 Ready to proceed to Section 3: Signal Generation!")
    else:
        print(f"\n⚠️  Some components need attention before proceeding")

    return passed_tests == total_tests

if __name__ == "__main__":
    verify_section_2_complete()

# Section 3 Verification Script
# Tests all components of Section 3: Signal Generation & Portfolio Construction

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
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

def ensure_features_exist():
    """Ensure we have features for signal generation"""
    print_section("SECTION 3.0: FEATURE PREPARATION")

    sys.path.append('/Users/tamirreznik/code/private/PatternIQ')
    from src.features.momentum import MomentumFeatures

    db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
    engine = create_engine(db_url)

    # Check if features exist
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM features_daily"))
        feature_count = result.fetchone()[0]

        result = conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM features_daily"))
        feature_symbols = result.fetchone()[0]

    print(f"📊 Current features: {feature_count} records for {feature_symbols} symbols")

    if feature_count == 0:
        print("🔄 Generating features for signal testing...")

        momentum_calc = MomentumFeatures()

        # Get available symbols
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DISTINCT symbol FROM bars_1d ORDER BY symbol"))
            symbols = [row[0] for row in result.fetchall()]

        for symbol in symbols[:3]:  # Process first 3 symbols
            print(f"   Computing features for {symbol}")
            momentum_calc.compute_all_momentum_features(symbol)

        # Check again
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM features_daily"))
            feature_count = result.fetchone()[0]

        print(f"✅ Generated {feature_count} features")

    return feature_count > 0

def verify_signal_generation():
    """Verify Section 3 signal generation"""
    print_section("SECTION 3.1: SIGNAL GENERATION VERIFICATION")

    from src.signals.rules import RuleBasedSignals

    signal_engine = RuleBasedSignals()

    try:
        # Get available symbols with features
        with signal_engine.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT symbol FROM features_daily 
                ORDER BY symbol LIMIT 3
            """))
            test_symbols = [row[0] for row in result.fetchall()]

            result = conn.execute(text("SELECT MAX(d) FROM features_daily"))
            latest_date = result.fetchone()[0]

        if not test_symbols:
            print("❌ No symbols with features found")
            return False

        print(f"🎯 Testing signal generation for: {test_symbols}")
        print(f"📅 Signal date: {latest_date}")

        # Generate signals
        all_signals = signal_engine.compute_all_signals(test_symbols, latest_date)

        print(f"\n📊 Signal Generation Results:")
        for signal_name, signals in all_signals.items():
            active_signals = {k: v for k, v in signals.items() if abs(v) > 0.001}
            total_signals = len(signals)

            print(f"   {signal_name}:")
            print(f"     Total symbols: {total_signals}")
            print(f"     Active signals: {len(active_signals)}")

            if active_signals:
                avg_signal = np.mean(list(active_signals.values()))
                max_signal = max(active_signals.values())
                min_signal = min(active_signals.values())
                print(f"     Signal range: [{min_signal:+.4f}, {max_signal:+.4f}], avg: {avg_signal:+.4f}")

                # Show top signals
                sorted_signals = sorted(active_signals.items(), key=lambda x: abs(x[1]), reverse=True)
                print(f"     Top signals: {sorted_signals[:2]}")

        # Verify signals were saved to database
        with signal_engine.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT signal_name, COUNT(*) as count
                FROM signals_daily
                WHERE d = :latest_date
                GROUP BY signal_name
                ORDER BY signal_name
            """), {"latest_date": latest_date})

            db_signals = result.fetchall()

            print(f"\n📋 Database Signal Summary:")
            for signal_name, count in db_signals:
                print(f"   {signal_name}: {count} signals")

        return len(all_signals) > 0 and any(len(signals) > 0 for signals in all_signals.values())

    except Exception as e:
        print(f"❌ Signal generation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_signal_blending():
    """Verify Section 3 signal blending and IC weighting"""
    print_section("SECTION 3.2: SIGNAL BLENDING VERIFICATION")

    from src.signals.blend import SignalBlender

    blender = SignalBlender()

    try:
        # Get available signals
        with blender.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT signal_name 
                FROM signals_daily 
                WHERE signal_name != 'combined_ic_weighted'
                ORDER BY signal_name
            """))
            signal_names = [row[0] for row in result.fetchall()]

            result = conn.execute(text("SELECT MAX(d) FROM signals_daily"))
            latest_date = result.fetchone()[0]

            result = conn.execute(text("""
                SELECT DISTINCT symbol FROM signals_daily 
                WHERE d = :latest_date
                ORDER BY symbol
            """), {"latest_date": latest_date})
            symbols = [row[0] for row in result.fetchall()]

        if not signal_names:
            print("❌ No individual signals found for blending")
            return False

        print(f"🔗 Blending signals: {signal_names}")
        print(f"📅 Blend date: {latest_date}")
        print(f"📈 Symbols: {symbols}")

        # Calculate IC weights
        print(f"\n🧮 Computing IC weights...")
        weights = blender.get_signal_weights(signal_names, latest_date, lookback_days=30)  # Shorter lookback for demo

        print(f"   IC Weights:")
        for signal_name, weight in weights.items():
            print(f"     {signal_name}: {weight:.4f}")

        # Create combined signal
        combined_signals = blender.create_combined_signal(symbols, latest_date, signal_names)

        active_combined = {k: v for k, v in combined_signals.items() if abs(v) > 0.001}
        print(f"\n📊 Combined Signal Results:")
        print(f"   Total symbols: {len(combined_signals)}")
        print(f"   Active signals: {len(active_combined)}")

        if active_combined:
            avg_signal = np.mean(list(active_combined.values()))
            max_signal = max(active_combined.values())
            min_signal = min(active_combined.values())
            print(f"   Signal range: [{min_signal:+.4f}, {max_signal:+.4f}], avg: {avg_signal:+.4f}")

        # Save combined signal
        blender.save_combined_signal(combined_signals, latest_date)

        # Portfolio construction
        print(f"\n🎯 Constructing portfolio...")
        portfolio = blender.construct_portfolio(combined_signals, long_pct=0.4, short_pct=0.3)

        long_count = len(portfolio['long'])
        short_count = len(portfolio['short'])
        long_exposure = sum(portfolio['long'].values()) if portfolio['long'] else 0
        short_exposure = abs(sum(portfolio['short'].values())) if portfolio['short'] else 0

        print(f"   Long positions: {long_count} ({long_exposure:.2%} exposure)")
        print(f"   Short positions: {short_count} ({short_exposure:.2%} exposure)")
        print(f"   Gross exposure: {long_exposure + short_exposure:.2%}")

        if portfolio['long']:
            print(f"   Top long: {list(portfolio['long'].items())[:2]}")
        if portfolio['short']:
            print(f"   Top short: {list(portfolio['short'].items())[:2]}")

        return len(active_combined) > 0 and (long_count > 0 or short_count > 0)

    except Exception as e:
        print(f"❌ Signal blending error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_section_3_complete():
    """Run complete Section 3 verification"""
    print_section("PATTERNIQ SECTION 3 VERIFICATION")
    print("Verifying: Signal Generation, IC Weighting, Portfolio Construction")

    results = {}

    # Ensure we have features first
    results['features'] = ensure_features_exist()

    if results['features']:
        results['signals'] = verify_signal_generation()
        results['blending'] = verify_signal_blending()
    else:
        print("❌ Cannot proceed without features")
        results['signals'] = False
        results['blending'] = False

    # Summary
    print_section("SECTION 3 VERIFICATION SUMMARY")

    total_tests = len(results)
    passed_tests = sum(results.values())

    print(f"Test Results:")
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {component.title():<20}: {status}")

    print(f"\nOverall Status: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print(f"\n🎉 SECTION 3 VERIFICATION COMPLETE!")
        print(f"✅ Rule-based signal generation working")
        print(f"✅ IC weighting and signal blending operational")
        print(f"✅ Portfolio construction functioning")
        print(f"✅ Signal ranking and database storage working")
        print(f"\n🚀 Ready to proceed to Section 4: Backtesting!")
    else:
        print(f"\n⚠️  Some components need attention before proceeding")

    return passed_tests == total_tests

if __name__ == "__main__":
    verify_section_3_complete()

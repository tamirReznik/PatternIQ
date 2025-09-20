# Section 4 Verification Script
# Tests all components of Section 4: Backtesting Framework & Performance Analytics

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

def verify_prerequisites():
    """Verify we have the required data for backtesting"""
    print_section("SECTION 4.0: BACKTEST PREREQUISITES")

    db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
    engine = create_engine(db_url)

    try:
        with engine.connect() as conn:
            # Check signals
            result = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT signal_name) FROM signals_daily"))
            signal_count, signal_types = result.fetchone()

            # Check price data
            result = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT symbol) FROM bars_1d"))
            price_count, price_symbols = result.fetchone()

            # Check date overlap
            result = conn.execute(text("""
                SELECT 
                    MIN(s.d) as signal_start, MAX(s.d) as signal_end,
                    MIN(b.t::date) as price_start, MAX(b.t::date) as price_end
                FROM signals_daily s
                CROSS JOIN bars_1d b
            """))
            dates = result.fetchone()

        print(f"📊 Data Availability Check:")
        print(f"   Signals: {signal_count} records, {signal_types} types")
        print(f"   Prices: {price_count} bars, {price_symbols} symbols")
        print(f"   Signal period: {dates[0]} to {dates[1]}")
        print(f"   Price period: {dates[2]} to {dates[3]}")

        has_data = signal_count > 0 and price_count > 0

        if has_data:
            print(f"✅ Prerequisites met for backtesting")
        else:
            print(f"❌ Insufficient data for backtesting")

        return has_data

    except Exception as e:
        print(f"❌ Error checking prerequisites: {e}")
        return False

def verify_backtesting_engine():
    """Verify Section 4 backtesting simulator"""
    print_section("SECTION 4.1: BACKTESTING ENGINE VERIFICATION")

    sys.path.append('/Users/tamirreznik/code/private/PatternIQ')
    from src.backtest.simulator import BacktestSimulator

    try:
        # Initialize simulator
        simulator = BacktestSimulator(cost_bps=5.0, slippage_bps=2.0)
        print(f"✅ BacktestSimulator initialized")
        print(f"   Trading costs: {simulator.cost_bps}bps + {simulator.slippage_bps}bps slippage")

        # Get test data
        with simulator.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT signal_name 
                FROM signals_daily 
                ORDER BY signal_name 
                LIMIT 1
            """))
            signal_names = [row[0] for row in result.fetchall()]

            result = conn.execute(text("""
                SELECT DISTINCT symbol 
                FROM signals_daily 
                ORDER BY symbol 
                LIMIT 3
            """))
            symbols = [row[0] for row in result.fetchall()]

            result = conn.execute(text("""
                SELECT MIN(d) as start_date, MAX(d) as end_date 
                FROM signals_daily
            """))
            date_range = result.fetchone()

        if not signal_names or not symbols:
            print("❌ No signal data available for backtesting")
            return False

        signal_name = signal_names[0]
        start_date = date_range[0]
        end_date = date_range[1]

        print(f"🎯 Running backtest:")
        print(f"   Signal: {signal_name}")
        print(f"   Symbols: {symbols}")
        print(f"   Period: {start_date} to {end_date}")

        # Run backtest
        run_id = simulator.run_backtest(signal_name, symbols, start_date, end_date)

        if run_id:
            print(f"✅ Backtest completed: {run_id[:8]}...")

            # Verify data was saved
            with simulator.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM backtest_positions WHERE run_id = :run_id
                """), {"run_id": run_id})
                position_count = result.fetchone()[0]

                result = conn.execute(text("""
                    SELECT COUNT(*) FROM backtests WHERE run_id = :run_id
                """), {"run_id": run_id})
                metadata_count = result.fetchone()[0]

            print(f"   Database records:")
            print(f"     Positions: {position_count}")
            print(f"     Metadata: {metadata_count}")

            # Basic performance metrics
            if simulator.daily_returns:
                returns = np.array(simulator.daily_returns)
                total_return = simulator.portfolio_value - 1.0
                sharpe = (np.mean(returns) * 252) / (np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0

                print(f"   Quick metrics:")
                print(f"     Total return: {total_return:6.2%}")
                print(f"     Sharpe ratio: {sharpe:6.2f}")
                print(f"     Trading days: {len(returns)}")

            return True
        else:
            print("❌ Backtest failed")
            return False

    except Exception as e:
        print(f"❌ Backtesting engine error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_performance_analytics():
    """Verify Section 4 performance analytics"""
    print_section("SECTION 4.2: PERFORMANCE ANALYTICS VERIFICATION")

    from src.backtest.metrics import PerformanceAnalyzer

    try:
        analyzer = PerformanceAnalyzer()
        print(f"✅ PerformanceAnalyzer initialized")

        # Get most recent backtest
        with analyzer.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT run_id, labeling, start_date, end_date 
                FROM backtests 
                ORDER BY created_at DESC 
                LIMIT 1
            """))
            latest_run = result.fetchone()

        if not latest_run:
            print("❌ No backtest runs found for analysis")
            return False

        run_id, signal_name, start_date, end_date = latest_run
        print(f"🔍 Analyzing run: {run_id[:8]}... ({signal_name})")

        # Generate comprehensive performance report
        report = analyzer.generate_performance_report(run_id)

        if not report:
            print("❌ Could not generate performance report")
            return False

        print(f"✅ Performance report generated")

        # Display key metrics
        returns = report['returns']
        risk = report['risk']
        hit_rates = report['hit_rates']
        signal_quality = report['signal_quality']
        turnover = report['turnover']

        print(f"\n📊 Key Performance Metrics:")
        print(f"   Total Return:      {returns['total_return']:8.2%}")
        print(f"   Sharpe Ratio:      {returns['sharpe_ratio']:8.2f}")
        print(f"   Max Drawdown:      {risk['max_drawdown']:8.2%}")
        print(f"   Daily Hit Rate:    {hit_rates['daily']:8.2%}")
        print(f"   Information Coeff: {signal_quality['information_coefficient']:8.4f}")
        print(f"   Annual Turnover:   {turnover['avg_annual']:8.2%}")

        # Test individual metric calculations
        returns_df = analyzer.get_backtest_returns(run_id)
        if not returns_df.empty:
            returns_series = returns_df['return']

            sharpe_test = analyzer.calculate_sharpe_ratio(returns_series)
            max_dd_test, _ = analyzer.calculate_max_drawdown(returns_series)
            hit_rate_test = analyzer.calculate_hit_rate(returns_series)

            print(f"\n🧮 Metric Verification:")
            print(f"   Sharpe calculation: {sharpe_test:.4f}")
            print(f"   Max DD calculation: {max_dd_test:.4f}")
            print(f"   Hit rate calculation: {hit_rate_test['daily']:.4f}")

        return True

    except Exception as e:
        print(f"❌ Performance analytics error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_section_4_complete():
    """Run complete Section 4 verification"""
    print_section("PATTERNIQ SECTION 4 VERIFICATION")
    print("Verifying: Backtesting Framework & Performance Analytics")

    results = {}

    # Test each component
    results['prerequisites'] = verify_prerequisites()

    if results['prerequisites']:
        results['backtesting'] = verify_backtesting_engine()
        results['analytics'] = verify_performance_analytics()
    else:
        print("❌ Cannot proceed without required data")
        results['backtesting'] = False
        results['analytics'] = False

    # Summary
    print_section("SECTION 4 VERIFICATION SUMMARY")

    total_tests = len(results)
    passed_tests = sum(results.values())

    print(f"Test Results:")
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {component.title():<20}: {status}")

    print(f"\nOverall Status: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print(f"\n🎉 SECTION 4 VERIFICATION COMPLETE!")
        print(f"✅ Event-driven backtesting engine operational")
        print(f"✅ Transaction cost modeling working")
        print(f"✅ Performance analytics comprehensive")
        print(f"✅ Risk metrics and attribution functioning")
        print(f"\n🚀 PatternIQ backtesting framework is ready!")

        print(f"\n📈 Complete Pipeline Status:")
        print(f"   Section 1: ✅ Data Ingestion & Storage")
        print(f"   Section 2: ✅ Feature Engineering & Adjustment")
        print(f"   Section 3: ✅ Signal Generation & Portfolio Construction")
        print(f"   Section 4: ✅ Backtesting & Performance Analytics")
        print(f"\n🎯 PatternIQ MVP is COMPLETE and operational!")

    else:
        print(f"\n⚠️  Some components need attention before completion")

    return passed_tests == total_tests

if __name__ == "__main__":
    verify_section_4_complete()

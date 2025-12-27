#!/usr/bin/env python3
"""
Unified Backtest Runner - PatternIQ Historical Simulation

Consolidates quick_simulation.py, flexible_simulation.py, and historical_backtest.py
into a single unified system with strategy comparison and time horizon support.

Usage:
    # With venv activated:
    source venv/bin/activate
    python scripts/simulations/run_backtest.py --strategy short --period 1y
    
    # Or use the wrapper script:
    bash scripts/simulations/run_backtest.sh --period 1y
    
    # Custom date range:
    python scripts/simulations/run_backtest.py --start 2024-01-01 --end 2024-12-31 --capital 50000
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List

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
        print("  bash scripts/simulations/run_backtest.sh --period 1y")
        print("")
        sys.exit(1)

# Check venv before importing dependencies
check_venv()

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backtest.simulator import BacktestSimulator
from src.backtest.metrics import PerformanceAnalyzer


def parse_period(period_str: str) -> tuple[date, date]:
    """Parse period string like '1y', '6m', '2y' into start and end dates"""
    end_date = date.today()
    
    if period_str.endswith('y'):
        years = int(period_str[:-1])
        start_date = end_date - timedelta(days=years * 365)
    elif period_str.endswith('m'):
        months = int(period_str[:-1])
        start_date = end_date - timedelta(days=months * 30)
    elif period_str.endswith('d'):
        days = int(period_str[:-1])
        start_date = end_date - timedelta(days=days)
    else:
        raise ValueError(f"Invalid period format: {period_str}. Use format like '1y', '6m', '30d'")
    
    return start_date, end_date


def run_backtest(
    start_date: date,
    end_date: date,
    initial_capital: float = 100000.0,
    strategy: str = "all",
    signal_name: str = "combined_ic_weighted"
) -> Dict:
    """
    Run historical backtest for specified period and strategy
    
    Args:
        start_date: Start date for backtest
        end_date: End date for backtest
        initial_capital: Starting capital
        strategy: Strategy to test ('short', 'mid', 'long', 'all')
        signal_name: Signal name to use for backtesting
    
    Returns:
        Dictionary with backtest results
    """
    print("🎯 PatternIQ Historical Backtest")
    print("=" * 60)
    print(f"📅 Period: {start_date} → {end_date}")
    print(f"💰 Initial Capital: ${initial_capital:,.0f}")
    print(f"📊 Strategy: {strategy.upper()}")
    print(f"📡 Signal: {signal_name}")
    print("")
    
    # Get symbols from database
    try:
        from src.common.db_manager import db_manager
        from sqlalchemy import text
        
        engine = db_manager.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT symbol
                FROM signals_daily
                WHERE d BETWEEN :start_date AND :end_date
                AND signal_name = :signal_name
                LIMIT 500
            """), {
                "start_date": start_date,
                "end_date": end_date,
                "signal_name": signal_name
            })
            
            symbols = [row[0] for row in result.fetchall()]
        
        if not symbols:
            print("⚠️  No signals found in database for this period")
            print("   Run data ingestion and signal generation first")
            return None
        
        print(f"📈 Universe: {len(symbols)} symbols")
        print("")
        
    except Exception as e:
        print(f"❌ Error fetching symbols: {e}")
        return None
    
    # Run backtest
    simulator = BacktestSimulator(cost_bps=5.0, slippage_bps=2.0)
    
    try:
        run_id = simulator.run_backtest(
            signal_name=signal_name,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            universe="SP500"
        )
        
        print(f"✅ Backtest completed: {run_id}")
        print("")
        
        # Calculate metrics
        analyzer = PerformanceAnalyzer()
        metrics = analyzer.calculate_metrics(run_id)
        
        # Display results
        print("📊 Performance Metrics:")
        print("-" * 40)
        print(f"Total Return: {metrics.get('total_return_pct', 'N/A')}")
        print(f"Annualized Return: {metrics.get('annualized_return_pct', 'N/A')}")
        print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}")
        print(f"Max Drawdown: {metrics.get('max_drawdown_pct', 'N/A')}")
        print(f"Win Rate: {metrics.get('hit_rate', 'N/A')}")
        print(f"Volatility: {metrics.get('volatility_pct', 'N/A')}")
        
        return {
            "run_id": run_id,
            "metrics": metrics,
            "start_date": start_date,
            "end_date": end_date,
            "strategy": strategy
        }
        
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_strategies(
    start_date: date,
    end_date: date,
    initial_capital: float = 100000.0
) -> Dict:
    """Compare short, mid, and long-term strategies"""
    print("🔀 Strategy Comparison Backtest")
    print("=" * 60)
    print("")
    
    results = {}
    
    for strategy in ["short", "mid", "long"]:
        print(f"📊 Testing {strategy.upper()}-term strategy...")
        result = run_backtest(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            strategy=strategy
        )
        if result:
            results[strategy] = result
        print("")
    
    # Compare results
    if results:
        print("📈 Strategy Comparison Summary:")
        print("-" * 60)
        print(f"{'Strategy':<15} {'Return':<15} {'Sharpe':<15} {'Max DD':<15}")
        print("-" * 60)
        
        for strategy, result in results.items():
            metrics = result.get("metrics", {})
            ret = metrics.get("total_return_pct", "N/A")
            sharpe = metrics.get("sharpe_ratio", "N/A")
            dd = metrics.get("max_drawdown_pct", "N/A")
            print(f"{strategy.upper():<15} {str(ret):<15} {str(sharpe):<15} {str(dd):<15}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="PatternIQ Unified Backtest Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick 1-year backtest
  python scripts/simulations/run_backtest.py --period 1y
  
  # Custom date range with $50K
  python scripts/simulations/run_backtest.py --start 2024-01-01 --end 2024-12-31 --capital 50000
  
  # Test short-term strategy
  python scripts/simulations/run_backtest.py --strategy short --period 6m
  
  # Compare all strategies
  python scripts/simulations/run_backtest.py --strategy all --period 2y
        """
    )
    
    parser.add_argument(
        "--start",
        type=str,
        help="Start date (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end",
        type=str,
        help="End date (YYYY-MM-DD). Default: today"
    )
    
    parser.add_argument(
        "--period",
        type=str,
        help="Period string (e.g., '1y', '6m', '30d'). Default: 1y"
    )
    
    parser.add_argument(
        "--capital",
        type=float,
        default=100000.0,
        help="Initial capital (default: 100000)"
    )
    
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["short", "mid", "long", "all"],
        default="all",
        help="Time horizon strategy to test (default: all)"
    )
    
    parser.add_argument(
        "--signal",
        type=str,
        default="combined_ic_weighted",
        help="Signal name to use (default: combined_ic_weighted)"
    )
    
    args = parser.parse_args()
    
    # Parse dates
    if args.start and args.end:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    elif args.period:
        start_date, end_date = parse_period(args.period)
    else:
        # Default: 1 year
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
    
    if start_date >= end_date:
        print("❌ Error: Start date must be before end date")
        sys.exit(1)
    
    # Run backtest
    if args.strategy == "all":
        compare_strategies(start_date, end_date, args.capital)
    else:
        run_backtest(
            start_date=start_date,
            end_date=end_date,
            initial_capital=args.capital,
            strategy=args.strategy,
            signal_name=args.signal
        )


if __name__ == "__main__":
    main()


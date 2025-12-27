#!/usr/bin/env python3
"""
Retrospective Simulation Runner
Runs day-by-day retrospective analysis of trading bot decisions
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
        print("  bash scripts/simulations/run_retrospective.sh --strategy mid --years 5")
        print("")
        sys.exit(1)

# Check venv before importing dependencies
check_venv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtest.retrospective_simulator import RetrospectiveSimulator
from src.backtest.report_generator import ReportGenerator


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def parse_date_range(years: Optional[int], start: Optional[str], end: Optional[str]) -> tuple:
    """Parse date range from arguments"""
    if years:
        end_date = date.today()
        start_date = end_date - timedelta(days=years * 365)
        return start_date, end_date
    
    if start and end:
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        return start_date, end_date
    
    # Default: 5 years
    end_date = date.today()
    start_date = end_date - timedelta(days=5 * 365)
    return start_date, end_date


def main():
    parser = argparse.ArgumentParser(
        description='Run retrospective simulation of trading bot decisions'
    )
    parser.add_argument(
        '--years',
        type=int,
        help='Number of years to simulate (default: 5)'
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
        '--capital',
        type=float,
        default=100000.0,
        help='Initial capital (default: 100000)'
    )
    parser.add_argument(
        '--strategy',
        type=str,
        choices=['short', 'mid', 'long', 'all'],
        default='all',
        help='Time horizon strategy filter (default: all)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output filename prefix (optional)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose logging'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger("RetrospectiveRunner")
    
    # Parse date range
    start_date, end_date = parse_date_range(args.years, args.start, args.end)
    
    logger.info(f"Starting retrospective simulation")
    logger.info(f"  Period: {start_date} to {end_date}")
    logger.info(f"  Initial Capital: ${args.capital:,.2f}")
    logger.info(f"  Strategy: {args.strategy}")
    
    # Create simulator
    simulator = RetrospectiveSimulator(
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.capital,
        time_horizon_filter=args.strategy if args.strategy != 'all' else None
    )
    
    # Run simulation
    logger.info("Running day-by-day simulation...")
    results = simulator.run_day_by_day()
    
    if results['status'] != 'completed':
        logger.error(f"Simulation failed: {results.get('message', 'Unknown error')}")
        sys.exit(1)
    
    # Generate reports
    logger.info("Generating reports...")
    report_generator = ReportGenerator()
    reports = report_generator.generate_all_reports(results)
    
    # Print summary
    profitability = results['profitability_metrics']
    decision_quality = results['decision_quality_metrics']
    report_stats = results.get('report_statistics', {})
    
    print("\n" + "=" * 60)
    print("RETROSPECTIVE SIMULATION RESULTS")
    print("=" * 60)
    print(f"\nSimulation Period: {start_date} to {end_date}")
    print(f"Trading Days: {results['simulation_period']['trading_days']}")
    
    print("\n📊 Profitability Metrics:")
    print(f"  Total Return: {profitability['total_return']:.2%}")
    print(f"  Annualized Return: {profitability['annualized_return']:.2%}")
    print(f"  Sharpe Ratio: {profitability['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {profitability['max_drawdown']:.2%}")
    print(f"  Win Rate: {profitability['win_rate']:.2%}")
    print(f"  Profit Factor: {profitability['profit_factor']:.2f}")
    
    print("\n🎯 Decision Quality Metrics:")
    print(f"  Decision Accuracy: {decision_quality['accuracy']:.2%}")
    print(f"  Signal Correlation: {decision_quality['signal_correlation']:.2f}")
    print(f"  False Positive Rate: {decision_quality['false_positive_rate']:.2%}")
    print(f"  False Negative Rate: {decision_quality['false_negative_rate']:.2%}")
    print(f"  Timing Quality: {decision_quality['timing_quality']:.2f}")
    
    print("\n📋 Report Statistics:")
    print(f"  Reports generated on-the-fly: {report_stats.get('reports_generated', 0)}")
    print(f"  Reports loaded from cache: {report_stats.get('reports_loaded', 0)}")
    print(f"  Days with signals: {report_stats.get('days_with_signals', 0)}")
    print(f"  Days without signals: {report_stats.get('days_without_signals', 0)}")
    
    print("\n📁 Reports Generated:")
    for report_type, filepath in reports.items():
        print(f"  {report_type.upper()}: {filepath}")
    
    print("\n✅ Simulation completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()


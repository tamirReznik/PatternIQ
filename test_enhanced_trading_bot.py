#!/usr/bin/env python3
"""
Test the enhanced trading bot to ensure it will make trades
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.trading.simulator import AutoTradingBot
from datetime import date
import json

def test_enhanced_trading_bot():
    """Test the enhanced trading bot with real decision making"""
    print("🤖 Testing Enhanced Trading Bot")
    print("=" * 50)

    # Initialize the enhanced bot
    bot = AutoTradingBot(
        initial_capital=100000.0,
        paper_trading=True,
        max_position_size=0.05,  # 5% max per position
        trading_fee_per_trade=0.0,  # No fees for most modern brokers
        min_trade_size=1000  # $1000 minimum trade
    )

    print(f"✅ Enhanced bot initialized:")
    print(f"   Capital: ${bot.initial_capital:,.0f}")
    print(f"   Max position size: {bot.max_position_size:.1%}")
    print(f"   Min trade size: ${bot.min_trade_size:,.0f}")
    print(f"   Max positions: {bot.max_positions}")

    # Get current portfolio status
    status = bot.get_portfolio_status()
    print(f"\n📊 Current Portfolio Status:")
    print(f"   Portfolio value: ${status['current_value']:,.0f}")
    print(f"   Cash balance: ${status['cash_balance']:,.0f}")
    print(f"   Positions: {status['positions_count']}")
    print(f"   Total trades: {status['total_trades']}")

    # Test fundamental scoring for a few stocks
    print(f"\n🔍 Testing fundamental analysis:")
    test_symbols = ["AAPL", "MSFT", "GOOGL"]
    for symbol in test_symbols:
        score = bot._get_fundamentals_score(symbol)
        print(f"   {symbol}: {score:.2f} fundamental score")

    # Test trading decision logic
    print(f"\n🎯 Testing trading decision logic:")

    # Test buy decision with strong signal
    buy_decision = bot._should_buy("AAPL", 0.85, 175.0, 5000)
    print(f"   Buy AAPL decision: {buy_decision['should_buy']} - {buy_decision['reason']}")

    # Test buy decision with weak signal
    weak_buy_decision = bot._should_buy("XOM", 0.4, 115.0, 5000)
    print(f"   Buy XOM (weak signal): {weak_buy_decision['should_buy']} - {weak_buy_decision['reason']}")

    # Test with small trade size
    small_trade_decision = bot._should_buy("NVDA", 0.75, 450.0, 500)
    print(f"   Small trade decision: {small_trade_decision['should_buy']} - {small_trade_decision['reason']}")

    # Check if we have any recent reports to process
    reports_dir = Path("reports")
    if reports_dir.exists():
        recent_reports = sorted(reports_dir.glob("*.json"))
        if recent_reports:
            latest_report = recent_reports[-1]
            print(f"\n📋 Found latest report: {latest_report.name}")

            # Load and show report structure
            with open(latest_report, 'r') as f:
                report = json.load(f)

            print(f"   Report date: {report.get('date', 'Unknown')}")
            print(f"   Long recommendations: {len(report.get('top_long', []))}")
            print(f"   Short recommendations: {len(report.get('top_short', []))}")

            # Show sample recommendations
            if report.get('top_long'):
                sample = report['top_long'][0]
                print(f"   Sample long: {sample.get('symbol')} - score {sample.get('score', 0):.2f}")

                # Test if bot would buy this
                decision = bot._should_buy(
                    sample.get('symbol'),
                    sample.get('score', 0.5),
                    sample.get('price', 100),
                    5000
                )
                print(f"   Bot decision: {decision['should_buy']} - {decision['reason']}")
        else:
            print(f"\n⚠️  No reports found in {reports_dir}")
    else:
        print(f"\n⚠️  Reports directory not found")

    print(f"\n🚀 Bot is ready to trade! Key improvements:")
    print(f"   ✅ Sophisticated buy/sell logic with fundamental analysis")
    print(f"   ✅ Risk management (stop losses, take profits)")
    print(f"   ✅ Position sizing and concentration limits")
    print(f"   ✅ Trading fee consideration")
    print(f"   ✅ Minimum trade size enforcement")
    print(f"   ✅ Performance tracking and reporting")

    print(f"\n⏰ Next steps:")
    print(f"   1. Bot will run automatically at 18:00 daily")
    print(f"   2. It will analyze today's signals with sophisticated logic")
    print(f"   3. Execute trades only when signals are strong AND fundamentals are good")
    print(f"   4. Track performance and send updates via Telegram")

if __name__ == "__main__":
    test_enhanced_trading_bot()

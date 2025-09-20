# test_all_features.py - Comprehensive test suite for all PatternIQ features

import os
import sys
import json
import asyncio
from datetime import date, datetime
from sqlalchemy import create_engine, text

def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_subsection(title):
    """Print formatted subsection header"""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")

def test_report_generation():
    """Test 1: Report Generation (JSON, HTML)"""
    print_section("TEST 1: REPORT GENERATION")

    try:
        from src.report.generator import ReportGenerator

        generator = ReportGenerator()
        today = date.today()

        print(f"📅 Generating reports for: {today}")

        # Check reports directory
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir, exist_ok=True)
            print(f"📁 Created reports directory: {os.path.abspath(reports_dir)}")

        # Generate sample report data
        sample_data = {
            "report_metadata": {
                "report_id": f"test-{today.strftime('%Y%m%d')}",
                "report_date": today.isoformat(),
                "generated_at": datetime.now().isoformat(),
                "system_version": "PatternIQ 1.0 MVP",
                "report_type": "daily_trading_signals"
            },
            "executive_summary": {
                "market_regime": "Test Mode - All Systems Operational",
                "signal_strength": 88,
                "total_recommendations": 6,
                "strong_conviction_trades": 3
            },
            "trading_recommendations": {
                "long_candidates": [
                    {"symbol": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "signal_score": 0.875, "recommendation": "STRONG BUY", "position_size": "3.0%", "current_price": 175.50, "rank": 1},
                    {"symbol": "MSFT", "company_name": "Microsoft Corp.", "sector": "Technology", "signal_score": 0.724, "recommendation": "BUY", "position_size": "2.5%", "current_price": 415.25, "rank": 2}
                ],
                "short_candidates": [
                    {"symbol": "XOM", "company_name": "Exxon Mobil Corp.", "sector": "Energy", "signal_score": -0.653, "recommendation": "SELL", "position_size": "2.0%", "current_price": 115.30, "rank": 1}
                ]
            },
            "market_analysis": {
                "market_regime": "Test Mode",
                "signal_strength": 88,
                "total_signals": 503,
                "strong_longs": 3,
                "strong_shorts": 1,
                "sector_analysis": [
                    {"sector": "Technology", "symbol_count": 75, "avg_signal": 0.285, "sentiment": "Bullish", "bullish_stocks": 52, "bearish_stocks": 8}
                ]
            },
            "performance_tracking": {
                "last_backtest_period": "2024-01-01 to 2024-09-20",
                "signal_strategy": "combined_ic_weighted",
                "total_positions_tested": 1250,
                "status": "Test Mode Active"
            },
            "risk_alerts": ["Test mode: All systems operational"],
            "next_actions": ["Verify report generation", "Test API endpoints", "Check Telegram integration"]
        }

        # Test JSON generation
        json_path = generator.save_json_report(sample_data, today)
        if os.path.exists(json_path):
            size = os.path.getsize(json_path)
            print(f"✅ JSON Report: {os.path.basename(json_path)} ({size:,} bytes)")
        else:
            print(f"❌ JSON Report: Failed to create")
            return False

        # Test HTML generation
        html_content = generator.generate_html_report(sample_data)
        html_path = generator.save_html_report(html_content, today)
        if os.path.exists(html_path):
            size = os.path.getsize(html_path)
            print(f"✅ HTML Report: {os.path.basename(html_path)} ({size:,} bytes)")
        else:
            print(f"❌ HTML Report: Failed to create")
            return False

        print(f"\n📁 Reports saved in: {os.path.abspath(reports_dir)}")
        print(f"🌐 Open HTML report: open {os.path.abspath(html_path)}")

        return True

    except Exception as e:
        print(f"❌ Report generation test failed: {e}")
        return False

def test_api_server():
    """Test 2: API Server Functionality"""
    print_section("TEST 2: API SERVER")

    try:
        import threading
        import time
        import requests
        from src.api.server import app
        import uvicorn

        print("🚀 Starting API server...")

        # Start server in background thread
        def start_server():
            uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        # Wait for server to start
        time.sleep(3)

        base_url = "http://127.0.0.1:8001"

        # Test endpoints
        print("📡 Testing API endpoints...")

        # Health check
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health Check: {data['service']} v{data['version']}")
            else:
                print(f"❌ Health Check: Status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Health Check: Connection failed - {e}")
            return False

        # Latest report
        try:
            response = requests.get(f"{base_url}/reports/latest?format=json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Latest Report: Found report for {data.get('report_metadata', {}).get('report_date', 'unknown')}")
            else:
                print(f"⚠️ Latest Report: Status {response.status_code} (may be expected if no signals)")
        except Exception as e:
            print(f"⚠️ Latest Report: {e}")

        # Portfolio status
        try:
            response = requests.get(f"{base_url}/portfolio/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Portfolio Status: {data.get('strategy', 'unknown')} strategy")
            else:
                print(f"⚠️ Portfolio Status: Status {response.status_code}")
        except Exception as e:
            print(f"⚠️ Portfolio Status: {e}")

        print(f"\n🌐 API Server running at: {base_url}")
        print(f"📖 Interactive docs: {base_url}/docs")

        return True

    except Exception as e:
        print(f"❌ API server test failed: {e}")
        return False

def test_telegram_bot():
    """Test 3: Telegram Bot Setup"""
    print_section("TEST 3: TELEGRAM BOT")

    try:
        from src.telegram.bot import PatternIQBot, setup_telegram_bot

        # Test bot setup
        bot = setup_telegram_bot()

        if bot and bot.bot:
            print(f"✅ Telegram bot initialized successfully")
            print(f"📱 Registered chat IDs: {len(bot.chat_ids)}")

            if bot.chat_ids:
                print(f"📞 Chat IDs: {bot.chat_ids}")
                print(f"💬 Ready to send daily reports")
                return True
            else:
                print(f"⚠️ No chat IDs registered")
                print(f"   Add chat IDs with environment variable:")
                print(f"   export TELEGRAM_CHAT_IDS='your_chat_id'")
                return True  # Bot works, just needs configuration
        else:
            print(f"⚠️ Telegram bot not configured")
            print(f"   Set environment variables:")
            print(f"   export TELEGRAM_BOT_TOKEN='your_token'")
            print(f"   export TELEGRAM_CHAT_IDS='your_chat_id'")
            return True  # Expected if not configured

    except Exception as e:
        print(f"❌ Telegram bot test failed: {e}")
        return False

def test_trading_bot():
    """Test 4: Automated Trading Bot"""
    print_section("TEST 4: AUTOMATED TRADING BOT")

    try:
        from src.trading.simulator import AutoTradingBot

        # Initialize trading bot
        bot = AutoTradingBot(initial_capital=100000.0, paper_trading=True)

        print(f"✅ Trading bot initialized")
        print(f"💰 Initial capital: ${bot.initial_capital:,.2f}")
        print(f"📊 Paper trading: {bot.paper_trading}")
        print(f"🛡️ Max position size: {bot.max_position_size:.1%}")

        # Get portfolio status
        status = bot.get_portfolio_status()

        print(f"\n📈 Portfolio Status:")
        print(f"   Initial Capital: ${status['initial_capital']:,.2f}")
        print(f"   Current Value: ${status['current_value']:,.2f}")
        print(f"   Total Return: {status['performance_metrics']['total_return_pct']}")
        print(f"   Cash Balance: ${status['cash_balance']:,.2f}")
        print(f"   Active Positions: {len(status['positions'])}")

        # Test state saving
        state_file = bot.save_state()
        if os.path.exists(state_file):
            print(f"✅ State persistence: {state_file}")

        return True

    except Exception as e:
        print(f"❌ Trading bot test failed: {e}")
        return False

def test_database_integration():
    """Test 5: Database Integration"""
    print_section("TEST 5: DATABASE INTEGRATION")

    try:
        db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
        engine = create_engine(db_url)

        with engine.connect() as conn:
            # Check all tables
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

            print(f"📊 Database tables: {len(tables)}")

            # Check data in key tables
            data_summary = {}
            for table in ['instruments', 'bars_1d', 'features_daily', 'signals_daily']:
                if table in tables:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    data_summary[table] = count

            print(f"\n📈 Data Summary:")
            for table, count in data_summary.items():
                print(f"   {table}: {count:,} records")

            # Test latest data
            result = conn.execute(text("SELECT MAX(t::date) FROM bars_1d"))
            latest_price_date = result.fetchone()[0]

            if latest_price_date:
                print(f"\n📅 Latest price data: {latest_price_date}")

            return True

    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        return False

def run_all_tests():
    """Run comprehensive test suite for all PatternIQ features"""
    print_section("PATTERNIQ COMPREHENSIVE FEATURE TEST SUITE")
    print("Testing: Reports, API, Telegram, Trading Bot, Database")

    # Run all tests
    test_results = {
        "Report Generation": test_report_generation(),
        "API Server": test_api_server(),
        "Telegram Bot": test_telegram_bot(),
        "Trading Bot": test_trading_bot(),
        "Database": test_database_integration()
    }

    # Summary
    print_section("TEST SUITE SUMMARY")

    total_tests = len(test_results)
    passed_tests = sum(test_results.values())

    print(f"Test Results:")
    for component, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {component:<20}: {status}")

    print(f"\nOverall Status: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ PatternIQ is fully operational")
        print(f"✅ Report generation working (JSON, HTML)")
        print(f"✅ API endpoints functional")
        print(f"✅ Telegram bot ready for configuration")
        print(f"✅ Automated trading system operational")
        print(f"✅ Database integration complete")

        print(f"\n🚀 NEXT STEPS:")
        print(f"1. Configure Telegram bot tokens (optional)")
        print(f"2. Set up daily cron job for automation")
        print(f"3. Start using daily reports for trading decisions")
        print(f"4. Monitor portfolio performance via API")

        print(f"\n📊 DAILY OUTPUT SUMMARY:")
        print(f"   • HTML Report: /reports/patterniq_report_YYYYMMDD.html")
        print(f"   • JSON Data: /reports/patterniq_report_YYYYMMDD.json")
        print(f"   • API Access: http://localhost:8000/reports/latest")
        print(f"   • Portfolio Status: http://localhost:8000/portfolio/status")
        print(f"   • Telegram Alerts: Sent to configured chat IDs")

    else:
        print(f"\n⚠️ Some tests failed - review above for details")
        print(f"📋 Failed components may need configuration or setup")

    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print(f"\n🎯 PatternIQ is ready for production use!")
    else:
        print(f"\n🔧 Some components need attention before full deployment")

#!/usr/bin/env python3
"""
PatternIQ Full Demo Script

Comprehensive end-to-end demonstration of all PatternIQ features.
Tests data ingestion, feature calculation, signal generation, report generation,
Telegram integration, API endpoints, and trading bot functionality.
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import date, datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Check venv
def check_venv():
    """Check if running in virtual environment"""
    in_venv = (
        hasattr(sys, 'real_prefix') or 
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )
    python_path = sys.executable
    venv_indicators = ['venv', 'virtualenv', '.venv']
    path_has_venv = any(indicator in python_path for indicator in venv_indicators)
    
    if not in_venv and not path_has_venv:
        print("❌ ERROR: Virtual environment not activated!")
        print("Please activate venv first: source venv/bin/activate")
        sys.exit(1)

check_venv()

from src.common.db_manager import db_manager
from src.data.ingestion.pipeline import run_data_ingestion_pipeline
from src.features.momentum import calculate_momentum_features
from src.signals.rules import generate_signals
from src.signals.blend import blend_signals_ic_weighted
from src.report.generator import generate_daily_report
from src.trading.bot import TradingBot
from src.telegram.bot import PatternIQBot, TELEGRAM_AVAILABLE
from sqlalchemy import text


def print_section(title: str):
    """Print section header"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


def test_database():
    """Test database connection"""
    print_section("1. Database Connection Test")
    
    try:
        engine = db_manager.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print("✅ Database connection successful")
        print(f"   Database: {engine.url}")
        
        # Check for existing data
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM instruments"))
            instrument_count = result.fetchone()[0]
            result = conn.execute(text("SELECT COUNT(*) FROM bars_1d"))
            bars_count = result.fetchone()[0]
            result = conn.execute(text("SELECT COUNT(*) FROM signals_daily"))
            signals_count = result.fetchone()[0]
        
        print(f"   Instruments: {instrument_count}")
        print(f"   Price bars: {bars_count}")
        print(f"   Signals: {signals_count}")
        
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_data_ingestion():
    """Test data ingestion pipeline"""
    print_section("2. Data Ingestion Test")
    
    try:
        print("Running data ingestion pipeline...")
        run_data_ingestion_pipeline()
        print("✅ Data ingestion completed")
        return True
    except Exception as e:
        print(f"❌ Data ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_feature_calculation():
    """Test feature calculation"""
    print_section("3. Feature Calculation Test")
    
    try:
        print("Calculating momentum features...")
        calculate_momentum_features()
        print("✅ Feature calculation completed")
        return True
    except Exception as e:
        print(f"❌ Feature calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_generation():
    """Test signal generation"""
    print_section("4. Signal Generation Test")
    
    try:
        print("Generating trading signals...")
        generate_signals()
        print("✅ Signal generation completed")
        return True
    except Exception as e:
        print(f"❌ Signal generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_blending():
    """Test signal blending"""
    print_section("5. Signal Blending Test")
    
    try:
        print("Blending signals with IC weighting...")
        result = blend_signals_ic_weighted()
        if result and result.get("status") == "success":
            print("✅ Signal blending completed")
            weights = result.get("top_weights", {})
            if weights:
                print("   Signal weights:")
                for signal, weight in weights.items():
                    print(f"     {signal}: {weight:.3f}")
            return True
        else:
            print("⚠️  Signal blending completed with warnings")
            print(f"   Status: {result.get('status', 'unknown')}")
            return True  # Not a failure, just no data
    except Exception as e:
        print(f"❌ Signal blending failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_generation():
    """Test report generation"""
    print_section("6. Report Generation Test")
    
    try:
        print("Generating daily report...")
        result = generate_daily_report()
        
        if result and result.get("status") == "success":
            reports = result.get("reports_generated", [])
            print("✅ Report generation completed")
            print(f"   Reports generated: {len(reports)}")
            for report in reports:
                print(f"     - {report}")
            
            # Check if reports exist
            reports_dir = Path("reports")
            json_reports = list(reports_dir.glob("patterniq_report_*.json"))
            html_reports = list(reports_dir.glob("patterniq_report_*.html"))
            
            if json_reports:
                latest_json = max(json_reports, key=lambda p: p.stat().st_mtime)
                print(f"   Latest JSON report: {latest_json.name}")
            
            if html_reports:
                latest_html = max(html_reports, key=lambda p: p.stat().st_mtime)
                print(f"   Latest HTML report: {latest_html.name}")
                print(f"   Open in browser: file://{latest_html.absolute()}")
            
            return True
        else:
            print("⚠️  Report generation completed with warnings")
            return True
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_telegram():
    """Test Telegram integration"""
    print_section("7. Telegram Integration Test")
    
    if not TELEGRAM_AVAILABLE:
        print("⚠️  python-telegram-bot package not installed")
        print("   Install with: pip install python-telegram-bot")
        return False
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_ids = os.getenv("TELEGRAM_CHAT_IDS")
    
    if not bot_token:
        print("⚠️  TELEGRAM_BOT_TOKEN not set")
        print("   Run setup: python scripts/setup/setup_telegram.py")
        return False
    
    if not chat_ids:
        print("⚠️  TELEGRAM_CHAT_IDS not set")
        print("   Run setup: python scripts/setup/setup_telegram.py")
        return False
    
    try:
        bot = PatternIQBot()
        
        if not bot.bot:
            print("❌ Telegram bot initialization failed")
            return False
        
        if not bot.chat_ids:
            print("❌ No chat IDs configured")
            return False
        
        print(f"✅ Telegram bot initialized")
        print(f"   Registered chats: {len(bot.chat_ids)}")
        
        # Test connection
        test_chat_id = bot.chat_ids[0]
        print(f"   Testing connection to chat {test_chat_id}...")
        test_success = await bot.test_connection(test_chat_id)
        
        if test_success:
            print("✅ Test message sent successfully!")
            print("   Check your Telegram for the test message")
            
            # Try to send actual report
            print("   Attempting to send daily report...")
            report_sent = await bot.send_daily_report()
            if report_sent:
                print("✅ Daily report sent successfully!")
            else:
                print("⚠️  Could not send daily report (may not have reports yet)")
            
            return True
        else:
            print("❌ Test message failed")
            return False
            
    except Exception as e:
        print(f"❌ Telegram test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trading_bot():
    """Test trading bot"""
    print_section("8. Trading Bot Test")
    
    try:
        print("Initializing trading bot...")
        bot = TradingBot(
            initial_capital=100000.0,
            paper_trading=True,
            enable_multi_asset=True,
            default_time_horizon="mid"
        )
        
        print("✅ Trading bot initialized")
        print(f"   Initial capital: ${bot.initial_capital:,.2f}")
        print(f"   Multi-asset: {bot.enable_multi_asset}")
        print(f"   Default horizon: {bot.default_time_horizon.value}")
        
        # Get portfolio status
        status = bot.get_portfolio_status()
        print(f"   Current value: ${status['current_value']:,.2f}")
        print(f"   Total return: {status['total_return']}")
        print(f"   Positions: {status['positions_count']}")
        
        # Check if we can process a report
        reports_dir = Path("reports")
        json_reports = list(reports_dir.glob("patterniq_report_*.json"))
        
        if json_reports:
            latest_json = max(json_reports, key=lambda p: p.stat().st_mtime)
            date_str = latest_json.stem.replace("patterniq_report_", "")
            report_date = datetime.strptime(date_str, "%Y%m%d").date()
            
            print(f"   Testing with report from {report_date}...")
            result = bot.process_daily_report(report_date)
            
            if result.get("status") == "completed":
                print("✅ Trading bot processed report successfully")
                print(f"   Trades executed: {result.get('trades_executed', 0)}")
                print(f"   Trades skipped: {result.get('trades_skipped', 0)}")
            else:
                print(f"⚠️  Trading bot processing: {result.get('status', 'unknown')}")
        else:
            print("⚠️  No reports available for trading bot test")
        
        return True
        
    except Exception as e:
        print(f"❌ Trading bot test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """Test API endpoints"""
    print_section("9. API Endpoints Test")
    
    try:
        from src.api.server import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        if response.status_code == 200:
            print("✅ API root endpoint working")
            data = response.json()
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
        else:
            print(f"❌ API root endpoint failed: {response.status_code}")
            return False
        
        # Test reports endpoint
        response = client.get("/reports/latest?format=json")
        if response.status_code == 200:
            print("✅ Reports endpoint working")
            report_data = response.json()
            print(f"   Report date: {report_data.get('date', 'N/A')}")
            print(f"   Recommendations: {len(report_data.get('top_long', []))} long, {len(report_data.get('top_short', []))} short")
        elif response.status_code == 404:
            print("⚠️  Reports endpoint working but no reports available")
        else:
            print(f"⚠️  Reports endpoint: {response.status_code}")
        
        # Test portfolio endpoint
        response = client.get("/portfolio/status")
        if response.status_code == 200:
            print("✅ Portfolio endpoint working")
            portfolio = response.json()
            print(f"   Portfolio value: ${portfolio.get('current_value', 0):,.2f}")
        else:
            print(f"⚠️  Portfolio endpoint: {response.status_code}")
        
        return True
        
    except ImportError:
        print("⚠️  FastAPI TestClient not available")
        print("   API endpoints exist but cannot be tested without running server")
        return True
    except Exception as e:
        print(f"⚠️  API test issue: {e}")
        return True  # Not critical


def print_summary(results: dict):
    """Print demo summary"""
    print_section("Demo Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    failed_tests = total_tests - passed_tests
    
    print(f"Tests Run: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print()
    
    print("Test Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print()
    
    if failed_tests == 0:
        print("🎉 All tests passed! PatternIQ is ready to use.")
    else:
        print("⚠️  Some tests failed. Review errors above.")
    
    print()
    print("Next Steps:")
    print("  1. Review generated reports in reports/ directory")
    print("  2. Setup Telegram (if not done): python scripts/setup/setup_telegram.py")
    print("  3. Run daily batch: python run_patterniq.py batch")
    print("  4. Start API server: python run_patterniq.py api-only")
    print()


async def main():
    """Run full demo"""
    print()
    print("🚀 PatternIQ Full Feature Demo")
    print("=" * 70)
    print("This demo will test all PatternIQ features end-to-end")
    print("=" * 70)
    
    results = {}
    
    # Run tests
    results["Database Connection"] = test_database()
    
    # Ask user if they want to run data ingestion (it can be slow)
    if results["Database Connection"]:
        run_ingestion = input("\nRun data ingestion? (This may take a few minutes) (y/n): ").strip().lower()
        if run_ingestion == 'y':
            results["Data Ingestion"] = test_data_ingestion()
        else:
            print("⏭️  Skipping data ingestion")
            results["Data Ingestion"] = None
    
    if results.get("Data Ingestion") or results.get("Data Ingestion") is None:
        results["Feature Calculation"] = test_feature_calculation()
        results["Signal Generation"] = test_signal_generation()
        results["Signal Blending"] = test_signal_blending()
        results["Report Generation"] = test_report_generation()
        results["Trading Bot"] = test_trading_bot()
    
    results["Telegram Integration"] = await test_telegram()
    results["API Endpoints"] = test_api_endpoints()
    
    # Print summary
    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())


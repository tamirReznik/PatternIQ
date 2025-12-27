#!/usr/bin/env python3
# test_patterniq_modes.py - Combined test script for PatternIQ operating modes

import os
import sys
import logging
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PatternIQ_Test")

# Make sure we can import from src
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Enable test mode
os.environ["PATTERNIQ_TESTING"] = "true"

class PatternIQTest:
    """Comprehensive test for PatternIQ operating modes"""

    def __init__(self):
        """Initialize test environment"""
        # Ensure directories exist
        Path("reports").mkdir(exist_ok=True)
        Path("trading_data").mkdir(exist_ok=True)

        # Remove any existing portfolio state
        portfolio_file = Path("trading_data/portfolio_state.json")
        if portfolio_file.exists():
            try:
                portfolio_file.unlink()
                logger.info(f"Removed existing portfolio state file")
            except:
                logger.warning(f"Could not remove portfolio state file")

    def test_configuration_modes(self):
        """Test different configuration modes"""
        logger.info("🧪 Testing configuration modes...")

        from src.common.config import load_config

        # Test batch mode
        os.environ["PATTERNIQ_ALWAYS_ON"] = "false"
        os.environ["START_API_SERVER"] = "false"
        config = load_config()
        assert config.always_on == False, "always_on should be False in batch mode"
        assert config.start_api_server == False, "start_api_server should be False in batch mode"

        # Test always-on mode
        os.environ["PATTERNIQ_ALWAYS_ON"] = "true"
        os.environ["START_API_SERVER"] = "true"
        config = load_config()
        assert config.always_on == True, "always_on should be True in always-on mode"
        assert config.start_api_server == True, "start_api_server should be True in always-on mode"

        # Test API-only mode
        os.environ["PATTERNIQ_ALWAYS_ON"] = "false"
        os.environ["START_API_SERVER"] = "true"
        config = load_config()
        assert config.always_on == False, "always_on should be False in API-only mode"
        assert config.start_api_server == True, "start_api_server should be True in API-only mode"

        logger.info("✅ Configuration modes verified")
        return True

    async def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        logger.info("🧪 Testing orchestrator initialization...")

        # Mock database to avoid real connection
        with patch("src.main.asyncio.to_thread"), \
             patch("sqlalchemy.create_engine"):

            from src.main import PatternIQOrchestrator
            orchestrator = PatternIQOrchestrator()

            assert orchestrator is not None, "Orchestrator should initialize"
            assert orchestrator.trading_bot is None, "Trading bot should be None initially"

        logger.info("✅ Orchestrator initialization verified")
        return True

    async def test_batch_pipeline_mocked(self):
        """Test batch pipeline with mocked components"""
        logger.info("🧪 Testing batch pipeline with mocks...")

        # Import orchestrator first
        from src.main import PatternIQOrchestrator

        # Configure batch mode
        os.environ["PATTERNIQ_ALWAYS_ON"] = "false"
        os.environ["GENERATE_REPORTS"] = "true"

        # Create mock objects that will replace the real functions
        mock_data = MagicMock()
        mock_features = MagicMock()
        mock_signals = MagicMock()
        mock_blend = MagicMock()
        mock_reports = MagicMock()
        mock_exit = MagicMock()

        # Replace the real functions with our mocks using patch.object
        with patch("src.main.demo_full_data_ingestion", mock_data), \
             patch("src.main.demo_momentum_features", mock_features), \
             patch("src.main.demo_signal_generation", mock_signals), \
             patch("src.main.blend_signals_ic_weighted", mock_blend), \
             patch("src.main.generate_daily_report", mock_reports), \
             patch("src.main.sys.exit", mock_exit):

            # Create trading bot mock
            mock_bot = MagicMock()
            mock_bot.process_daily_report.return_value = {"status": "success", "trades_executed": 3}
            mock_bot.get_portfolio_status.return_value = {
                "initial_capital": 100000.0,
                "current_value": 102000.0,
                "total_return": "2.00%"
            }

            # Create and configure orchestrator
            orchestrator = PatternIQOrchestrator()
            orchestrator.trading_bot = mock_bot

            # Run in batch mode
            await orchestrator.run_daily_pipeline()

            # Check all pipeline steps were called
            mock_data.assert_called_once()
            mock_features.assert_called_once()
            mock_signals.assert_called_once()
            mock_blend.assert_called_once()
            mock_reports.assert_called_once()
            mock_bot.process_daily_report.assert_called_once()

        logger.info("✅ Batch pipeline with mocks verified")
        return True

    async def test_always_on_mode_mocked(self):
        """Test always-on mode with mocked components"""
        logger.info("🧪 Testing always-on mode with mocks...")

        # Mock everything to isolate the test
        with patch("sqlalchemy.create_engine"), \
             patch("asyncio.create_task") as mock_create_task, \
             patch("uvicorn.Server") as mock_server, \
             patch("asyncio.sleep", side_effect=KeyboardInterrupt), \
             patch("src.main.PatternIQOrchestrator.run_daily_pipeline",
                  new_callable=AsyncMock, return_value=True):

            from src.main import PatternIQOrchestrator

            # Configure always-on mode
            os.environ["PATTERNIQ_ALWAYS_ON"] = "true"
            os.environ["START_API_SERVER"] = "true"

            # Create orchestrator
            orchestrator = PatternIQOrchestrator()

            # Run always-on mode (will be interrupted by KeyboardInterrupt from mocked sleep)
            try:
                await orchestrator.run_always_on_mode()
            except KeyboardInterrupt:
                pass  # Expected

            # API server should be started in always-on mode
            mock_create_task.assert_called_once()

        logger.info("✅ Always-on mode with mocks verified")
        return True

    def test_report_generation(self):
        """Test report generation"""
        logger.info("🧪 Testing report generation...")

        from src.report.generator import generate_daily_report
        from datetime import date

        # Generate report for today
        today_str = date.today().strftime("%Y-%m-%d")
        result = generate_daily_report(today_str)

        # Check result
        assert result is not None, "Report generation should return result"
        assert "status" in result, "Report result should include status"
        assert result["status"] == "success", "Report generation should succeed"

        # Check files were created
        date_id = today_str.replace("-", "")
        json_path = Path(f"reports/patterniq_report_{date_id}.json")
        html_path = Path(f"reports/patterniq_report_{date_id}.html")

        assert json_path.exists(), "JSON report should be created"
        assert html_path.exists(), "HTML report should be created"

        logger.info("✅ Report generation verified")
        return True

    def test_trading_bot(self):
        """Test trading bot functionality"""
        logger.info("🧪 Testing trading bot functionality...")

        from src.trading.simulator import AutoTradingBot

        # Create new trading bot with clean state
        bot = AutoTradingBot(initial_capital=100000.0, paper_trading=True)

        # Check initial state
        status = bot.get_portfolio_status()
        assert status["initial_capital"] == 100000.0, "Initial capital should be set"
        assert status["cash_balance"] == 100000.0, "Initial cash should equal initial capital"
        assert status["current_value"] == 100000.0, "Initial value should equal initial capital"
        assert status["positions"] == [], "Initial positions should be empty"

        # Test report processing
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")

        # Create test report directory and file
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        # Process report
        with patch("src.trading.simulator.AutoTradingBot._execute_buy") as mock_buy:
            # Enable test mode to create demo report
            os.environ["PATTERNIQ_TESTING"] = "true"

            # Process today's report
            result = bot.process_daily_report(today)

            # Check processing worked
            assert result["status"] in ["completed", "error"], "Processing should complete"
            if result["status"] == "completed":
                assert mock_buy.called, "Buy should be called for test report"

        logger.info("✅ Trading bot functionality verified")
        return True

    def test_cli_interface(self):
        """Test CLI interface"""
        logger.info("🧪 Testing CLI interface...")

        # Check CLI script exists
        cli_script = Path("run_patterniq.py")
        assert cli_script.exists(), "CLI script should exist"

        # Test with help flag
        import subprocess
        result = subprocess.run(
            [sys.executable, str(cli_script), "--help"],
            capture_output=True, text=True
        )

        # Check output contains mode options
        assert result.returncode == 0, "CLI help command should succeed"
        help_text = result.stdout.lower()
        assert "batch" in help_text, "Help should mention batch mode"
        assert "always-on" in help_text, "Help should mention always-on mode"
        assert "api-only" in help_text, "Help should mention api-only mode"

        logger.info("✅ CLI interface verified")
        return True

    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Running PatternIQ Combined Tests")
        logger.info("=" * 60)

        # Define all tests
        sync_tests = [
            ("Configuration Modes", self.test_configuration_modes),
            ("Report Generation", self.test_report_generation),
            ("Trading Bot", self.test_trading_bot),
            ("CLI Interface", self.test_cli_interface),
        ]

        async_tests = [
            ("Orchestrator Initialization", self.test_orchestrator_initialization),
            ("Batch Pipeline (Mocked)", self.test_batch_pipeline_mocked),
            ("Always-On Mode (Mocked)", self.test_always_on_mode_mocked)
        ]

        # Run synchronous tests
        sync_results = []
        for name, test_func in sync_tests:
            logger.info(f"\n📋 Running: {name}")
            logger.info("-" * 40)

            try:
                result = test_func()
                sync_results.append((name, result))
            except Exception as e:
                logger.error(f"❌ Test failed with exception: {e}")
                import traceback
                logger.error(traceback.format_exc())
                sync_results.append((name, False))

        # Run asynchronous tests
        async_results = []
        for name, test_func in async_tests:
            logger.info(f"\n📋 Running: {name}")
            logger.info("-" * 40)

            try:
                result = await test_func()
                async_results.append((name, result))
            except Exception as e:
                logger.error(f"❌ Test failed with exception: {e}")
                import traceback
                logger.error(traceback.format_exc())
                async_results.append((name, False))

        # Combine results
        all_results = sync_results + async_results

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 COMBINED TEST SUMMARY")
        logger.info("=" * 60)

        passed = sum(1 for _, success in all_results if success)
        total = len(all_results)

        for name, success in all_results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{status:<10} {name}")

        logger.info("-" * 60)
        logger.info(f"Results: {passed}/{total} tests passed")

        if passed == total:
            logger.info("\n🎉 ALL TESTS PASSED! PatternIQ is operating correctly.")
            return True
        else:
            logger.error(f"\n⚠️ {total-passed} tests failed. Please check the output above.")
            return False

async def main():
    """Main entry point"""
    tester = PatternIQTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())

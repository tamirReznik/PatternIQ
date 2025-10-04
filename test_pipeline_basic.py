#!/usr/bin/env python3
# test_pipeline_basic.py - Basic test for PatternIQ pipeline functionality

import os
import sys
import asyncio
import logging
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PipelineTest")

# Make sure we can import from src
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Enable test mode
os.environ["PATTERNIQ_TESTING"] = "true"

class PipelineTest:
    """Basic tests for PatternIQ pipeline functionality"""

    def __init__(self):
        """Initialize test environment"""
        # Ensure directories exist
        Path("reports").mkdir(exist_ok=True)
        Path("trading_data").mkdir(exist_ok=True)

    async def test_orchestrator_initialization(self):
        """Test that the orchestrator initializes correctly"""
        logger.info("🧪 Testing orchestrator initialization...")

        from src.main import PatternIQOrchestrator
        orchestrator = PatternIQOrchestrator()

        # Verify initialization
        assert orchestrator is not None, "Orchestrator should initialize"
        assert orchestrator.trading_bot is None, "Trading bot should start as None"
        assert orchestrator.api_server is None, "API server should start as None"

        logger.info("✅ Orchestrator initialization verified")
        return True

    async def test_batch_mode_execution(self):
        """Test batch mode execution flow"""
        logger.info("🧪 Testing batch mode execution...")

        from src.main import PatternIQOrchestrator

        # Configure batch mode
        os.environ["PATTERNIQ_ALWAYS_ON"] = "false"
        os.environ["START_API_SERVER"] = "false"
        os.environ["GENERATE_REPORTS"] = "false"
        os.environ["SEND_TELEGRAM_ALERTS"] = "false"

        # Mock all dependencies to isolate test
        with patch('src.data.demo_full_pipeline.demo_full_data_ingestion') as mock_data, \
             patch('src.features.momentum.demo_momentum_features') as mock_features, \
             patch('src.signals.rules.demo_signal_generation') as mock_signals, \
             patch('src.signals.blend.blend_signals_ic_weighted') as mock_blend, \
             patch('src.report.generator.generate_daily_report') as mock_reports, \
             patch('sys.exit') as mock_exit:

            # Create test bot
            mock_bot = MagicMock()
            mock_bot.process_daily_report.return_value = {"status": "completed", "trades_executed": 2}
            mock_bot.get_portfolio_status.return_value = {
                "initial_capital": 100000.0,
                "current_value": 102500.0,
                "total_return": "2.50%"
            }

            # Create orchestrator and inject mocked bot
            orchestrator = PatternIQOrchestrator()
            orchestrator.trading_bot = mock_bot

            # Run batch mode
            await orchestrator.run_batch_mode()

            # Verify all steps were called
            mock_data.assert_called_once()
            mock_features.assert_called_once()
            mock_signals.assert_called_once()
            mock_blend.assert_called_once()
            mock_reports.assert_not_called()  # Reports disabled
            mock_bot.process_daily_report.assert_called_once()
            mock_exit.assert_called_once()  # Should exit in batch mode

        logger.info("✅ Batch mode execution verified")
        return True

    async def test_pipeline_error_handling(self):
        """Test pipeline error handling"""
        logger.info("🧪 Testing pipeline error handling...")

        from src.main import PatternIQOrchestrator

        # Mock data pipeline to fail
        with patch('src.data.demo_full_pipeline.demo_full_data_ingestion',
                 side_effect=Exception("Test failure")):

            orchestrator = PatternIQOrchestrator()
            result = await orchestrator.run_daily_pipeline()

            # Should return False on failure
            assert result == False, "Pipeline should return False on failure"

        logger.info("✅ Pipeline error handling verified")
        return True

    async def test_api_start_in_always_on_mode(self):
        """Test API server starts in always-on mode"""
        logger.info("🧪 Testing API server in always-on mode...")

        from src.main import PatternIQOrchestrator

        # Configure always-on mode
        os.environ["PATTERNIQ_ALWAYS_ON"] = "true"
        os.environ["START_API_SERVER"] = "true"

        # Mock API server start to avoid actually starting server
        mock_server = AsyncMock()

        with patch('src.main.uvicorn.Server', return_value=mock_server), \
             patch('src.main.uvicorn.Config'), \
             patch('asyncio.create_task') as mock_create_task, \
             patch('asyncio.sleep', side_effect=KeyboardInterrupt):

            # Mock daily pipeline
            orchestrator = PatternIQOrchestrator()
            orchestrator.run_daily_pipeline = AsyncMock(return_value=True)

            try:
                await orchestrator.run_always_on_mode()
            except KeyboardInterrupt:
                pass  # Expected for test

            # Verify API server was started and pipeline ran
            mock_create_task.assert_called_once()
            orchestrator.run_daily_pipeline.assert_called_once()

        logger.info("✅ API server in always-on mode verified")
        return True

    async def test_report_generation(self):
        """Test report generation"""
        logger.info("🧪 Testing report generation...")

        from src.report.generator import generate_daily_report
        from datetime import date

        # Generate a test report
        result = generate_daily_report(date.today().strftime("%Y-%m-%d"))

        # Verify report was generated
        assert result is not None, "Report generation should return a result"
        assert "status" in result, "Report result should include status"
        assert result["status"] == "success", "Report status should be success"

        # Check if files were generated
        reports_dir = Path("reports")
        today_str = date.today().strftime("%Y%m%d")
        json_report = reports_dir / f"patterniq_report_{today_str}.json"
        html_report = reports_dir / f"patterniq_report_{today_str}.html"

        assert json_report.exists(), "JSON report should be generated"
        assert html_report.exists(), "HTML report should be generated"

        logger.info("✅ Report generation verified")
        return True

    async def test_trading_bot(self):
        """Test trading bot functionality"""
        logger.info("🧪 Testing trading bot...")

        from src.trading.simulator import AutoTradingBot

        # Create trading bot
        bot = AutoTradingBot(initial_capital=100000.0, paper_trading=True)

        # Get initial portfolio status
        status = bot.get_portfolio_status()

        # Verify basic portfolio data
        assert status["initial_capital"] == 100000.0, "Initial capital should match"
        assert status["cash_balance"] == 100000.0, "Initial cash should match"
        assert status["paper_trading"] == True, "Paper trading mode should be set"

        logger.info("✅ Trading bot verified")
        return True

    async def run_all_tests(self):
        """Run all tests"""
        logger.info("\n🚀 Running PatternIQ Pipeline Basic Tests")
        logger.info("=" * 60)

        tests = [
            ("Orchestrator Initialization", self.test_orchestrator_initialization),
            ("Batch Mode Execution", self.test_batch_mode_execution),
            ("Pipeline Error Handling", self.test_pipeline_error_handling),
            ("API Server in Always-On Mode", self.test_api_start_in_always_on_mode),
            ("Report Generation", self.test_report_generation),
            ("Trading Bot Functionality", self.test_trading_bot)
        ]

        results = []
        for name, test_func in tests:
            logger.info(f"\n📋 Running: {name}")
            logger.info("-" * 40)

            try:
                success = await test_func()
                results.append((name, success))
            except Exception as e:
                logger.error(f"❌ Test failed with exception: {e}")
                results.append((name, False))

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{status:<10} {name}")

        logger.info("-" * 60)
        logger.info(f"Results: {passed}/{total} tests passed")

        if passed == total:
            logger.info("🎉 All pipeline tests passed! PatternIQ pipeline is working correctly.")
            return True
        else:
            logger.error(f"⚠️ {total-passed} tests failed. Please check the output above.")
            return False

async def main():
    tester = PipelineTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())

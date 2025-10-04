#!/usr/bin/env python3
# test_pipeline_modes.py - Test pipeline execution in different modes

import os
import sys
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import PatternIQOrchestrator
from src.common.config import load_config

class TestPipelineExecution:
    """Test actual pipeline execution in different modes"""

    def setUp(self):
        """Setup test environment"""
        self.test_reports_dir = Path("test_reports")
        self.test_reports_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Cleanup test environment"""
        if self.test_reports_dir.exists():
            for file in self.test_reports_dir.glob("*"):
                file.unlink()
            self.test_reports_dir.rmdir()

    async def test_batch_mode_pipeline(self):
        """Test complete batch mode pipeline execution"""
        print("🧪 Testing batch mode pipeline execution...")

        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'START_API_SERVER': 'false',
            'GENERATE_REPORTS': 'true',
            'SEND_TELEGRAM_ALERTS': 'false',
            'PAPER_TRADING': 'true'
        }):
            orchestrator = PatternIQOrchestrator()

            # Mock all external dependencies
            with patch('src.data.demo_full_pipeline.main') as mock_data, \
                 patch('src.features.momentum.main') as mock_features, \
                 patch('src.signals.rules.main') as mock_signals, \
                 patch('src.signals.blend.main') as mock_blend, \
                 patch('src.report.generator.main') as mock_reports:

                # Mock trading bot
                mock_trading_bot = MagicMock()
                mock_trading_bot.process_daily_report.return_value = {
                    'status': 'completed',
                    'trades_executed': 5,
                    'portfolio_value': 105000.0
                }
                mock_trading_bot.get_portfolio_status.return_value = {
                    'initial_capital': 100000.0,
                    'current_value': 105000.0,
                    'total_return': '5.00%',
                    'cash_balance': 45000.0,
                    'positions_value': 60000.0,
                    'total_pnl': 5000.0
                }

                # Patch the trading bot creation
                with patch('src.trading.simulator.AutoTradingBot', return_value=mock_trading_bot):
                    # Run the pipeline
                    result = await orchestrator.run_daily_pipeline()

                    # Verify result
                    assert result == True, "Pipeline should return True on success"

                    # Verify all steps were called in order
                    mock_data.assert_called_once()
                    mock_features.assert_called_once()
                    mock_signals.assert_called_once()
                    mock_blend.assert_called_once()
                    mock_reports.assert_called_once()

                    # Verify trading bot was used
                    mock_trading_bot.process_daily_report.assert_called_once()
                    mock_trading_bot.get_portfolio_status.assert_called_once()

                    print("✅ Batch mode pipeline executed successfully")
                    return True

    async def test_batch_mode_with_error(self):
        """Test batch mode error handling"""
        print("🧪 Testing batch mode error handling...")

        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'GENERATE_REPORTS': 'false',
            'SEND_TELEGRAM_ALERTS': 'false'
        }):
            orchestrator = PatternIQOrchestrator()

            # Mock data pipeline to raise exception
            with patch('src.data.demo_full_pipeline.main', side_effect=Exception("Test pipeline error")):
                result = await orchestrator.run_daily_pipeline()

                # Should return False on error
                assert result == False, "Pipeline should return False on error"
                print("✅ Error handling works correctly")
                return True

    async def test_always_on_mode_setup(self):
        """Test always-on mode initial setup"""
        print("🧪 Testing always-on mode setup...")

        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'true',
            'START_API_SERVER': 'false',  # Skip API for test
            'GENERATE_REPORTS': 'false',
            'SEND_TELEGRAM_ALERTS': 'false'
        }):
            orchestrator = PatternIQOrchestrator()

            # Mock pipeline components
            with patch('src.data.demo_full_pipeline.main') as mock_data, \
                 patch('src.features.momentum.main') as mock_features, \
                 patch('src.signals.rules.main') as mock_signals, \
                 patch('src.signals.blend.main') as mock_blend, \
                 patch('asyncio.sleep') as mock_sleep:

                # Mock trading bot
                mock_trading_bot = MagicMock()
                mock_trading_bot.process_daily_report.return_value = {'status': 'completed'}
                mock_trading_bot.get_portfolio_status.return_value = {
                    'initial_capital': 100000.0,
                    'current_value': 102000.0,
                    'total_return': '2.00%'
                }

                with patch('src.trading.simulator.AutoTradingBot', return_value=mock_trading_bot):
                    # Mock sleep to exit after first iteration
                    mock_sleep.side_effect = KeyboardInterrupt("Test exit")

                    try:
                        await orchestrator.run_always_on_mode()
                    except KeyboardInterrupt:
                        pass  # Expected for test

                    # Verify initial pipeline ran
                    mock_data.assert_called_once()
                    mock_features.assert_called_once()
                    mock_signals.assert_called_once()
                    mock_blend.assert_called_once()

                    print("✅ Always-on mode setup works correctly")
                    return True

    async def test_trading_bot_integration(self):
        """Test trading bot integration"""
        print("🧪 Testing trading bot integration...")

        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'PAPER_TRADING': 'true',
            'INITIAL_CAPITAL': '50000.0',
            'MAX_POSITION_SIZE': '0.03'
        }):
            orchestrator = PatternIQOrchestrator()

            # Create a mock trading bot with realistic behavior
            mock_trading_bot = MagicMock()
            mock_trading_bot.process_daily_report.return_value = {
                'status': 'completed',
                'trades_executed': 3,
                'long_positions': 2,
                'short_positions': 1,
                'portfolio_value': 51500.0
            }
            mock_trading_bot.get_portfolio_status.return_value = {
                'initial_capital': 50000.0,
                'current_value': 51500.0,
                'total_return': '3.00%',
                'cash_balance': 35000.0,
                'positions_value': 16500.0,
                'total_pnl': 1500.0,
                'positions': [
                    {
                        'symbol': 'AAPL',
                        'shares': 50,
                        'entry_price': 150.0,
                        'current_price': 155.0,
                        'unrealized_pnl': 250.0
                    }
                ]
            }

            with patch('src.trading.simulator.AutoTradingBot', return_value=mock_trading_bot):
                # Test trading integration
                await orchestrator.run_trading()

                # Verify trading bot was called
                mock_trading_bot.process_daily_report.assert_called_once()
                mock_trading_bot.get_portfolio_status.assert_called_once()

                print("✅ Trading bot integration works correctly")
                return True

    def test_configuration_modes(self):
        """Test different configuration modes"""
        print("🧪 Testing configuration modes...")

        # Test batch mode config
        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'START_API_SERVER': 'false',
            'GENERATE_REPORTS': 'true',
            'REPORT_FORMATS': 'json,html'
        }):
            config = load_config()
            assert config.always_on == False
            assert config.start_api_server == False
            assert config.generate_reports == True
            assert config.report_formats == ['json', 'html']

        # Test always-on mode config
        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'true',
            'START_API_SERVER': 'true',
            'API_HOST': '0.0.0.0',
            'API_PORT': '8000'
        }):
            config = load_config()
            assert config.always_on == True
            assert config.start_api_server == True
            assert config.api_host == '0.0.0.0'
            assert config.api_port == 8000

        # Test development mode config
        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'START_API_SERVER': 'true',
            'GENERATE_REPORTS': 'false',
            'SEND_TELEGRAM_ALERTS': 'false'
        }):
            config = load_config()
            assert config.always_on == False
            assert config.start_api_server == True
            assert config.generate_reports == False
            assert config.send_telegram_alerts == False

        print("✅ All configuration modes work correctly")
        return True

    async def test_telegram_integration(self):
        """Test Telegram integration"""
        print("🧪 Testing Telegram integration...")

        with patch.dict(os.environ, {
            'SEND_TELEGRAM_ALERTS': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token_123',
            'TELEGRAM_CHAT_IDS': '123456789'
        }):
            orchestrator = PatternIQOrchestrator()

            # Mock Telegram bot
            mock_telegram_bot = MagicMock()
            mock_telegram_bot.send_daily_report = AsyncMock(return_value=True)

            # Create a fake report file
            test_report = Path("reports/test_report.json")
            test_report.parent.mkdir(exist_ok=True)
            test_report.write_text(json.dumps({
                "date": "2025-01-01",
                "summary": "Test report",
                "recommendations": []
            }))

            try:
                with patch('src.telegram.bot.PatternIQBot', return_value=mock_telegram_bot), \
                     patch('pathlib.Path.glob', return_value=[test_report]):

                    await orchestrator.send_telegram_alert()

                    # Verify Telegram bot was called
                    mock_telegram_bot.send_daily_report.assert_called_once_with(test_report)

                    print("✅ Telegram integration works correctly")
                    return True
            finally:
                if test_report.exists():
                    test_report.unlink()

    async def run_all_async_tests(self):
        """Run all async tests"""
        tests = [
            ("Batch Mode Pipeline", self.test_batch_mode_pipeline),
            ("Batch Mode Error Handling", self.test_batch_mode_with_error),
            ("Always-On Mode Setup", self.test_always_on_mode_setup),
            ("Trading Bot Integration", self.test_trading_bot_integration),
            ("Telegram Integration", self.test_telegram_integration)
        ]

        results = []
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            print("-" * 40)
            try:
                result = await test_func()
                results.append((test_name, result))
                if result:
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}")
                results.append((test_name, False))

        return results

    def run_all_tests(self):
        """Run all tests (sync and async)"""
        print("🚀 Starting PatternIQ Pipeline Mode Tests")
        print("=" * 60)

        self.setUp()

        try:
            # Run sync tests
            sync_results = [
                ("Configuration Modes", self.test_configuration_modes())
            ]

            # Run async tests
            async_results = asyncio.run(self.run_all_async_tests())

            # Combine results
            all_results = sync_results + async_results

            # Summary
            print("\n" + "=" * 60)
            print("📊 PIPELINE TEST SUMMARY")
            print("=" * 60)

            passed = sum(1 for _, result in all_results if result)
            total = len(all_results)

            for test_name, result in all_results:
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{status:<10} {test_name}")

            print("-" * 60)
            print(f"Results: {passed}/{total} tests passed")

            if passed == total:
                print("🎉 All pipeline tests passed!")
                return True
            else:
                print("⚠️  Some pipeline tests failed.")
                return False

        finally:
            self.tearDown()

def main():
    """Main entry point"""
    tester = TestPipelineExecution()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

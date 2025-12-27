#!/usr/bin/env python3
# test_operating_modes.py - Tests for different PatternIQ operating modes

import os
import sys
import asyncio
import tempfile
import subprocess
import time
import requests
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.common.config import PatternIQConfig, load_config
from src.main import PatternIQOrchestrator

class TestConfigurationSystem:
    """Test the configuration system and environment variable handling"""

    def test_default_config(self):
        """Test default configuration values"""
        config = PatternIQConfig()

        assert config.always_on == False
        assert config.api_host == "127.0.0.1"
        assert config.api_port == 8000
        assert config.paper_trading == True
        assert config.initial_capital == 100000.0
        assert config.generate_reports == True
        assert config.report_formats == ["json", "html"]

    def test_config_from_env(self):
        """Test configuration loading from environment variables"""
        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'true',
            'API_PORT': '9000',
            'PAPER_TRADING': 'false',
            'INITIAL_CAPITAL': '50000.0',
            'REPORT_FORMATS': 'json,html,pdf'
        }):
            config = load_config()

            assert config.always_on == True
            assert config.api_port == 9000
            assert config.paper_trading == False
            assert config.initial_capital == 50000.0
            assert config.report_formats == ['json', 'html', 'pdf']

    def test_boolean_parsing(self):
        """Test boolean environment variable parsing"""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('invalid', False)  # Should default to false
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'PATTERNIQ_ALWAYS_ON': env_value}):
                config = load_config()
                assert config.always_on == expected

class TestBatchMode:
    """Test batch mode operation (run once and exit)"""

    @pytest.mark.asyncio
    async def test_batch_mode_config(self):
        """Test batch mode configuration"""
        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'START_API_SERVER': 'false'
        }):
            orchestrator = PatternIQOrchestrator()
            config = orchestrator.config

            assert config.always_on == False
            assert config.start_api_server == False

    @pytest.mark.asyncio
    async def test_batch_mode_pipeline_execution(self):
        """Test that batch mode runs the pipeline"""
        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'START_API_SERVER': 'false',
            'GENERATE_REPORTS': 'false',  # Skip reports for faster testing
            'SEND_TELEGRAM_ALERTS': 'false'
        }):
            orchestrator = PatternIQOrchestrator()

            # Mock all pipeline steps
            with patch('src.data.demo_full_pipeline.main') as mock_data, \
                 patch('src.features.momentum.main') as mock_features, \
                 patch('src.signals.rules.main') as mock_signals, \
                 patch('src.signals.blend.main') as mock_blend, \
                 patch('src.report.generator.main') as mock_reports:

                # Mock trading bot
                mock_trading_bot = MagicMock()
                mock_trading_bot.process_daily_report.return_value = {'status': 'completed'}
                mock_trading_bot.get_portfolio_status.return_value = {
                    'initial_capital': 100000.0,
                    'current_value': 105000.0,
                    'total_return': '5.00%'
                }
                orchestrator.trading_bot = mock_trading_bot

                # Run pipeline
                result = await orchestrator.run_daily_pipeline()

                # Verify all steps were called
                assert result == True
                mock_data.assert_called_once()
                mock_features.assert_called_once()
                mock_signals.assert_called_once()
                mock_blend.assert_called_once()
                # Reports should be skipped due to config
                mock_reports.assert_not_called()

    def test_batch_mode_cli(self):
        """Test batch mode CLI command"""
        # Test that the CLI script can be called
        result = subprocess.run([
            sys.executable, 'run_patterniq.py', '--help'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)

        assert result.returncode == 0
        assert 'batch' in result.stdout
        assert 'always-on' in result.stdout
        assert 'api-only' in result.stdout

class TestAlwaysOnMode:
    """Test always-on mode operation (continuous)"""

    @pytest.mark.asyncio
    async def test_always_on_config(self):
        """Test always-on mode configuration"""
        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'true',
            'START_API_SERVER': 'true'
        }):
            orchestrator = PatternIQOrchestrator()
            config = orchestrator.config

            assert config.always_on == True
            assert config.start_api_server == True

    @pytest.mark.asyncio
    async def test_always_on_initial_pipeline(self):
        """Test that always-on mode runs initial pipeline"""
        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'true',
            'START_API_SERVER': 'false',  # Skip API for test
            'GENERATE_REPORTS': 'false',
            'SEND_TELEGRAM_ALERTS': 'false'
        }):
            orchestrator = PatternIQOrchestrator()

            # Mock pipeline steps
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
                    'current_value': 105000.0,
                    'total_return': '5.00%'
                }
                orchestrator.trading_bot = mock_trading_bot

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

class TestAPIMode:
    """Test API-only mode operation"""

    def test_api_server_starts(self):
        """Test that API server can start"""
        # Import here to avoid circular imports
        from src.api.server import app

        # Check that the FastAPI app is properly configured
        assert app is not None
        assert hasattr(app, 'routes')

        # Check that key routes exist
        route_paths = [route.path for route in app.routes]
        expected_routes = [
            '/',
            '/reports/latest',
            '/portfolio/status',
            '/signals/{date}'
        ]

        for expected_route in expected_routes:
            # Check if any route matches (allowing for path parameters)
            route_found = any(
                expected_route.replace('{date}', '') in path or
                path == expected_route
                for path in route_paths
            )
            assert route_found, f"Route {expected_route} not found in {route_paths}"

class TestEnvironmentConfiguration:
    """Test environment variable configuration"""

    def test_env_example_file_exists(self):
        """Test that .env.example file exists and has required settings"""
        env_example_path = Path(__file__).parent / ".env.example"
        assert env_example_path.exists(), ".env.example file not found"

        content = env_example_path.read_text()

        # Check for key configuration sections
        required_sections = [
            'BATCH MODE',
            'ALWAYS-ON MODE',
            'DEVELOPMENT MODE',
            'PRODUCTION MODE',
            'PATTERNIQ_ALWAYS_ON',
            'START_API_SERVER',
            'TELEGRAM_BOT_TOKEN'
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_environment_variable_parsing(self):
        """Test various environment variable formats"""
        test_configs = {
            # Boolean tests
            'PATTERNIQ_ALWAYS_ON': ['true', 'false', 'True', 'False'],
            'START_API_SERVER': ['true', 'false'],
            'PAPER_TRADING': ['true', 'false'],

            # Numeric tests
            'API_PORT': ['8000', '9000', '3000'],
            'INITIAL_CAPITAL': ['100000.0', '50000', '200000.5'],
            'MAX_POSITION_SIZE': ['0.05', '0.03', '0.10'],

            # String tests
            'API_HOST': ['127.0.0.1', '0.0.0.0', 'localhost'],
            'UNIVERSE': ['SP500', 'NASDAQ100'],
            'REPORT_FORMATS': ['json', 'json,html', 'json,html,pdf']
        }

        for env_var, test_values in test_configs.items():
            for test_value in test_values:
                with patch.dict(os.environ, {env_var: test_value}):
                    config = load_config()
                    # Just verify config loads without error
                    assert config is not None

class TestIntegrationScenarios:
    """Test real-world integration scenarios"""

    def test_cron_job_scenario(self):
        """Test typical cron job configuration"""
        cron_env = {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'START_API_SERVER': 'false',
            'GENERATE_REPORTS': 'true',
            'SEND_TELEGRAM_ALERTS': 'true',
            'PAPER_TRADING': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_IDS': '123456789'
        }

        with patch.dict(os.environ, cron_env):
            config = load_config()

            assert config.always_on == False
            assert config.start_api_server == False
            assert config.generate_reports == True
            assert config.send_telegram_alerts == True
            assert config.paper_trading == True
            assert config.telegram_bot_token == 'test_token'

    def test_production_server_scenario(self):
        """Test production server configuration"""
        prod_env = {
            'PATTERNIQ_ALWAYS_ON': 'true',
            'START_API_SERVER': 'true',
            'API_HOST': '0.0.0.0',
            'API_PORT': '8000',
            'GENERATE_REPORTS': 'true',
            'SEND_TELEGRAM_ALERTS': 'true',
            'PAPER_TRADING': 'true',  # Keep safe for testing
            'REPORT_FORMATS': 'json,html,pdf'
        }

        with patch.dict(os.environ, prod_env):
            config = load_config()

            assert config.always_on == True
            assert config.start_api_server == True
            assert config.api_host == '0.0.0.0'
            assert config.api_port == 8000
            assert config.generate_reports == True
            assert config.report_formats == ['json', 'html', 'pdf']

    def test_development_scenario(self):
        """Test development/testing configuration"""
        dev_env = {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'START_API_SERVER': 'true',
            'API_HOST': '127.0.0.1',
            'API_PORT': '8001',
            'GENERATE_REPORTS': 'false',
            'SEND_TELEGRAM_ALERTS': 'false',
            'PAPER_TRADING': 'true'
        }

        with patch.dict(os.environ, dev_env):
            config = load_config()

            assert config.always_on == False
            assert config.start_api_server == True
            assert config.api_host == '127.0.0.1'
            assert config.api_port == 8001
            assert config.generate_reports == False
            assert config.send_telegram_alerts == False

class TestErrorHandling:
    """Test error handling in different modes"""

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Test that pipeline errors are handled gracefully"""
        with patch.dict(os.environ, {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'GENERATE_REPORTS': 'false',
            'SEND_TELEGRAM_ALERTS': 'false'
        }):
            orchestrator = PatternIQOrchestrator()

            # Mock data pipeline to raise exception
            with patch('src.data.demo_full_pipeline.main', side_effect=Exception("Test error")):
                result = await orchestrator.run_daily_pipeline()

                # Should return False on error
                assert result == False

    def test_invalid_config_handling(self):
        """Test handling of invalid configuration values"""
        invalid_configs = [
            {'API_PORT': 'invalid_port'},
            {'INITIAL_CAPITAL': 'not_a_number'},
            {'MAX_POSITION_SIZE': 'invalid_float'}
        ]

        for invalid_config in invalid_configs:
            with patch.dict(os.environ, invalid_config):
                try:
                    config = load_config()
                    # Some configs might use defaults on invalid values
                    assert config is not None
                except (ValueError, TypeError):
                    # Some might raise exceptions, which is also acceptable
                    pass

def run_cli_tests():
    """Run CLI-specific tests that need subprocess"""
    print("🧪 Testing CLI interface...")

    # Test help command
    result = subprocess.run([
        sys.executable, 'run_patterniq.py', '--help'
    ], capture_output=True, text=True)

    assert result.returncode == 0
    assert 'PatternIQ' in result.stdout
    print("✅ CLI help command works")

    # Test invalid mode
    result = subprocess.run([
        sys.executable, 'run_patterniq.py', 'invalid_mode'
    ], capture_output=True, text=True)

    assert result.returncode != 0
    print("✅ CLI rejects invalid modes")

def run_all_tests():
    """Run all tests"""
    print("🚀 Starting PatternIQ Operating Mode Tests")
    print("=" * 50)

    # Run pytest tests
    pytest_args = [
        __file__,
        '-v',
        '--tb=short'
    ]

    exit_code = pytest.main(pytest_args)

    if exit_code == 0:
        print("\n🎉 All tests passed!")

        # Run CLI tests
        try:
            run_cli_tests()
            print("\n✅ All operating mode tests completed successfully!")
        except Exception as e:
            print(f"\n❌ CLI tests failed: {e}")
            return 1
    else:
        print("\n❌ Some tests failed!")
        return exit_code

    return 0

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

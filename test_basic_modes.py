#!/usr/bin/env python3
# test_basic_modes.py - Simple test for PatternIQ operating modes

import os
import sys
import subprocess
import tempfile
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ModeTest")

# Make sure we can import from src
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.common.config import load_config

class ModeTest:
    """Simple tests for PatternIQ operating modes"""

    def __init__(self):
        """Initialize test environment"""
        # Ensure directories exist
        Path("reports").mkdir(exist_ok=True)
        Path("trading_data").mkdir(exist_ok=True)

        # Enable test mode
        os.environ["PATTERNIQ_TESTING"] = "true"

    def test_batch_mode(self):
        """Test batch mode configuration"""
        logger.info("🧪 Testing BATCH mode configuration...")

        # Set environment to batch mode
        os.environ["PATTERNIQ_ALWAYS_ON"] = "false"
        os.environ["START_API_SERVER"] = "false"

        # Load and verify config
        config = load_config()

        assert config.always_on == False, "always_on should be False in batch mode"
        assert config.start_api_server == False, "start_api_server should be False in batch mode"

        logger.info("✅ Batch mode configuration verified")
        return True

    def test_always_on_mode(self):
        """Test always-on mode configuration"""
        logger.info("🧪 Testing ALWAYS-ON mode configuration...")

        # Set environment to always-on mode
        os.environ["PATTERNIQ_ALWAYS_ON"] = "true"
        os.environ["START_API_SERVER"] = "true"
        os.environ["API_PORT"] = "8123"  # Use non-standard port for testing

        # Load and verify config
        config = load_config()

        assert config.always_on == True, "always_on should be True in always-on mode"
        assert config.start_api_server == True, "start_api_server should be True in always-on mode"
        assert config.api_port == 8123, "API port should be set from environment"

        logger.info("✅ Always-on mode configuration verified")
        return True

    def test_api_only_mode(self):
        """Test API-only mode configuration"""
        logger.info("🧪 Testing API-ONLY mode configuration...")

        # Set environment to API-only mode
        os.environ["PATTERNIQ_ALWAYS_ON"] = "false"
        os.environ["START_API_SERVER"] = "true"
        os.environ["API_PORT"] = "8124"

        # Load and verify config
        config = load_config()

        assert config.always_on == False, "always_on should be False in API-only mode"
        assert config.start_api_server == True, "start_api_server should be True in API-only mode"
        assert config.api_port == 8124, "API port should be set correctly"

        logger.info("✅ API-only mode configuration verified")
        return True

    def test_boolean_parsing(self):
        """Test boolean environment variable parsing"""
        logger.info("🧪 Testing boolean environment parsing...")

        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('', False)  # Default to false
        ]

        for env_value, expected in test_cases:
            os.environ["PATTERNIQ_ALWAYS_ON"] = env_value
            config = load_config()
            assert config.always_on == expected, f"'{env_value}' should parse to {expected}"

        logger.info("✅ Boolean parsing verified")
        return True

    def test_numeric_parsing(self):
        """Test numeric environment variable parsing"""
        logger.info("🧪 Testing numeric environment parsing...")

        # Test integer parsing
        os.environ["API_PORT"] = "9000"
        config = load_config()
        assert config.api_port == 9000, "Integer parsing failed for API_PORT"

        # Test float parsing
        os.environ["INITIAL_CAPITAL"] = "50000.50"
        os.environ["MAX_POSITION_SIZE"] = "0.10"

        config = load_config()
        assert config.initial_capital == 50000.50, "Float parsing failed for INITIAL_CAPITAL"
        assert config.max_position_size == 0.10, "Float parsing failed for MAX_POSITION_SIZE"

        logger.info("✅ Numeric parsing verified")
        return True

    def test_string_list_parsing(self):
        """Test string list environment variable parsing"""
        logger.info("🧪 Testing string list environment parsing...")

        os.environ["REPORT_FORMATS"] = "json,html,pdf"

        config = load_config()
        expected = ["json", "html", "pdf"]
        assert config.report_formats == expected, f"String list parsing failed: got {config.report_formats}, expected {expected}"

        logger.info("✅ String list parsing verified")
        return True

    def test_cli_runner(self):
        """Test that CLI runner script exists and is executable"""
        logger.info("🧪 Testing CLI runner script...")

        runner = Path("run_patterniq.py")
        assert runner.exists(), "run_patterniq.py script not found"
        assert os.access(runner, os.X_OK), "run_patterniq.py script not executable"

        # Basic syntax check
        result = subprocess.run([sys.executable, str(runner), "--help"],
                              capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"CLI --help failed: {result.stderr}")
            return False

        # Check that the help output contains the mode options
        help_text = result.stdout.lower()
        assert "batch" in help_text, "batch mode not found in help text"
        assert "always-on" in help_text, "always-on mode not found in help text"

        logger.info("✅ CLI runner script verified")
        return True

    def run_all_tests(self):
        """Run all tests"""
        logger.info("\n🚀 Running PatternIQ Operating Mode Basic Tests")
        logger.info("=" * 60)

        tests = [
            ("Batch Mode Configuration", self.test_batch_mode),
            ("Always-On Mode Configuration", self.test_always_on_mode),
            ("API-Only Mode Configuration", self.test_api_only_mode),
            ("Boolean Environment Parsing", self.test_boolean_parsing),
            ("Numeric Environment Parsing", self.test_numeric_parsing),
            ("String List Environment Parsing", self.test_string_list_parsing),
            ("CLI Runner Script", self.test_cli_runner)
        ]

        results = []
        for name, test_func in tests:
            logger.info(f"\n📋 Running: {name}")
            logger.info("-" * 40)

            try:
                success = test_func()
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
            logger.info("🎉 All mode tests passed! PatternIQ operating modes are working correctly.")
            return True
        else:
            logger.error(f"⚠️ {total-passed} tests failed. Please check the output above.")
            return False

if __name__ == "__main__":
    tester = ModeTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

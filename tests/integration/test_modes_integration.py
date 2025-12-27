#!/usr/bin/env python3
# test_modes_integration.py - Integration tests for PatternIQ operating modes

import os
import sys
import subprocess
import tempfile
import time
import requests
import signal
from pathlib import Path
from contextlib import contextmanager

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

@contextmanager
def temporary_env(**kwargs):
    """Temporarily set environment variables"""
    old_environ = dict(os.environ)
    os.environ.update(kwargs)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)

class TestModeIntegration:
    """Integration tests for different operating modes"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.python_cmd = sys.executable

    def test_batch_mode_dry_run(self):
        """Test batch mode with dry run (no actual pipeline execution)"""
        print("🧪 Testing BATCH mode (dry run)...")

        # Create a simple test script that mimics batch mode behavior
        test_script = self.project_root / "test_batch_mode.py"
        test_script.write_text("""
import sys
import os
sys.path.insert(0, 'src')

from src.common.config import load_config

# Test batch mode configuration
with open('.env.test', 'w') as f:
    f.write('PATTERNIQ_ALWAYS_ON=false\\n')
    f.write('START_API_SERVER=false\\n')
    f.write('GENERATE_REPORTS=true\\n')

os.environ['PATTERNIQ_ALWAYS_ON'] = 'false'
os.environ['START_API_SERVER'] = 'false'

config = load_config()
print(f"Always on: {config.always_on}")
print(f"Start API: {config.start_api_server}")
print(f"Generate reports: {config.generate_reports}")

# Verify batch mode config
assert config.always_on == False
assert config.start_api_server == False
print("✅ Batch mode configuration verified")
""")

        try:
            result = subprocess.run([
                self.python_cmd, str(test_script)
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("✅ Batch mode configuration test passed")
                print(result.stdout)
            else:
                print("❌ Batch mode test failed:")
                print(result.stderr)
                return False
        except subprocess.TimeoutExpired:
            print("❌ Batch mode test timed out")
            return False
        finally:
            if test_script.exists():
                test_script.unlink()

        return True

    def test_always_on_mode_config(self):
        """Test always-on mode configuration"""
        print("🧪 Testing ALWAYS-ON mode configuration...")

        test_script = self.project_root / "test_always_on_config.py"
        test_script.write_text("""
import sys
import os
sys.path.insert(0, 'src')

from src.common.config import load_config

# Test always-on mode configuration
os.environ['PATTERNIQ_ALWAYS_ON'] = 'true'
os.environ['START_API_SERVER'] = 'true'
os.environ['API_HOST'] = '127.0.0.1'
os.environ['API_PORT'] = '8001'

config = load_config()
print(f"Always on: {config.always_on}")
print(f"Start API: {config.start_api_server}")
print(f"API host: {config.api_host}")
print(f"API port: {config.api_port}")

# Verify always-on mode config
assert config.always_on == True
assert config.start_api_server == True
assert config.api_host == '127.0.0.1'
assert config.api_port == 8001
print("✅ Always-on mode configuration verified")
""")

        try:
            result = subprocess.run([
                self.python_cmd, str(test_script)
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("✅ Always-on mode configuration test passed")
                print(result.stdout)
            else:
                print("❌ Always-on mode test failed:")
                print(result.stderr)
                return False
        except subprocess.TimeoutExpired:
            print("❌ Always-on mode test timed out")
            return False
        finally:
            if test_script.exists():
                test_script.unlink()

        return True

    def test_api_only_mode(self):
        """Test API-only mode by starting server briefly"""
        print("🧪 Testing API-ONLY mode...")

        # Test that we can start the API server
        try:
            # Start API server in background
            process = subprocess.Popen([
                self.python_cmd, 'run_patterniq.py', 'api-only', '--port', '8002'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Give server time to start
            time.sleep(3)

            # Test if server is responding
            try:
                response = requests.get('http://127.0.0.1:8002/', timeout=5)
                if response.status_code == 200:
                    print("✅ API server started successfully")
                    server_works = True
                else:
                    print(f"❌ API server returned status {response.status_code}")
                    server_works = False
            except requests.exceptions.RequestException as e:
                print(f"❌ Could not connect to API server: {e}")
                server_works = False

            # Stop the server
            process.terminate()
            process.wait(timeout=5)

            return server_works

        except Exception as e:
            print(f"❌ API-only mode test failed: {e}")
            return False

    def test_cli_help(self):
        """Test CLI help command"""
        print("🧪 Testing CLI help command...")

        try:
            result = subprocess.run([
                self.python_cmd, 'run_patterniq.py', '--help'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                print("✅ CLI help command works")
                # Check for key content
                if 'batch' in result.stdout and 'always-on' in result.stdout:
                    print("✅ CLI shows expected operating modes")
                    return True
                else:
                    print("❌ CLI help missing expected content")
                    return False
            else:
                print("❌ CLI help command failed")
                print(result.stderr)
                return False
        except subprocess.TimeoutExpired:
            print("❌ CLI help command timed out")
            return False

    def test_environment_file_parsing(self):
        """Test that .env.example has valid syntax"""
        print("🧪 Testing .env.example file...")

        env_file = self.project_root / ".env.example"
        if not env_file.exists():
            print("❌ .env.example file not found")
            return False

        try:
            content = env_file.read_text()

            # Check for required sections
            required_sections = [
                'BATCH MODE',
                'ALWAYS-ON MODE',
                'PATTERNIQ_ALWAYS_ON',
                'START_API_SERVER'
            ]

            missing_sections = []
            for section in required_sections:
                if section not in content:
                    missing_sections.append(section)

            if missing_sections:
                print(f"❌ Missing sections in .env.example: {missing_sections}")
                return False

            # Check for valid environment variable format
            lines = content.split('\n')
            env_lines = [line for line in lines if '=' in line and not line.strip().startswith('#')]

            for line in env_lines:
                if '=' not in line:
                    continue
                key, value = line.split('=', 1)
                if not key.strip():
                    print(f"❌ Invalid environment variable line: {line}")
                    return False

            print(f"✅ .env.example file valid ({len(env_lines)} environment variables)")
            return True

        except Exception as e:
            print(f"❌ Error parsing .env.example: {e}")
            return False

    def test_config_validation(self):
        """Test configuration validation with different values"""
        print("🧪 Testing configuration validation...")

        test_configs = [
            # Valid configs
            {'PATTERNIQ_ALWAYS_ON': 'true', 'expected_always_on': True},
            {'PATTERNIQ_ALWAYS_ON': 'false', 'expected_always_on': False},
            {'API_PORT': '8000', 'expected_port': 8000},
            {'API_PORT': '9000', 'expected_port': 9000},
            {'PAPER_TRADING': 'true', 'expected_paper': True},
            {'PAPER_TRADING': 'false', 'expected_paper': False}
        ]

        for i, test_config in enumerate(test_configs):
            expected_keys = [k for k in test_config.keys() if k.startswith('expected_')]
            env_vars = {k: v for k, v in test_config.items() if not k.startswith('expected_')}

            test_script = self.project_root / f"test_config_{i}.py"
            test_script.write_text(f"""
import sys
import os
sys.path.insert(0, 'src')

# Set environment variables
{chr(10).join([f"os.environ['{k}'] = '{v}'" for k, v in env_vars.items()])}

from src.common.config import load_config

config = load_config()

# Validate expected values
{chr(10).join([f"assert config.{k.replace('expected_', '')} == {test_config[k]}" for k in expected_keys])}

print("✅ Config test {i} passed")
""")

            try:
                result = subprocess.run([
                    self.python_cmd, str(test_script)
                ], capture_output=True, text=True, timeout=10)

                if result.returncode != 0:
                    print(f"❌ Config test {i} failed: {result.stderr}")
                    return False

            except subprocess.TimeoutExpired:
                print(f"❌ Config test {i} timed out")
                return False
            finally:
                if test_script.exists():
                    test_script.unlink()

        print("✅ All configuration validation tests passed")
        return True

    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting PatternIQ Operating Mode Integration Tests")
        print("=" * 60)

        tests = [
            ("CLI Help", self.test_cli_help),
            ("Environment File", self.test_environment_file_parsing),
            ("Configuration Validation", self.test_config_validation),
            ("Batch Mode Configuration", self.test_batch_mode_dry_run),
            ("Always-On Mode Configuration", self.test_always_on_mode_config),
            ("API-Only Mode", self.test_api_only_mode)
        ]

        results = []
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            print("-" * 40)
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}")
                results.append((test_name, False))

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status:<10} {test_name}")

        print("-" * 60)
        print(f"Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed! Operating modes are working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the output above.")
            return False

def main():
    """Main entry point"""
    tester = TestModeIntegration()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

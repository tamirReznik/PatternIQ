#!/usr/bin/env python3
# test_all_modes.py - Master test runner for all PatternIQ operating modes

import os
import sys
import subprocess
import time
from pathlib import Path

def run_test_suite(test_file, description):
    """Run a test suite and return results"""
    print(f"\n🚀 Running {description}")
    print("=" * 60)

    start_time = time.time()

    try:
        result = subprocess.run([
            sys.executable, str(test_file)
        ], capture_output=True, text=True, timeout=120)

        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ {description} PASSED ({duration:.1f}s)")
            if result.stdout:
                # Show only summary lines
                lines = result.stdout.split('\n')
                summary_lines = [line for line in lines if '✅' in line or '❌' in line or 'Results:' in line or 'passed!' in line]
                for line in summary_lines[-5:]:  # Show last 5 summary lines
                    print(f"   {line}")
            return True, duration
        else:
            print(f"❌ {description} FAILED ({duration:.1f}s)")
            if result.stderr:
                print("Error output:")
                print(result.stderr[:500])  # Show first 500 chars of error
            return False, duration

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} TIMED OUT (120s)")
        return False, 120.0
    except Exception as e:
        print(f"💥 {description} ERROR: {e}")
        return False, 0.0

def check_prerequisites():
    """Check that all required files exist"""
    print("🔍 Checking prerequisites...")

    required_files = [
        'src/main.py',
        'src/common/config.py',
        'run_patterniq.py',
        '.env.example',
        'test_operating_modes.py',
        'test_modes_integration.py',
        'test_pipeline_modes.py'
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False

    print("✅ All required files present")
    return True

def test_basic_imports():
    """Test that basic imports work"""
    print("🔍 Testing basic imports...")

    test_script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

try:
    from src.common.config import load_config, PatternIQConfig
    from src.main import PatternIQOrchestrator
    print("✅ Basic imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
"""

    try:
        result = subprocess.run([
            sys.executable, '-c', test_script
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ Basic imports work")
            return True
        else:
            print(f"❌ Import test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Import test error: {e}")
        return False

def main():
    """Main test runner"""
    print("🤖 PatternIQ Operating Modes - Complete Test Suite")
    print("=" * 70)
    print(f"📅 {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"📁 Working Directory: {Path.cwd()}")
    print("=" * 70)

    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites check failed. Please ensure all files are present.")
        return 1

    # Test basic imports
    if not test_basic_imports():
        print("\n❌ Basic imports failed. Please check your environment.")
        return 1

    # Define test suites
    test_suites = [
        ('test_modes_integration.py', 'Integration Tests'),
        ('test_pipeline_modes.py', 'Pipeline Mode Tests'),
        ('test_operating_modes.py', 'Operating Mode Unit Tests')
    ]

    # Run all test suites
    results = []
    total_duration = 0

    for test_file, description in test_suites:
        if Path(test_file).exists():
            passed, duration = run_test_suite(test_file, description)
            results.append((description, passed, duration))
            total_duration += duration
        else:
            print(f"⚠️  Skipping {description} - file not found: {test_file}")
            results.append((description, False, 0))

    # Final summary
    print("\n" + "=" * 70)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)

    for description, passed, duration in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:<10} {description:<30} ({duration:.1f}s)")

    print("-" * 70)
    print(f"📈 Results: {passed_count}/{total_count} test suites passed")
    print(f"⏱️  Total time: {total_duration:.1f} seconds")

    # Overall status
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("✅ PatternIQ operating modes are working correctly")
        print("✅ System is ready for deployment in any mode")
        print("\n📋 Quick Start Commands:")
        print("   Batch mode:     python run_patterniq.py batch")
        print("   Always-on:      python run_patterniq.py always-on")
        print("   API-only:       python run_patterniq.py api-only")
        return 0
    else:
        failed_count = total_count - passed_count
        print(f"\n⚠️  {failed_count} TEST SUITE(S) FAILED")
        print("❌ Please review the test output above")
        print("🔧 Fix any issues before deploying")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

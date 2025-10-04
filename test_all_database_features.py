#!/usr/bin/env python3
# test_all_database_features.py - Master test runner for all database functionality

import os
import sys
import subprocess
import asyncio
import time
from pathlib import Path

def run_test_suite(test_file, description):
    """Run a test suite and return results"""
    print(f"\n🚀 Running {description}")
    print("=" * 60)

    start_time = time.time()

    try:
        if test_file.endswith('_integration.py'):
            # Run async integration tests directly
            result = subprocess.run([
                sys.executable, str(test_file)
            ], capture_output=True, text=True, timeout=120)
        else:
            # Run pytest-based tests
            result = subprocess.run([
                sys.executable, str(test_file)
            ], capture_output=True, text=True, timeout=120)

        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ {description} PASSED ({duration:.1f}s)")
            # Show summary lines
            if result.stdout:
                lines = result.stdout.split('\n')
                summary_lines = [line for line in lines if ('✅' in line or '🎉' in line or 'passed' in line.lower()) and len(line.strip()) > 0]
                for line in summary_lines[-3:]:  # Show last 3 summary lines
                    print(f"   {line}")
            return True, duration
        else:
            print(f"❌ {description} FAILED ({duration:.1f}s)")
            if result.stderr:
                print("Error output:")
                print(result.stderr[:300])  # Show first 300 chars of error
            return False, duration

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} TIMED OUT (120s)")
        return False, 120.0
    except Exception as e:
        print(f"💥 {description} ERROR: {e}")
        return False, 0.0

def check_prerequisites():
    """Check that all required files exist"""
    print("🔍 Checking database test prerequisites...")

    required_files = [
        'src/common/config.py',
        'src/common/db_manager.py',
        'migrate_database.py',
        'run_patterniq.py',
        'test_database_modes.py',
        'test_cli_database.py',
        'test_database_integration.py'
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False

    print("✅ All required database test files present")
    return True

def test_basic_imports():
    """Test that basic database imports work"""
    print("🔍 Testing database module imports...")

    test_script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

try:
    from src.common.config import load_config, PatternIQConfig
    from src.common.db_manager import DatabaseManager
    
    # Test basic functionality
    config = PatternIQConfig(db_mode="sqlite", sqlite_path="test.db")
    assert config.get_effective_db_url().startswith("sqlite:///")
    
    # Test manager initialization
    db_manager = DatabaseManager()
    assert db_manager is not None
    
    print("✅ Database module imports successful")
except Exception as e:
    print(f"❌ Database import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

    try:
        result = subprocess.run([
            sys.executable, '-c', test_script
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ Database module imports work")
            return True
        else:
            print(f"❌ Database import test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Database import test error: {e}")
        return False

def main():
    """Main test runner"""
    print("🗄️ PatternIQ Database Features - Complete Test Suite")
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

    # Define test suites in order of complexity
    test_suites = [
        ('test_database_modes.py', 'Database Configuration & Migration Tests'),
        ('test_cli_database.py', 'CLI Database Options Tests'),
        ('test_database_integration.py', 'Database Integration Tests')
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
            print(f"⚠️ Skipping {description} - file not found: {test_file}")
            results.append((description, False, 0))

    # Test migration utility
    print(f"\n🚀 Testing Migration Utility")
    print("=" * 60)
    try:
        # Test migration utility help
        result = subprocess.run([
            sys.executable, 'migrate_database.py', '--help'
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and 'info' in result.stdout:
            print("✅ Migration Utility CLI PASSED")
            results.append(("Migration Utility CLI", True, 1.0))
        else:
            print("❌ Migration Utility CLI FAILED")
            results.append(("Migration Utility CLI", False, 1.0))
    except Exception as e:
        print(f"❌ Migration Utility test error: {e}")
        results.append(("Migration Utility CLI", False, 1.0))

    # Final summary
    print("\n" + "=" * 70)
    print("📊 DATABASE FEATURES TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)

    for description, passed, duration in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:<10} {description:<40} ({duration:.1f}s)")

    print("-" * 70)
    print(f"📈 Results: {passed_count}/{total_count} test suites passed")
    print(f"⏱️ Total time: {total_duration:.1f} seconds")

    # Overall status
    if passed_count == total_count:
        print("\n🎉 ALL DATABASE TESTS PASSED! 🎉")
        print("✅ Database configuration system is working correctly")
        print("✅ Database migration system is working correctly")
        print("✅ CLI database options are working correctly")
        print("✅ Database mode switching is working correctly")
        print("✅ Migration utility is working correctly")
        print("\n📋 Database Features Ready:")
        print("   • Auto mode: SQLite for batch, PostgreSQL for always-on")
        print("   • Force modes: --db-mode sqlite|postgres")
        print("   • Auto-migration: Seamless data transfer between databases")
        print("   • Manual migration: migrate_database.py utility")
        print("   • Backup creation: Automatic before migrations")
        print("   • Error handling: Graceful failure recovery")
        return 0
    else:
        failed_count = total_count - passed_count
        print(f"\n⚠️ {failed_count} TEST SUITE(S) FAILED")
        print("❌ Please review the test output above")
        print("🔧 Fix any issues before using database features")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

#!/usr/bin/env python3
"""
Simple batch runner for PatternIQ with explicit output
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Setup logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    print("🚀 PatternIQ Batch Mode - Direct Execution")
    print("=" * 60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    print(f"📁 Working directory: {os.getcwd()}")

    # Add src to Python path
    sys.path.insert(0, str(project_dir / "src"))
    print(f"🔧 Added to Python path: {project_dir / 'src'}")

    # Set environment for batch mode
    env_vars = {
        'PATTERNIQ_ALWAYS_ON': 'false',
        'DB_MODE': 'auto',
        'GENERATE_REPORTS': 'true',
        'SEND_TELEGRAM_ALERTS': 'false',
        'START_API_SERVER': 'false'
    }

    print("\n🔧 Setting environment variables:")
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"   {key} = {value}")

    print("\n📦 Testing imports...")
    try:
        from src.common.config import config
        print("   ✅ Config imported successfully")
        print(f"   - Always on: {config.always_on}")
        print(f"   - DB mode: {config.db_mode}")
        print(f"   - Generate reports: {config.generate_reports}")

        from src.common.db_manager import db_manager
        print("   ✅ Database manager imported successfully")

        from src.main import PatternIQOrchestrator
        print("   ✅ Main orchestrator imported successfully")

    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n🏃 Starting PatternIQ batch execution...")
    try:
        orchestrator = PatternIQOrchestrator()

        # Run the daily pipeline
        success = asyncio.run(orchestrator.run_daily_pipeline())

        if success:
            print("\n✅ Batch execution completed successfully!")
        else:
            print("\n❌ Batch execution failed!")

        # Check for generated reports
        reports_dir = Path("reports")
        if reports_dir.exists():
            reports = list(reports_dir.glob("*.json"))
            print(f"\n📊 Found {len(reports)} report files:")
            for report in sorted(reports):
                stat = report.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                print(f"   - {report.name} (modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")

        return success

    except Exception as e:
        print(f"\n❌ Batch execution failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n🎯 Batch mode completed with status: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)

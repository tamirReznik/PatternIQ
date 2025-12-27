#!/usr/bin/env python3
# test_batch_run.py - Test batch mode execution with explicit output

import os
import sys
import asyncio
from pathlib import Path

print("🚀 Starting PatternIQ Batch Mode Test")
print("=" * 50)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set batch mode environment
os.environ['PATTERNIQ_ALWAYS_ON'] = 'false'
os.environ['DB_MODE'] = 'auto'
os.environ['GENERATE_REPORTS'] = 'true'
os.environ['SEND_TELEGRAM_ALERTS'] = 'false'
os.environ['SQLITE_PATH'] = 'data/patterniq_batch.db'

print("✅ Environment variables set for batch mode")
print(f"   - PATTERNIQ_ALWAYS_ON: {os.environ.get('PATTERNIQ_ALWAYS_ON')}")
print(f"   - DB_MODE: {os.environ.get('DB_MODE')}")
print(f"   - GENERATE_REPORTS: {os.environ.get('GENERATE_REPORTS')}")

try:
    print("\n📦 Importing main module...")
    from src.main import main
    print("✅ Import successful")

    print("\n🏃 Running PatternIQ batch mode...")
    asyncio.run(main())
    print("✅ Batch mode completed successfully!")

except Exception as e:
    print(f"\n❌ Error during batch mode execution: {e}")
    import traceback
    traceback.print_exc()

print("\n📊 Checking for new reports...")
reports_dir = Path("reports")
if reports_dir.exists():
    reports = list(reports_dir.glob("*.json"))
    print(f"Found {len(reports)} report files:")
    for report in sorted(reports):
        print(f"   - {report.name}")
else:
    print("Reports directory not found")

print("\n🎯 Batch mode test completed!")

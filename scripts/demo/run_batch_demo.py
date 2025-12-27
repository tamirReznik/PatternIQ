#!/usr/bin/env python3
# run_batch_demo.py - Run PatternIQ batch mode with visible output

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging to show output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    print("🚀 PatternIQ Batch Mode Execution")
    print("=" * 50)

    # Set environment for batch mode
    os.environ['PATTERNIQ_ALWAYS_ON'] = 'false'
    os.environ['DB_MODE'] = 'auto'
    os.environ['GENERATE_REPORTS'] = 'true'
    os.environ['SEND_TELEGRAM_ALERTS'] = 'false'
    os.environ['SQLITE_PATH'] = 'data/patterniq_batch.db'

    try:
        from src.main import main as run_main
        print("✅ Imported main successfully")

        print("\n📋 Starting PatternIQ batch execution...")
        asyncio.run(run_main())

    except SystemExit as e:
        if e.code == 0:
            print(f"\n✅ Batch mode completed successfully! (exit code: {e.code})")
        else:
            print(f"\n❌ Batch mode failed with exit code: {e.code}")
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

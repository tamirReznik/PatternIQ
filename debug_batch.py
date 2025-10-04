#!/usr/bin/env python3
# debug_batch.py - Debug why batch mode isn't working

import os
import sys
from pathlib import Path

def debug_batch_mode():
    print("🔍 Debugging PatternIQ Batch Mode Issues")
    print("=" * 50)

    # Add src to path
    sys.path.insert(0, str(Path.cwd() / "src"))

    # Test basic imports
    print("1. Testing imports...")
    try:
        from src.common.config import load_config
        print("   ✅ Config import OK")

        from src.common.db_manager import db_manager
        print("   ✅ DB manager import OK")

        from src.main import PatternIQOrchestrator
        print("   ✅ Main orchestrator import OK")

    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test configuration
    print("\n2. Testing configuration...")
    try:
        os.environ['PATTERNIQ_ALWAYS_ON'] = 'false'
        os.environ['DB_MODE'] = 'auto'
        os.environ['GENERATE_REPORTS'] = 'true'

        config = load_config()
        print(f"   - Always on: {config.always_on}")
        print(f"   - DB mode: {config.db_mode}")
        print(f"   - Using SQLite: {config.is_using_sqlite()}")
        print(f"   - DB URL: {config.get_effective_db_url()}")

    except Exception as e:
        print(f"   ❌ Config failed: {e}")
        return False

    # Test database setup
    print("\n3. Testing database setup...")
    try:
        success = db_manager.setup_database()
        print(f"   - Setup result: {success}")

        if success:
            db_info = db_manager.get_database_info()
            print(f"   - DB type: {db_info.get('database_type', 'Unknown')}")
            print(f"   - Records: {db_info.get('total_records', 'N/A')}")

    except Exception as e:
        print(f"   ❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test orchestrator creation
    print("\n4. Testing orchestrator...")
    try:
        orchestrator = PatternIQOrchestrator()
        print(f"   ✅ Orchestrator created")
        print(f"   - Config loaded: {orchestrator.config is not None}")

    except Exception as e:
        print(f"   ❌ Orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ All basic components working - investigating pipeline execution...")
    return True

if __name__ == "__main__":
    debug_batch_mode()

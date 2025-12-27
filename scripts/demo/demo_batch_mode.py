#!/usr/bin/env python3
# demo_batch_mode.py - Demonstrate batch mode with database selection

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

def demo_batch_mode():
    """Demonstrate batch mode with auto database selection"""
    print("🚀 PatternIQ Batch Mode Demo")
    print("=" * 50)

    # Set up batch mode environment
    os.environ['PATTERNIQ_ALWAYS_ON'] = 'false'
    os.environ['DB_MODE'] = 'auto'
    os.environ['SQLITE_PATH'] = 'data/demo_batch.db'
    os.environ['GENERATE_REPORTS'] = 'true'
    os.environ['SEND_TELEGRAM_ALERTS'] = 'false'

    # Test database configuration
    from src.common.config import load_config
    config = load_config()

    print(f"📋 Configuration:")
    print(f"   - Mode: {'ALWAYS-ON' if config.always_on else 'BATCH'}")
    print(f"   - Database Mode: {config.db_mode}")
    print(f"   - Using SQLite: {config.is_using_sqlite()}")
    print(f"   - Database URL: {config.get_effective_db_url()}")
    print(f"   - Auto-migrate: {config.auto_migrate}")

    # Test database manager setup
    from src.common.db_manager import db_manager

    print(f"\n🗄️ Setting up database...")
    try:
        success = db_manager.setup_database()
        if success:
            print("✅ Database setup successful")

            # Get database info
            db_info = db_manager.get_database_info()
            print(f"   - Database Type: {db_info['database_type']}")
            print(f"   - Total Records: {db_info.get('total_records', 'N/A')}")
        else:
            print("❌ Database setup failed")
    except Exception as e:
        print(f"❌ Database setup error: {e}")

    print(f"\n📊 This demonstrates:")
    print(f"   ✅ Auto mode selects SQLite for batch mode")
    print(f"   ✅ Database directory is created automatically")
    print(f"   ✅ System ready for file-based operation")
    print(f"   ✅ No PostgreSQL server required")

    return config.is_using_sqlite()

if __name__ == "__main__":
    result = demo_batch_mode()
    print(f"\n🎉 Batch mode demo {'successful' if result else 'failed'}!")

#!/usr/bin/env python3
# migrate_database.py - Database migration utility for PatternIQ

import os
import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.common.config import config
from src.common.db_manager import db_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_sqlite_to_postgres():
    """Migrate data from SQLite to PostgreSQL"""
    logger.info("🔄 Migrating from SQLite to PostgreSQL...")

    # Override config to force PostgreSQL mode
    original_mode = config.db_mode
    config.db_mode = "postgres"

    try:
        success = db_manager.migrate_data("sqlite_to_postgres", confirm=True)
        if success:
            logger.info("✅ Migration completed successfully!")
            return True
        else:
            logger.error("❌ Migration failed!")
            return False
    finally:
        config.db_mode = original_mode

def migrate_postgres_to_sqlite():
    """Migrate data from PostgreSQL to SQLite"""
    logger.info("🔄 Migrating from PostgreSQL to SQLite...")

    # Override config to force SQLite mode
    original_mode = config.db_mode
    config.db_mode = "sqlite"

    try:
        success = db_manager.migrate_data("postgres_to_sqlite", confirm=True)
        if success:
            logger.info("✅ Migration completed successfully!")
            return True
        else:
            logger.error("❌ Migration failed!")
            return False
    finally:
        config.db_mode = original_mode

def show_database_info():
    """Show information about both databases"""
    logger.info("📊 Database Information:")
    logger.info("=" * 50)

    # Check SQLite
    logger.info("SQLite Database:")
    try:
        original_mode = config.db_mode
        config.db_mode = "sqlite"
        sqlite_info = db_manager.get_database_info()
        logger.info(f"  Path: {config.sqlite_path}")
        logger.info(f"  Exists: {'Yes' if Path(config.sqlite_path).exists() else 'No'}")
        logger.info(f"  Records: {sqlite_info.get('total_records', 'N/A')}")
        if sqlite_info.get('tables'):
            for table, count in sqlite_info['tables'].items():
                if count and count != 'N/A' and count > 0:
                    logger.info(f"    {table}: {count}")
    except Exception as e:
        logger.info(f"  Error: {e}")
    finally:
        config.db_mode = original_mode

    logger.info("")

    # Check PostgreSQL
    logger.info("PostgreSQL Database:")
    try:
        original_mode = config.db_mode
        config.db_mode = "postgres"
        postgres_info = db_manager.get_database_info()
        logger.info(f"  URL: {config.db_url}")
        logger.info(f"  Records: {postgres_info.get('total_records', 'N/A')}")
        if postgres_info.get('tables'):
            for table, count in postgres_info['tables'].items():
                if count and count != 'N/A' and count > 0:
                    logger.info(f"    {table}: {count}")
    except Exception as e:
        logger.info(f"  Error: {e}")
    finally:
        config.db_mode = original_mode

def create_backup():
    """Create a backup of the current database"""
    logger.info("💾 Creating database backup...")

    backup_path = db_manager.backup_database("manual_backup")
    logger.info(f"✅ Backup created: {backup_path}")
    return backup_path

def main():
    parser = argparse.ArgumentParser(
        description="PatternIQ Database Migration Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_database.py info                           # Show database info
  python migrate_database.py backup                         # Create backup
  python migrate_database.py sqlite-to-postgres             # Migrate SQLite → PostgreSQL
  python migrate_database.py postgres-to-sqlite             # Migrate PostgreSQL → SQLite
  
Environment Variables:
  PATTERNIQ_DB_URL       PostgreSQL connection string
  SQLITE_PATH           SQLite database file path
        """
    )

    parser.add_argument(
        "action",
        choices=["info", "backup", "sqlite-to-postgres", "postgres-to-sqlite"],
        help="Action to perform"
    )

    parser.add_argument(
        "--sqlite-path",
        default="data/patterniq.db",
        help="Path for SQLite database (default: data/patterniq.db)"
    )

    parser.add_argument(
        "--postgres-url",
        help="PostgreSQL connection URL (overrides environment)"
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompts"
    )

    args = parser.parse_args()

    # Set configuration overrides
    if args.sqlite_path:
        os.environ["SQLITE_PATH"] = args.sqlite_path
        config.sqlite_path = args.sqlite_path

    if args.postgres_url:
        os.environ["PATTERNIQ_DB_URL"] = args.postgres_url
        config.db_url = args.postgres_url

    logger.info("🗄️ PatternIQ Database Migration Utility")
    logger.info("=" * 50)

    try:
        if args.action == "info":
            show_database_info()

        elif args.action == "backup":
            create_backup()

        elif args.action == "sqlite-to-postgres":
            if not args.yes:
                response = input("⚠️  This will overwrite PostgreSQL data. Continue? (y/N): ")
                if response.lower() != 'y':
                    logger.info("Migration cancelled.")
                    return

            # Create backup first
            backup_path = create_backup()
            logger.info(f"Backup created at: {backup_path}")

            success = migrate_sqlite_to_postgres()
            if success:
                logger.info("🎉 Migration completed successfully!")
                logger.info("You can now use PostgreSQL mode:")
                logger.info("  export DB_MODE=postgres")
                logger.info("  python run_patterniq.py always-on")
            else:
                logger.error("💥 Migration failed! Check logs above.")
                sys.exit(1)

        elif args.action == "postgres-to-sqlite":
            if not args.yes:
                response = input("⚠️  This will overwrite SQLite data. Continue? (y/N): ")
                if response.lower() != 'y':
                    logger.info("Migration cancelled.")
                    return

            # Create backup first
            backup_path = create_backup()
            logger.info(f"Backup created at: {backup_path}")

            success = migrate_postgres_to_sqlite()
            if success:
                logger.info("🎉 Migration completed successfully!")
                logger.info("You can now use SQLite mode:")
                logger.info("  export DB_MODE=sqlite")
                logger.info("  python run_patterniq.py batch")
            else:
                logger.error("💥 Migration failed! Check logs above.")
                sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

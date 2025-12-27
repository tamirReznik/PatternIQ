# src/common/db_manager.py

import os
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime

from src.common.config import config
from src.data.models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and migrations between SQLite and PostgreSQL"""

    def __init__(self):
        self.config = config
        self._sqlite_engine = None
        self._postgres_engine = None
        self._current_engine = None
        self._current_session = None

    def get_engine(self, force_postgres: bool = False, force_sqlite: bool = False):
        """Get the appropriate database engine based on configuration"""
        if force_postgres:
            return self._get_postgres_engine()
        elif force_sqlite:
            return self._get_sqlite_engine()
        else:
            # Use configuration to determine engine
            if self.config.is_using_sqlite():
                return self._get_sqlite_engine()
            else:
                return self._get_postgres_engine()

    def _get_sqlite_engine(self):
        """Get SQLite engine"""
        if self._sqlite_engine is None:
            sqlite_url = f"sqlite:///{self.config.sqlite_path}"
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config.sqlite_path), exist_ok=True)
            self._sqlite_engine = create_engine(sqlite_url)
            logger.info(f"Created SQLite engine: {sqlite_url}")
        return self._sqlite_engine

    def _get_postgres_engine(self):
        """Get PostgreSQL engine"""
        if self._postgres_engine is None:
            self._postgres_engine = create_engine(self.config.db_url)
            logger.info(f"Created PostgreSQL engine: {self.config.db_url}")
        return self._postgres_engine

    def get_session(self):
        """Get database session for current configuration"""
        engine = self.get_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()

    def initialize_database(self):
        """Initialize database schema for current configuration"""
        engine = self.get_engine()
        logger.info(f"Initializing database schema: {engine.url}")
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully")

    def check_migration_needed(self) -> Optional[str]:
        """Check if migration is needed and return the direction"""
        current_mode = "sqlite" if self.config.is_using_sqlite() else "postgres"

        # Check if there's data in the other database
        if current_mode == "sqlite":
            # Check if PostgreSQL has data
            try:
                postgres_engine = self._get_postgres_engine()
                with postgres_engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM instruments"))
                    postgres_count = result.fetchone()[0]
                    if postgres_count > 0:
                        return "postgres_to_sqlite"
            except Exception as e:
                logger.debug(f"PostgreSQL not accessible or empty: {e}")
        else:
            # Check if SQLite has data
            try:
                if os.path.exists(self.config.sqlite_path):
                    sqlite_engine = self._get_sqlite_engine()
                    with sqlite_engine.connect() as conn:
                        result = conn.execute(text("SELECT COUNT(*) FROM instruments"))
                        sqlite_count = result.fetchone()[0]
                        if sqlite_count > 0:
                            return "sqlite_to_postgres"
            except Exception as e:
                logger.debug(f"SQLite not accessible or empty: {e}")

        return None

    def migrate_data(self, direction: str, confirm: bool = False) -> bool:
        """Migrate data between databases"""
        if not confirm and not self.config.auto_migrate:
            logger.warning(f"Migration {direction} detected but auto_migrate is disabled")
            return False

        logger.info(f"Starting migration: {direction}")

        try:
            if direction == "sqlite_to_postgres":
                return self._migrate_sqlite_to_postgres()
            elif direction == "postgres_to_sqlite":
                return self._migrate_postgres_to_sqlite()
            else:
                logger.error(f"Unknown migration direction: {direction}")
                return False
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

    def _migrate_sqlite_to_postgres(self) -> bool:
        """Migrate data from SQLite to PostgreSQL"""
        logger.info("Migrating data from SQLite to PostgreSQL...")

        sqlite_engine = self._get_sqlite_engine()
        postgres_engine = self._get_postgres_engine()

        # Initialize PostgreSQL schema
        Base.metadata.create_all(bind=postgres_engine)

        # Get list of tables to migrate
        tables_to_migrate = [
            'instruments', 'bars_1d', 'universe_membership',
            'fundamentals_snapshot', 'features_daily', 'signals_daily',
            'backtests', 'backtest_positions', 'reports'
        ]

        migrated_count = 0

        for table_name in tables_to_migrate:
            try:
                # Read from SQLite
                df = pd.read_sql_table(table_name, sqlite_engine)
                if len(df) > 0:
                    # Write to PostgreSQL
                    df.to_sql(table_name, postgres_engine, if_exists='replace', index=False)
                    logger.info(f"Migrated {len(df)} records from {table_name}")
                    migrated_count += len(df)
                else:
                    logger.debug(f"Table {table_name} is empty, skipping")
            except Exception as e:
                logger.warning(f"Could not migrate table {table_name}: {e}")

        logger.info(f"SQLite to PostgreSQL migration completed. {migrated_count} records migrated.")
        return True

    def _migrate_postgres_to_sqlite(self) -> bool:
        """Migrate data from PostgreSQL to SQLite"""
        logger.info("Migrating data from PostgreSQL to SQLite...")

        sqlite_engine = self._get_sqlite_engine()
        postgres_engine = self._get_postgres_engine()

        # Initialize SQLite schema
        Base.metadata.create_all(bind=sqlite_engine)

        # Get list of tables to migrate
        tables_to_migrate = [
            'instruments', 'bars_1d', 'universe_membership',
            'fundamentals_snapshot', 'features_daily', 'signals_daily',
            'backtests', 'backtest_positions', 'reports'
        ]

        migrated_count = 0

        for table_name in tables_to_migrate:
            try:
                # Read from PostgreSQL
                df = pd.read_sql_table(table_name, postgres_engine)
                if len(df) > 0:
                    # Write to SQLite
                    df.to_sql(table_name, sqlite_engine, if_exists='replace', index=False)
                    logger.info(f"Migrated {len(df)} records from {table_name}")
                    migrated_count += len(df)
                else:
                    logger.debug(f"Table {table_name} is empty, skipping")
            except Exception as e:
                logger.warning(f"Could not migrate table {table_name}: {e}")

        logger.info(f"PostgreSQL to SQLite migration completed. {migrated_count} records migrated.")
        return True

    def backup_database(self, backup_name: Optional[str] = None) -> str:
        """Create a backup of the current database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.config.is_using_sqlite():
            # Backup SQLite file
            if backup_name:
                backup_path = f"backups/{backup_name}_{timestamp}.db"
            else:
                backup_path = f"backups/patterniq_backup_{timestamp}.db"

            os.makedirs("backups", exist_ok=True)

            # Check if SQLite file exists before trying to backup
            if os.path.exists(self.config.sqlite_path):
                shutil.copy2(self.config.sqlite_path, backup_path)
                logger.info(f"SQLite backup created: {backup_path}")
            else:
                logger.info(f"SQLite file {self.config.sqlite_path} doesn't exist yet - skipping backup")
                # Create an empty backup file to maintain consistency
                Path(backup_path).touch()

            return backup_path
        else:
            # Backup PostgreSQL using pg_dump (if available)
            if backup_name:
                backup_path = f"backups/{backup_name}_{timestamp}.sql"
            else:
                backup_path = f"backups/patterniq_backup_{timestamp}.sql"

            os.makedirs("backups", exist_ok=True)
            # Note: This requires pg_dump to be available
            logger.info(f"PostgreSQL backup would be created: {backup_path}")
            logger.warning("PostgreSQL backup requires pg_dump utility - implement as needed")
            return backup_path

    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the current database"""
        engine = self.get_engine()

        info = {
            "database_type": "SQLite" if self.config.is_using_sqlite() else "PostgreSQL",
            "database_url": str(engine.url),
            "tables": {},
            "total_records": 0
        }

        tables_to_check = [
            'instruments', 'bars_1d', 'universe_membership',
            'fundamentals_snapshot', 'features_daily', 'signals_daily',
            'backtests', 'backtest_positions', 'reports'
        ]

        try:
            with engine.connect() as conn:
                for table_name in tables_to_check:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        count = result.fetchone()[0]
                        info["tables"][table_name] = count
                        info["total_records"] += count
                    except Exception:
                        info["tables"][table_name] = "N/A"
        except Exception as e:
            logger.error(f"Could not get database info: {e}")
            info["error"] = str(e)

        return info
    
    def is_using_sqlite(self) -> bool:
        """Check if currently using SQLite"""
        return self.config.is_using_sqlite()
    
    def is_using_postgres(self) -> bool:
        """Check if currently using PostgreSQL"""
        return self.config.is_using_postgres()

    def setup_database(self) -> bool:
        """Setup database with migration handling"""
        logger.info("Setting up database...")

        # Check if migration is needed
        migration_direction = self.check_migration_needed()

        if migration_direction and self.config.auto_migrate:
            logger.info(f"Auto-migration enabled, performing: {migration_direction}")
            # Create backup before migration
            self.backup_database(f"pre_migration_{migration_direction}")

            # Perform migration
            if not self.migrate_data(migration_direction, confirm=True):
                logger.error("Migration failed!")
                return False
        elif migration_direction:
            logger.warning(f"Migration needed ({migration_direction}) but auto_migrate is disabled")
            logger.warning("Set AUTO_MIGRATE=true to enable automatic migration")

        # Initialize current database
        self.initialize_database()

        # Log database info
        db_info = self.get_database_info()
        logger.info(f"Database setup complete:")
        logger.info(f"  Type: {db_info['database_type']}")
        logger.info(f"  Total records: {db_info['total_records']}")

        return True

# Global database manager instance
db_manager = DatabaseManager()

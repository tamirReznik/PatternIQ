#!/usr/bin/env python3
# test_database_modes.py - Tests for database configuration and migration

import os
import sys
import tempfile
import shutil
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.common.config import PatternIQConfig, load_config
from src.common.db_manager import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DatabaseTest")

class TestDatabaseConfiguration:
    """Test database configuration system"""

    def test_auto_mode_batch(self):
        """Test auto mode selects SQLite for batch mode"""
        with patch.dict(os.environ, {
            'DB_MODE': 'auto',
            'PATTERNIQ_ALWAYS_ON': 'false',
            'SQLITE_PATH': 'test_data/test.db'
        }):
            config = load_config()

            assert config.db_mode == "auto"
            assert config.always_on == False

            # Should use SQLite for batch mode
            db_url = config.get_effective_db_url()
            assert db_url.startswith("sqlite:///")
            assert "test_data/test.db" in db_url
            assert config.is_using_sqlite() == True
            assert config.is_using_postgres() == False

    def test_auto_mode_always_on(self):
        """Test auto mode selects PostgreSQL for always-on mode"""
        with patch.dict(os.environ, {
            'DB_MODE': 'auto',
            'PATTERNIQ_ALWAYS_ON': 'true',
            'PATTERNIQ_DB_URL': 'postgresql://test:test@localhost:5432/test'
        }):
            config = load_config()

            assert config.db_mode == "auto"
            assert config.always_on == True

            # Should use PostgreSQL for always-on mode
            db_url = config.get_effective_db_url()
            assert db_url.startswith("postgresql://")
            assert config.is_using_sqlite() == False
            assert config.is_using_postgres() == True

    def test_force_sqlite_mode(self):
        """Test forcing SQLite mode regardless of always_on setting"""
        with patch.dict(os.environ, {
            'DB_MODE': 'sqlite',
            'PATTERNIQ_ALWAYS_ON': 'true',  # Even with always-on
            'SQLITE_PATH': 'forced_sqlite.db'
        }):
            config = load_config()

            assert config.db_mode == "sqlite"
            assert config.always_on == True

            # Should still use SQLite even in always-on mode
            db_url = config.get_effective_db_url()
            assert db_url.startswith("sqlite:///")
            assert "forced_sqlite.db" in db_url
            assert config.is_using_sqlite() == True

    def test_force_postgres_mode(self):
        """Test forcing PostgreSQL mode regardless of always_on setting"""
        with patch.dict(os.environ, {
            'DB_MODE': 'postgres',
            'PATTERNIQ_ALWAYS_ON': 'false',  # Even with batch mode
            'PATTERNIQ_DB_URL': 'postgresql://forced:test@localhost:5432/forced'
        }):
            config = load_config()

            assert config.db_mode == "postgres"
            assert config.always_on == False

            # Should use PostgreSQL even in batch mode
            db_url = config.get_effective_db_url()
            assert db_url.startswith("postgresql://")
            assert config.is_using_postgres() == True

    def test_file_mode_alias(self):
        """Test that 'file' mode is treated as 'sqlite'"""
        with patch.dict(os.environ, {
            'DB_MODE': 'file',
            'SQLITE_PATH': 'file_mode_test.db'
        }):
            config = load_config()

            assert config.db_mode == "file"

            db_url = config.get_effective_db_url()
            assert db_url.startswith("sqlite:///")
            assert config.is_using_sqlite() == True

    def test_invalid_db_mode(self):
        """Test that invalid db_mode raises error"""
        config = PatternIQConfig(db_mode="invalid_mode")

        with pytest.raises(ValueError, match="Invalid db_mode"):
            config.get_effective_db_url()

    def test_auto_migrate_configuration(self):
        """Test auto_migrate configuration"""
        # Test default (True)
        with patch.dict(os.environ, {}):
            config = load_config()
            assert config.auto_migrate == True

        # Test explicit True
        with patch.dict(os.environ, {'AUTO_MIGRATE': 'true'}):
            config = load_config()
            assert config.auto_migrate == True

        # Test False
        with patch.dict(os.environ, {'AUTO_MIGRATE': 'false'}):
            config = load_config()
            assert config.auto_migrate == False

class TestDatabaseManager:
    """Test database manager functionality"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary directory for test databases
        self.temp_dir = tempfile.mkdtemp()
        self.test_sqlite_path = os.path.join(self.temp_dir, "test.db")

        # Mock config with test paths
        self.mock_config = MagicMock()
        self.mock_config.sqlite_path = self.test_sqlite_path
        self.mock_config.db_url = "postgresql://test:test@localhost:5432/test"
        self.mock_config.auto_migrate = True

    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_database_manager_initialization(self):
        """Test database manager initialization"""
        with patch('src.common.db_manager.config', self.mock_config):
            db_manager = DatabaseManager()

            assert db_manager.config == self.mock_config
            assert db_manager._sqlite_engine is None
            assert db_manager._postgres_engine is None

    def test_get_sqlite_engine(self):
        """Test SQLite engine creation"""
        with patch('src.common.db_manager.config', self.mock_config):
            db_manager = DatabaseManager()

            # Mock SQLAlchemy create_engine
            with patch('src.common.db_manager.create_engine') as mock_create:
                mock_engine = MagicMock()
                mock_create.return_value = mock_engine

                engine = db_manager._get_sqlite_engine()

                assert engine == mock_engine
                mock_create.assert_called_once()
                call_args = mock_create.call_args[0][0]
                assert call_args.startswith("sqlite:///")
                assert self.test_sqlite_path in call_args

    def test_get_postgres_engine(self):
        """Test PostgreSQL engine creation"""
        with patch('src.common.db_manager.config', self.mock_config):
            db_manager = DatabaseManager()

            # Mock SQLAlchemy create_engine
            with patch('src.common.db_manager.create_engine') as mock_create:
                mock_engine = MagicMock()
                mock_create.return_value = mock_engine

                engine = db_manager._get_postgres_engine()

                assert engine == mock_engine
                mock_create.assert_called_once_with(self.mock_config.db_url)

    def test_get_engine_force_options(self):
        """Test forcing specific engine types"""
        with patch('src.common.db_manager.config', self.mock_config):
            db_manager = DatabaseManager()

            with patch.object(db_manager, '_get_sqlite_engine') as mock_sqlite, \
                 patch.object(db_manager, '_get_postgres_engine') as mock_postgres:

                # Test force SQLite
                db_manager.get_engine(force_sqlite=True)
                mock_sqlite.assert_called_once()
                mock_postgres.assert_not_called()

                mock_sqlite.reset_mock()
                mock_postgres.reset_mock()

                # Test force PostgreSQL
                db_manager.get_engine(force_postgres=True)
                mock_postgres.assert_called_once()
                mock_sqlite.assert_not_called()

    def test_check_migration_needed(self):
        """Test migration detection logic"""
        with patch('src.common.db_manager.config', self.mock_config):
            db_manager = DatabaseManager()

            # Mock config to use SQLite
            self.mock_config.is_using_sqlite.return_value = True
            self.mock_config.is_using_postgres.return_value = False

            # Mock PostgreSQL having data
            with patch.object(db_manager, '_get_postgres_engine') as mock_pg_engine:
                mock_connection = MagicMock()
                mock_result = MagicMock()
                mock_result.fetchone.return_value = [10]  # 10 records
                mock_connection.execute.return_value = mock_result
                mock_pg_engine.return_value.connect.return_value.__enter__.return_value = mock_connection

                direction = db_manager.check_migration_needed()
                assert direction == "postgres_to_sqlite"

    def test_backup_database_sqlite(self):
        """Test SQLite database backup"""
        # Create a test SQLite file
        os.makedirs(os.path.dirname(self.test_sqlite_path), exist_ok=True)
        Path(self.test_sqlite_path).touch()

        with patch('src.common.db_manager.config', self.mock_config):
            self.mock_config.is_using_sqlite.return_value = True

            db_manager = DatabaseManager()

            # Mock the backup directory creation
            with patch('os.makedirs'), \
                 patch('shutil.copy2') as mock_copy:

                backup_path = db_manager.backup_database("test_backup")

                # Should call copy2 to create backup
                mock_copy.assert_called_once()
                assert "test_backup" in backup_path
                assert backup_path.endswith(".db")

    def test_database_info_collection(self):
        """Test database information collection"""
        with patch('src.common.db_manager.config', self.mock_config):
            self.mock_config.is_using_sqlite.return_value = True

            db_manager = DatabaseManager()

            # Mock engine and connection
            mock_engine = MagicMock()
            mock_connection = MagicMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = [42]  # 42 records
            mock_connection.execute.return_value = mock_result
            mock_engine.connect.return_value.__enter__.return_value = mock_connection
            mock_engine.url = "sqlite:///test.db"

            with patch.object(db_manager, 'get_engine', return_value=mock_engine):
                info = db_manager.get_database_info()

                assert info["database_type"] == "SQLite"
                assert "sqlite:///test.db" in str(info["database_url"])
                assert info["total_records"] > 0  # Should have accumulated some records

class TestDatabaseMigration:
    """Test database migration functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_sqlite_path = os.path.join(self.temp_dir, "test.db")

        # Mock config
        self.mock_config = MagicMock()
        self.mock_config.sqlite_path = self.test_sqlite_path
        self.mock_config.db_url = "postgresql://test:test@localhost:5432/test"
        self.mock_config.auto_migrate = True

    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_migrate_sqlite_to_postgres(self):
        """Test SQLite to PostgreSQL migration"""
        with patch('src.common.db_manager.config', self.mock_config):
            db_manager = DatabaseManager()

            # Mock pandas and SQLAlchemy components
            mock_sqlite_engine = MagicMock()
            mock_postgres_engine = MagicMock()

            with patch.object(db_manager, '_get_sqlite_engine', return_value=mock_sqlite_engine), \
                 patch.object(db_manager, '_get_postgres_engine', return_value=mock_postgres_engine), \
                 patch('src.common.db_manager.pd.read_sql_table') as mock_read, \
                 patch('src.common.db_manager.Base') as mock_base:

                # Mock empty dataframe (no data to migrate)
                mock_df = MagicMock()
                mock_df.__len__.return_value = 0
                mock_read.return_value = mock_df

                result = db_manager._migrate_sqlite_to_postgres()

                # Should return True for successful migration
                assert result == True

                # Should create PostgreSQL schema
                mock_base.metadata.create_all.assert_called_once_with(bind=mock_postgres_engine)

    def test_migrate_postgres_to_sqlite(self):
        """Test PostgreSQL to SQLite migration"""
        with patch('src.common.db_manager.config', self.mock_config):
            db_manager = DatabaseManager()

            # Mock pandas and SQLAlchemy components
            mock_sqlite_engine = MagicMock()
            mock_postgres_engine = MagicMock()

            with patch.object(db_manager, '_get_sqlite_engine', return_value=mock_sqlite_engine), \
                 patch.object(db_manager, '_get_postgres_engine', return_value=mock_postgres_engine), \
                 patch('src.common.db_manager.pd.read_sql_table') as mock_read, \
                 patch('src.common.db_manager.Base') as mock_base:

                # Mock dataframe with some data
                mock_df = MagicMock()
                mock_df.__len__.return_value = 5  # 5 records
                mock_read.return_value = mock_df

                result = db_manager._migrate_postgres_to_sqlite()

                # Should return True for successful migration
                assert result == True

                # Should create SQLite schema
                mock_base.metadata.create_all.assert_called_once_with(bind=mock_sqlite_engine)

                # Should write data to SQLite
                mock_df.to_sql.assert_called()

class TestDatabaseSetup:
    """Test database setup with migration handling"""

    def test_setup_database_no_migration_needed(self):
        """Test database setup when no migration is needed"""
        mock_config = MagicMock()
        mock_config.auto_migrate = True

        with patch('src.common.db_manager.config', mock_config):
            db_manager = DatabaseManager()

            with patch.object(db_manager, 'check_migration_needed', return_value=None), \
                 patch.object(db_manager, 'initialize_database'), \
                 patch.object(db_manager, 'get_database_info', return_value={'database_type': 'SQLite', 'total_records': 0}):

                result = db_manager.setup_database()

                assert result == True
                db_manager.initialize_database.assert_called_once()

    def test_setup_database_with_auto_migration(self):
        """Test database setup with automatic migration"""
        mock_config = MagicMock()
        mock_config.auto_migrate = True

        with patch('src.common.db_manager.config', mock_config):
            db_manager = DatabaseManager()

            with patch.object(db_manager, 'check_migration_needed', return_value="sqlite_to_postgres"), \
                 patch.object(db_manager, 'backup_database', return_value="backup.db"), \
                 patch.object(db_manager, 'migrate_data', return_value=True), \
                 patch.object(db_manager, 'initialize_database'), \
                 patch.object(db_manager, 'get_database_info', return_value={'database_type': 'PostgreSQL', 'total_records': 10}):

                result = db_manager.setup_database()

                assert result == True
                db_manager.backup_database.assert_called_once()
                db_manager.migrate_data.assert_called_once_with("sqlite_to_postgres", confirm=True)
                db_manager.initialize_database.assert_called_once()

    def test_setup_database_migration_disabled(self):
        """Test database setup when auto-migration is disabled"""
        mock_config = MagicMock()
        mock_config.auto_migrate = False

        with patch('src.common.db_manager.config', mock_config):
            db_manager = DatabaseManager()

            with patch.object(db_manager, 'check_migration_needed', return_value="postgres_to_sqlite"), \
                 patch.object(db_manager, 'migrate_data') as mock_migrate, \
                 patch.object(db_manager, 'initialize_database'), \
                 patch.object(db_manager, 'get_database_info', return_value={'database_type': 'SQLite', 'total_records': 0}):

                result = db_manager.setup_database()

                assert result == True
                # Migration should not be called when disabled
                mock_migrate.assert_not_called()
                db_manager.initialize_database.assert_called_once()

def run_all_tests():
    """Run all database configuration and migration tests"""
    logger.info("🚀 Starting Database Configuration & Migration Tests")
    logger.info("=" * 60)

    # Run pytest with this file
    pytest_args = [
        __file__,
        '-v',
        '--tb=short',
        '-x'  # Stop on first failure
    ]

    exit_code = pytest.main(pytest_args)

    if exit_code == 0:
        logger.info("\n🎉 All database tests passed!")
        logger.info("✅ Database configuration system is working correctly")
        logger.info("✅ Database migration system is working correctly")
        logger.info("✅ Auto-migration logic is working correctly")
    else:
        logger.error("\n❌ Some database tests failed!")
        logger.error("Please check the test output above")

    return exit_code

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

#!/usr/bin/env python3
# test_cli_database.py - Tests for CLI database configuration options

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

class TestCLIDatabaseOptions:
    """Test CLI database configuration options"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_sqlite_path = os.path.join(self.temp_dir, "cli_test.db")

    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_cli_help_includes_database_options(self):
        """Test that CLI help includes database configuration options"""
        result = subprocess.run([
            sys.executable, 'run_patterniq.py', '--help'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        help_text = result.stdout.lower()

        # Check for database-related options
        assert '--db-mode' in help_text
        assert '--sqlite-path' in help_text
        assert '--no-migrate' in help_text
        assert 'auto' in help_text
        assert 'sqlite' in help_text
        assert 'postgres' in help_text

    def test_cli_database_mode_parsing(self):
        """Test CLI database mode argument parsing"""
        # Import the CLI module to test argument parsing
        from run_patterniq import setup_environment

        # Test auto mode
        with patch.dict(os.environ, {}, clear=True):
            setup_environment("batch", db_mode="auto")
            assert os.environ.get("DB_MODE") == "auto"

        # Test sqlite mode
        with patch.dict(os.environ, {}, clear=True):
            setup_environment("batch", db_mode="sqlite")
            assert os.environ.get("DB_MODE") == "sqlite"

        # Test postgres mode
        with patch.dict(os.environ, {}, clear=True):
            setup_environment("batch", db_mode="postgres")
            assert os.environ.get("DB_MODE") == "postgres"

    def test_cli_sqlite_path_configuration(self):
        """Test CLI SQLite path configuration"""
        from run_patterniq import setup_environment

        custom_path = "/custom/path/test.db"

        with patch.dict(os.environ, {}, clear=True):
            setup_environment("batch", sqlite_path=custom_path)
            assert os.environ.get("SQLITE_PATH") == custom_path

    def test_cli_no_migrate_option(self):
        """Test CLI no-migrate option"""
        from run_patterniq import setup_environment

        with patch.dict(os.environ, {}, clear=True):
            setup_environment("batch", no_migrate=True)
            assert os.environ.get("AUTO_MIGRATE") == "false"

    def test_cli_combined_database_options(self):
        """Test combining multiple database CLI options"""
        from run_patterniq import setup_environment

        with patch.dict(os.environ, {}, clear=True):
            setup_environment(
                "batch",
                db_mode="sqlite",
                sqlite_path=self.test_sqlite_path,
                no_migrate=True
            )

            assert os.environ.get("DB_MODE") == "sqlite"
            assert os.environ.get("SQLITE_PATH") == self.test_sqlite_path
            assert os.environ.get("AUTO_MIGRATE") == "false"

class TestMigrationUtilityCLI:
    """Test the database migration utility CLI"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_sqlite_path = os.path.join(self.temp_dir, "migration_test.db")

    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_migration_utility_help(self):
        """Test migration utility help command"""
        result = subprocess.run([
            sys.executable, 'migrate_database.py', '--help'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        help_text = result.stdout.lower()

        # Check for migration actions
        assert 'info' in help_text
        assert 'backup' in help_text
        assert 'sqlite-to-postgres' in help_text
        assert 'postgres-to-sqlite' in help_text

        # Check for options
        assert '--sqlite-path' in help_text
        assert '--postgres-url' in help_text
        assert '--yes' in help_text

    def test_migration_utility_info_command(self):
        """Test migration utility info command"""
        # Mock the database manager to avoid real database connections
        with patch('migrate_database.db_manager') as mock_db_manager:
            mock_db_manager.get_database_info.return_value = {
                'database_type': 'SQLite',
                'total_records': 42,
                'tables': {'instruments': 10, 'bars_1d': 32}
            }

            # Import and run the migration utility function
            from migrate_database import show_database_info

            # Should not raise an exception
            show_database_info()

            # Should call get_database_info twice (SQLite and PostgreSQL)
            assert mock_db_manager.get_database_info.call_count >= 2

    def test_migration_utility_backup_command(self):
        """Test migration utility backup command"""
        with patch('migrate_database.db_manager') as mock_db_manager:
            mock_db_manager.backup_database.return_value = "backup_test_123.db"

            from migrate_database import create_backup

            backup_path = create_backup()

            assert backup_path == "backup_test_123.db"
            mock_db_manager.backup_database.assert_called_once_with("manual_backup")

    def test_migration_sqlite_to_postgres_function(self):
        """Test SQLite to PostgreSQL migration function"""
        with patch('migrate_database.config') as mock_config, \
             patch('migrate_database.db_manager') as mock_db_manager:

            mock_config.db_mode = "auto"
            mock_db_manager.migrate_data.return_value = True

            from migrate_database import migrate_sqlite_to_postgres

            result = migrate_sqlite_to_postgres()

            assert result == True
            mock_db_manager.migrate_data.assert_called_once_with("sqlite_to_postgres", confirm=True)

    def test_migration_postgres_to_sqlite_function(self):
        """Test PostgreSQL to SQLite migration function"""
        with patch('migrate_database.config') as mock_config, \
             patch('migrate_database.db_manager') as mock_db_manager:

            mock_config.db_mode = "auto"
            mock_db_manager.migrate_data.return_value = True

            from migrate_database import migrate_postgres_to_sqlite

            result = migrate_postgres_to_sqlite()

            assert result == True
            mock_db_manager.migrate_data.assert_called_once_with("postgres_to_sqlite", confirm=True)

class TestIntegratedDatabaseModes:
    """Test integrated database mode scenarios"""

    def test_batch_mode_auto_sqlite(self):
        """Test batch mode automatically uses SQLite"""
        with patch.dict(os.environ, {
            'DB_MODE': 'auto',
            'PATTERNIQ_ALWAYS_ON': 'false'
        }):
            from src.common.config import load_config
            config = load_config()

            assert config.db_mode == "auto"
            assert config.always_on == False
            assert config.is_using_sqlite() == True

    def test_always_on_mode_auto_postgres(self):
        """Test always-on mode automatically uses PostgreSQL"""
        with patch.dict(os.environ, {
            'DB_MODE': 'auto',
            'PATTERNIQ_ALWAYS_ON': 'true'
        }):
            from src.common.config import load_config
            config = load_config()

            assert config.db_mode == "auto"
            assert config.always_on == True
            assert config.is_using_postgres() == True

    def test_override_auto_mode_with_explicit_setting(self):
        """Test overriding auto mode with explicit database setting"""
        # Force SQLite even in always-on mode
        with patch.dict(os.environ, {
            'DB_MODE': 'sqlite',
            'PATTERNIQ_ALWAYS_ON': 'true'
        }):
            from src.common.config import load_config
            config = load_config()

            assert config.db_mode == "sqlite"
            assert config.always_on == True
            assert config.is_using_sqlite() == True  # Should override auto-selection

    def test_batch_with_forced_postgres(self):
        """Test batch mode with forced PostgreSQL"""
        with patch.dict(os.environ, {
            'DB_MODE': 'postgres',
            'PATTERNIQ_ALWAYS_ON': 'false'
        }):
            from src.common.config import load_config
            config = load_config()

            assert config.db_mode == "postgres"
            assert config.always_on == False
            assert config.is_using_postgres() == True

    def test_directory_creation_for_sqlite(self):
        """Test that SQLite directory is created automatically"""
        test_path = "deep/nested/path/test.db"

        with patch.dict(os.environ, {
            'DB_MODE': 'sqlite',
            'SQLITE_PATH': test_path
        }):
            with patch('os.makedirs') as mock_makedirs:
                from src.common.config import load_config
                config = load_config()

                # Should trigger directory creation when getting effective URL
                config.get_effective_db_url()

                # Should create the directory
                mock_makedirs.assert_called_with("deep/nested/path", exist_ok=True)

class TestErrorHandling:
    """Test error handling in database configuration"""

    def test_invalid_database_mode_error(self):
        """Test error handling for invalid database mode"""
        from src.common.config import PatternIQConfig

        config = PatternIQConfig(db_mode="invalid_mode")

        with pytest.raises(ValueError) as exc_info:
            config.get_effective_db_url()

        assert "Invalid db_mode" in str(exc_info.value)
        assert "invalid_mode" in str(exc_info.value)

    def test_migration_failure_handling(self):
        """Test handling of migration failures"""
        with patch('migrate_database.db_manager') as mock_db_manager:
            mock_db_manager.migrate_data.return_value = False  # Simulate failure

            from migrate_database import migrate_sqlite_to_postgres

            result = migrate_sqlite_to_postgres()
            assert result == False

    def test_database_connection_error_handling(self):
        """Test handling of database connection errors"""
        from src.common.db_manager import DatabaseManager

        with patch('src.common.db_manager.create_engine') as mock_create:
            mock_create.side_effect = Exception("Connection failed")

            db_manager = DatabaseManager()

            # Should handle connection errors gracefully
            info = db_manager.get_database_info()
            assert "error" in info or info.get("total_records") == "N/A"

def run_all_tests():
    """Run all CLI and integration tests"""
    print("🚀 Starting CLI Database Configuration Tests")
    print("=" * 60)

    # Run pytest with this file
    pytest_args = [
        __file__,
        '-v',
        '--tb=short'
    ]

    exit_code = pytest.main(pytest_args)

    if exit_code == 0:
        print("\n🎉 All CLI database tests passed!")
        print("✅ CLI database options are working correctly")
        print("✅ Migration utility CLI is working correctly")
        print("✅ Database mode integration is working correctly")
    else:
        print("\n❌ Some CLI database tests failed!")

    return exit_code

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

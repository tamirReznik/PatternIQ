#!/usr/bin/env python3
# test_database_integration.py - Integration tests for database mode switching

import os
import sys
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

class TestDatabaseModeIntegration:
    """Integration tests for complete database mode switching scenarios"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_sqlite_path = os.path.join(self.temp_dir, "integration_test.db")

        # Create test directories
        os.makedirs(os.path.dirname(self.test_sqlite_path), exist_ok=True)
        Path("backups").mkdir(exist_ok=True)

    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # Clean up backup directory
        backup_dir = Path("backups")
        if backup_dir.exists():
            try:
                shutil.rmtree(backup_dir)
            except:
                pass

    async def test_batch_to_always_on_migration(self):
        """Test switching from batch (SQLite) to always-on (PostgreSQL)"""
        print("🧪 Testing batch → always-on migration...")

        # Step 1: Start in batch mode with SQLite
        with patch.dict(os.environ, {
            'DB_MODE': 'auto',
            'PATTERNIQ_ALWAYS_ON': 'false',
            'SQLITE_PATH': self.test_sqlite_path,
            'AUTO_MIGRATE': 'true'
        }):
            from src.main import PatternIQOrchestrator
            from src.common.config import load_config

            config = load_config()
            assert config.is_using_sqlite() == True
            assert config.always_on == False

            # Mock the pipeline components to avoid real execution
            with patch('src.main.demo_full_data_ingestion'), \
                 patch('src.main.demo_momentum_features'), \
                 patch('src.main.demo_signal_generation'), \
                 patch('src.main.blend_signals_ic_weighted'), \
                 patch('src.main.generate_daily_report'), \
                 patch('sys.exit') as mock_exit:

                orchestrator = PatternIQOrchestrator()
                # Mock trading bot to avoid file operations
                orchestrator.trading_bot = MagicMock()
                orchestrator.trading_bot.process_daily_report.return_value = {"status": "success"}
                orchestrator.trading_bot.get_portfolio_status.return_value = {
                    "initial_capital": 100000, "current_value": 101000, "total_return": "1.00%"
                }

                await orchestrator.run_batch_mode()
                mock_exit.assert_called_once_with(0)

        # Step 2: Switch to always-on mode with PostgreSQL
        with patch.dict(os.environ, {
            'DB_MODE': 'auto',
            'PATTERNIQ_ALWAYS_ON': 'true',
            'SQLITE_PATH': self.test_sqlite_path,
            'AUTO_MIGRATE': 'true'
        }):
            config = load_config()
            assert config.is_using_postgres() == True
            assert config.always_on == True

            print("✅ Batch → Always-On migration scenario verified")

    async def test_always_on_to_batch_migration(self):
        """Test switching from always-on (PostgreSQL) to batch (SQLite)"""
        print("🧪 Testing always-on → batch migration...")

        # Step 1: Start in always-on mode with PostgreSQL
        with patch.dict(os.environ, {
            'DB_MODE': 'auto',
            'PATTERNIQ_ALWAYS_ON': 'true',
            'SQLITE_PATH': self.test_sqlite_path,
            'AUTO_MIGRATE': 'true'
        }):
            from src.common.config import load_config

            config = load_config()
            assert config.is_using_postgres() == True
            assert config.always_on == True

        # Step 2: Switch to batch mode with SQLite
        with patch.dict(os.environ, {
            'DB_MODE': 'auto',
            'PATTERNIQ_ALWAYS_ON': 'false',
            'SQLITE_PATH': self.test_sqlite_path,
            'AUTO_MIGRATE': 'true'
        }):
            config = load_config()
            assert config.is_using_sqlite() == True
            assert config.always_on == False

            print("✅ Always-On → Batch migration scenario verified")

    def test_manual_database_mode_override(self):
        """Test manual database mode override scenarios"""
        print("🧪 Testing manual database mode overrides...")

        # Test forcing SQLite in always-on mode
        with patch.dict(os.environ, {
            'DB_MODE': 'sqlite',
            'PATTERNIQ_ALWAYS_ON': 'true',
            'SQLITE_PATH': self.test_sqlite_path
        }):
            from src.common.config import load_config

            config = load_config()
            assert config.is_using_sqlite() == True
            assert config.always_on == True  # Always-on mode but with SQLite

        # Test forcing PostgreSQL in batch mode
        with patch.dict(os.environ, {
            'DB_MODE': 'postgres',
            'PATTERNIQ_ALWAYS_ON': 'false',
            'PATTERNIQ_DB_URL': 'postgresql://test:test@localhost:5432/test'
        }):
            config = load_config()
            assert config.is_using_postgres() == True
            assert config.always_on == False  # Batch mode but with PostgreSQL

        print("✅ Manual database mode overrides verified")

    def test_migration_with_auto_migrate_disabled(self):
        """Test behavior when auto-migration is disabled"""
        print("🧪 Testing auto-migration disabled scenario...")

        with patch.dict(os.environ, {
            'DB_MODE': 'auto',
            'PATTERNIQ_ALWAYS_ON': 'false',
            'AUTO_MIGRATE': 'false',  # Disable auto-migration
            'SQLITE_PATH': self.test_sqlite_path
        }):
            from src.common.db_manager import DatabaseManager
            from src.common.config import load_config

            config = load_config()
            assert config.auto_migrate == False

            # Mock database manager to simulate existing data in other database
            with patch.object(DatabaseManager, 'check_migration_needed', return_value="postgres_to_sqlite"), \
                 patch.object(DatabaseManager, 'migrate_data') as mock_migrate, \
                 patch.object(DatabaseManager, 'initialize_database'), \
                 patch.object(DatabaseManager, 'get_database_info', return_value={'database_type': 'SQLite', 'total_records': 0}):

                db_manager = DatabaseManager()
                result = db_manager.setup_database()

                # Should setup successfully but not migrate
                assert result == True
                mock_migrate.assert_not_called()

        print("✅ Auto-migration disabled scenario verified")

    def test_database_backup_before_migration(self):
        """Test that backups are created before migration"""
        print("🧪 Testing backup creation before migration...")

        with patch.dict(os.environ, {
            'AUTO_MIGRATE': 'true',
            'SQLITE_PATH': self.test_sqlite_path
        }):
            from src.common.db_manager import DatabaseManager

            with patch.object(DatabaseManager, 'check_migration_needed', return_value="sqlite_to_postgres"), \
                 patch.object(DatabaseManager, 'backup_database', return_value="test_backup.db") as mock_backup, \
                 patch.object(DatabaseManager, 'migrate_data', return_value=True), \
                 patch.object(DatabaseManager, 'initialize_database'), \
                 patch.object(DatabaseManager, 'get_database_info', return_value={'database_type': 'PostgreSQL', 'total_records': 5}):

                db_manager = DatabaseManager()
                result = db_manager.setup_database()

                assert result == True
                mock_backup.assert_called_once()

        print("✅ Backup creation before migration verified")

    def test_cli_database_options_integration(self):
        """Test CLI database options integration"""
        print("🧪 Testing CLI database options integration...")

        from run_patterniq import setup_environment

        # Test complete CLI setup with database options
        with patch.dict(os.environ, {}, clear=True):
            setup_environment(
                "batch",
                db_mode="sqlite",
                sqlite_path=self.test_sqlite_path,
                no_migrate=True,
                telegram=True,
                port=9000
            )

            # Verify all environment variables are set correctly
            assert os.environ.get("PATTERNIQ_ALWAYS_ON") == "false"
            assert os.environ.get("DB_MODE") == "sqlite"
            assert os.environ.get("SQLITE_PATH") == self.test_sqlite_path
            assert os.environ.get("AUTO_MIGRATE") == "false"
            assert os.environ.get("SEND_TELEGRAM_ALERTS") == "true"
            assert os.environ.get("API_PORT") == "9000"

        print("✅ CLI database options integration verified")

    def test_error_handling_during_migration(self):
        """Test error handling during database migration"""
        print("🧪 Testing error handling during migration...")

        from src.common.db_manager import DatabaseManager

        with patch.dict(os.environ, {
            'AUTO_MIGRATE': 'true',
            'SQLITE_PATH': self.test_sqlite_path
        }):
            with patch.object(DatabaseManager, 'check_migration_needed', return_value="sqlite_to_postgres"), \
                 patch.object(DatabaseManager, 'backup_database', return_value="backup.db"), \
                 patch.object(DatabaseManager, 'migrate_data', return_value=False), \
                 patch.object(DatabaseManager, 'initialize_database'), \
                 patch.object(DatabaseManager, 'get_database_info', return_value={'database_type': 'SQLite', 'total_records': 0}):

                db_manager = DatabaseManager()
                result = db_manager.setup_database()

                # Should handle migration failure gracefully
                assert result == False

        print("✅ Error handling during migration verified")

    async def test_real_database_mode_switching(self):
        """Test actual database mode switching with mocked engines"""
        print("🧪 Testing real database mode switching...")

        from src.common.db_manager import DatabaseManager

        # Create a real database manager instance
        db_manager = DatabaseManager()

        # Mock the engines to avoid real database connections
        mock_sqlite_engine = MagicMock()
        mock_postgres_engine = MagicMock()

        with patch.object(db_manager, '_get_sqlite_engine', return_value=mock_sqlite_engine), \
             patch.object(db_manager, '_get_postgres_engine', return_value=mock_postgres_engine):

            # Test getting SQLite engine
            engine = db_manager.get_engine(force_sqlite=True)
            assert engine == mock_sqlite_engine

            # Test getting PostgreSQL engine
            engine = db_manager.get_engine(force_postgres=True)
            assert engine == mock_postgres_engine

        print("✅ Real database mode switching verified")

class TestCompleteWorkflows:
    """Test complete end-to-end workflows"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_sqlite_path = os.path.join(self.temp_dir, "workflow_test.db")

    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    async def test_complete_batch_workflow_sqlite(self):
        """Test complete batch workflow with SQLite"""
        print("🧪 Testing complete batch workflow with SQLite...")

        with patch.dict(os.environ, {
            'DB_MODE': 'sqlite',
            'PATTERNIQ_ALWAYS_ON': 'false',
            'SQLITE_PATH': self.test_sqlite_path,
            'GENERATE_REPORTS': 'false',
            'SEND_TELEGRAM_ALERTS': 'false'
        }):
            # Mock all pipeline components and database operations
            with patch('src.common.db_manager.create_engine') as mock_create_engine, \
                 patch('src.main.demo_full_data_ingestion'), \
                 patch('src.main.demo_momentum_features'), \
                 patch('src.main.demo_signal_generation'), \
                 patch('src.main.blend_signals_ic_weighted'), \
                 patch('sys.exit') as mock_exit:

                # Mock SQLite engine
                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine

                from src.main import PatternIQOrchestrator

                orchestrator = PatternIQOrchestrator()
                orchestrator.trading_bot = MagicMock()
                orchestrator.trading_bot.process_daily_report.return_value = {"status": "success"}
                orchestrator.trading_bot.get_portfolio_status.return_value = {
                    "initial_capital": 100000, "current_value": 102000, "total_return": "2.00%"
                }

                await orchestrator.run_batch_mode()

                # Should exit cleanly in batch mode
                mock_exit.assert_called_once_with(0)

        print("✅ Complete batch workflow with SQLite verified")

    async def test_complete_always_on_workflow_postgres(self):
        """Test complete always-on workflow with PostgreSQL"""
        print("🧪 Testing complete always-on workflow with PostgreSQL...")

        with patch.dict(os.environ, {
            'DB_MODE': 'postgres',
            'PATTERNIQ_ALWAYS_ON': 'true',
            'START_API_SERVER': 'true',
            'GENERATE_REPORTS': 'false',
            'SEND_TELEGRAM_ALERTS': 'false'
        }):
            # Mock all components
            with patch('src.common.db_manager.create_engine') as mock_create_engine, \
                 patch('asyncio.create_task') as mock_create_task, \
                 patch('asyncio.sleep', side_effect=KeyboardInterrupt), \
                 patch('src.main.PatternIQOrchestrator.run_daily_pipeline', new_callable=AsyncMock, return_value=True):

                # Mock PostgreSQL engine
                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine

                from src.main import PatternIQOrchestrator

                orchestrator = PatternIQOrchestrator()

                # Should start API server and run pipeline
                try:
                    await orchestrator.run_always_on_mode()
                except KeyboardInterrupt:
                    pass  # Expected for test

                # API server should be started
                mock_create_task.assert_called_once()

        print("✅ Complete always-on workflow with PostgreSQL verified")

async def run_integration_tests():
    """Run all integration tests"""
    print("🚀 Starting Database Mode Integration Tests")
    print("=" * 60)

    # Create test instances
    db_integration = TestDatabaseModeIntegration()
    workflows = TestCompleteWorkflows()

    tests = [
        ("Database Mode Integration Setup", lambda: (db_integration.setup_method(), workflows.setup_method())),
        ("Batch → Always-On Migration", db_integration.test_batch_to_always_on_migration),
        ("Always-On → Batch Migration", db_integration.test_always_on_to_batch_migration),
        ("Manual Database Mode Override", db_integration.test_manual_database_mode_override),
        ("Auto-Migration Disabled", db_integration.test_migration_with_auto_migrate_disabled),
        ("Backup Before Migration", db_integration.test_database_backup_before_migration),
        ("CLI Database Options Integration", db_integration.test_cli_database_options_integration),
        ("Error Handling During Migration", db_integration.test_error_handling_during_migration),
        ("Real Database Mode Switching", db_integration.test_real_database_mode_switching),
        ("Complete Batch Workflow (SQLite)", workflows.test_complete_batch_workflow_sqlite),
        ("Complete Always-On Workflow (PostgreSQL)", workflows.test_complete_always_on_workflow_postgres),
        ("Cleanup", lambda: (db_integration.teardown_method(), workflows.teardown_method()))
    ]

    results = []
    for name, test_func in tests:
        print(f"\n📋 Running: {name}")
        print("-" * 40)

        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            results.append((name, True))
            print(f"✅ {name} PASSED")
        except Exception as e:
            print(f"❌ {name} FAILED: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        if name not in ["Database Mode Integration Setup", "Cleanup"]:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status:<10} {name}")

    print("-" * 60)
    print(f"Results: {passed-2}/{total-2} tests passed")  # Exclude setup/cleanup

    if passed == total:
        print("\n🎉 All integration tests passed!")
        return True
    else:
        print(f"\n⚠️ {total-passed} tests failed.")
        return False

async def main():
    """Main entry point"""
    success = await run_integration_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())

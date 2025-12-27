#!/bin/bash
# move_tests.sh - Move all test files from root to tests/ directory

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "📦 Moving test files to tests/ directory..."
echo ""

# Create test directories if they don't exist
mkdir -p tests/data tests/signals tests/trading tests/integration tests/features tests/api

# Move test files based on their content/name
# Data-related tests
for test_file in test_data_sources.py test_database*.py test_adjustment*.py; do
    if [ -f "$test_file" ]; then
        mv "$test_file" tests/data/
        echo "✅ Moved $test_file → tests/data/"
    fi
done

# Signal-related tests
for test_file in test_simple_reports.py; do
    if [ -f "$test_file" ]; then
        mv "$test_file" tests/signals/
        echo "✅ Moved $test_file → tests/signals/"
    fi
done

# Trading-related tests
for test_file in test_enhanced_trading_bot.py test_enhanced_performance.py; do
    if [ -f "$test_file" ]; then
        mv "$test_file" tests/trading/
        echo "✅ Moved $test_file → tests/trading/"
    fi
done

# Integration tests
for test_file in test_batch_run.py test_pipeline*.py test_modes*.py test_operating*.py test_all*.py test_cli*.py test_patterniq*.py; do
    if [ -f "$test_file" ]; then
        mv "$test_file" tests/integration/
        echo "✅ Moved $test_file → tests/integration/"
    fi
done

# API tests
for test_file in test_telegram_bot.py; do
    if [ -f "$test_file" ]; then
        mv "$test_file" tests/api/
        echo "✅ Moved $test_file → tests/api/"
    fi
done

echo ""
echo "✅ Test file migration complete!"
echo ""
echo "Note: You may need to update imports in test files to reflect new locations."


#!/bin/bash
# Script to organize test files into tests/ directory

PROJECT_ROOT="$(dirname "$(dirname "$(realpath "$0")")")"
cd "$PROJECT_ROOT"

echo "Organizing test files..."

# Move test files from root to appropriate test directories
# Based on their content/name, organize them

# Data tests
if [ -f "test_database_integration.py" ]; then
    mv test_database_integration.py tests/data/test_database_integration.py
    echo "Moved test_database_integration.py"
fi

if [ -f "test_database_modes.py" ]; then
    mv test_database_modes.py tests/data/test_database_modes.py
    echo "Moved test_database_modes.py"
fi

if [ -f "test_cli_database.py" ]; then
    mv test_cli_database.py tests/data/test_cli_database.py
    echo "Moved test_cli_database.py"
fi

if [ -f "test_all_database_features.py" ]; then
    mv test_all_database_features.py tests/data/test_all_database_features.py
    echo "Moved test_all_database_features.py"
fi

# Integration tests
if [ -f "test_pipeline_basic.py" ]; then
    mv test_pipeline_basic.py tests/integration/test_pipeline_basic.py
    echo "Moved test_pipeline_basic.py"
fi

if [ -f "test_pipeline_modes.py" ]; then
    mv test_pipeline_modes.py tests/integration/test_pipeline_modes.py
    echo "Moved test_pipeline_modes.py"
fi

if [ -f "test_modes_integration.py" ]; then
    mv test_modes_integration.py tests/integration/test_modes_integration.py
    echo "Moved test_modes_integration.py"
fi

if [ -f "test_all_modes.py" ]; then
    mv test_all_modes.py tests/integration/test_all_modes.py
    echo "Moved test_all_modes.py"
fi

if [ -f "test_basic_modes.py" ]; then
    mv test_basic_modes.py tests/integration/test_basic_modes.py
    echo "Moved test_basic_modes.py"
fi

if [ -f "test_operating_modes.py" ]; then
    mv test_operating_modes.py tests/integration/test_operating_modes.py
    echo "Moved test_operating_modes.py"
fi

if [ -f "test_patterniq_modes.py" ]; then
    mv test_patterniq_modes.py tests/integration/test_patterniq_modes.py
    echo "Moved test_patterniq_modes.py"
fi

if [ -f "test_batch_run.py" ]; then
    mv test_batch_run.py tests/integration/test_batch_run.py
    echo "Moved test_batch_run.py"
fi

# Feature tests
if [ -f "test_all_features.py" ]; then
    mv test_all_features.py tests/features/test_all_features.py
    echo "Moved test_all_features.py"
fi

# Report tests
if [ -f "test_simple_reports.py" ]; then
    mv test_simple_reports.py tests/integration/test_simple_reports.py
    echo "Moved test_simple_reports.py"
fi

# Trading tests
if [ -f "test_enhanced_performance.py" ]; then
    mv test_enhanced_performance.py tests/trading/test_enhanced_performance.py
    echo "Moved test_enhanced_performance.py"
fi

# Telegram tests
if [ -f "test_telegram_bot.py" ]; then
    mv test_telegram_bot.py tests/integration/test_telegram_bot.py
    echo "Moved test_telegram_bot.py"
fi

# Adjust tests
if [ -f "test_adjustment_simple.py" ]; then
    mv test_adjustment_simple.py tests/adjust/test_adjustment_simple.py
    echo "Moved test_adjustment_simple.py"
fi

echo "✅ Test file organization complete!"


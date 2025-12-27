#!/bin/bash
# Organize root directory files into proper structure

PROJECT_ROOT="$(dirname "$(dirname "$(realpath "$0")")")"
cd "$PROJECT_ROOT"

echo "🧹 Organizing root directory files..."

# Create directories
mkdir -p scripts/runners
mkdir -p scripts/setup
mkdir -p scripts/dashboard
mkdir -p scripts/verify
mkdir -p config

# Move runner scripts
echo "📦 Moving runner scripts..."
[ -f "macos_daily_runner.py" ] && mv macos_daily_runner.py scripts/runners/ && echo "  ✓ macos_daily_runner.py"
[ -f "cloud_batch_runner.py" ] && mv cloud_batch_runner.py scripts/runners/ && echo "  ✓ cloud_batch_runner.py"
[ -f "direct_batch_runner.py" ] && mv direct_batch_runner.py scripts/runners/ && echo "  ✓ direct_batch_runner.py"
[ -f "debug_batch.py" ] && mv debug_batch.py scripts/runners/ && echo "  ✓ debug_batch.py"

# Move simulation scripts
echo "📊 Moving simulation scripts..."
[ -f "flexible_simulation.py" ] && mv flexible_simulation.py scripts/simulations/ && echo "  ✓ flexible_simulation.py"
[ -f "historical_backtest.py" ] && mv historical_backtest.py scripts/simulations/ && echo "  ✓ historical_backtest.py"
[ -f "quick_simulation.py" ] && mv quick_simulation.py scripts/simulations/ && echo "  ✓ quick_simulation.py"
[ -f "bot_performance_simulation.py" ] && mv bot_performance_simulation.py scripts/simulations/ && echo "  ✓ bot_performance_simulation.py"
[ -f "performance_enhancement_analysis.py" ] && mv performance_enhancement_analysis.py scripts/simulations/ && echo "  ✓ performance_enhancement_analysis.py"

# Move setup scripts
echo "⚙️  Moving setup scripts..."
[ -f "setup_db.py" ] && mv setup_db.py scripts/setup/ && echo "  ✓ setup_db.py"
[ -f "setup_telegram.py" ] && mv setup_telegram.py scripts/setup/ && echo "  ✓ setup_telegram.py"
[ -f "setup_macos_scheduling.sh" ] && mv setup_macos_scheduling.sh scripts/setup/ && echo "  ✓ setup_macos_scheduling.sh"
[ -f "migrate_database.py" ] && mv migrate_database.py scripts/setup/ && echo "  ✓ migrate_database.py"

# Move dashboard scripts
echo "📈 Moving dashboard scripts..."
[ -f "dashboard.py" ] && mv dashboard.py scripts/dashboard/ && echo "  ✓ dashboard.py"
[ -f "static_dashboard_generator.py" ] && mv static_dashboard_generator.py scripts/dashboard/ && echo "  ✓ static_dashboard_generator.py"

# Move verification scripts
echo "✅ Moving verification scripts..."
[ -f "verify_section_2.py" ] && mv verify_section_2.py scripts/verify/ && echo "  ✓ verify_section_2.py"
[ -f "verify_section_3.py" ] && mv verify_section_3.py scripts/verify/ && echo "  ✓ verify_section_3.py"
[ -f "verify_section_4.py" ] && mv verify_section_4.py scripts/verify/ && echo "  ✓ verify_section_4.py"
[ -f "simple_test.py" ] && mv simple_test.py scripts/verify/ && echo "  ✓ simple_test.py"

# Move demo scripts
echo "🎭 Moving demo scripts..."
[ -f "run_batch_demo.py" ] && mv run_batch_demo.py scripts/demo/ && echo "  ✓ run_batch_demo.py"

# Move config files
echo "⚙️  Moving config files..."
[ -f "cloud-run.yaml" ] && mv cloud-run.yaml config/ && echo "  ✓ cloud-run.yaml"
[ -f "com.patterniq.daily.plist" ] && mv com.patterniq.daily.plist config/ && echo "  ✓ com.patterniq.daily.plist"

# Move deploy script
echo "🚀 Moving deploy script..."
[ -f "deploy.sh" ] && mv deploy.sh scripts/ && echo "  ✓ deploy.sh"

echo ""
echo "✅ Root directory organization complete!"
echo ""
echo "📁 Files that should remain in root:"
echo "   - README.md"
echo "   - requirements.txt"
echo "   - Dockerfile"
echo "   - run_patterniq.py (main entry point)"
echo "   - .gitignore"
echo "   - .env.example (if exists)"


#!/bin/bash
# Wrapper script for run_backtest.py that automatically activates venv

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Check if venv exists
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
    echo "Please create it first: python3 -m venv venv"
    exit 1
fi

# Activate venv
source "$PROJECT_ROOT/venv/bin/activate"

# Check if activation was successful
if [ "$VIRTUAL_ENV" = "" ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Run the backtest script with all arguments
cd "$PROJECT_ROOT"
python "$SCRIPT_DIR/run_backtest.py" "$@"

# Exit with the same code as the Python script
exit $?


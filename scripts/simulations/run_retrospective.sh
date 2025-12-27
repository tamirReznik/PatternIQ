#!/bin/bash
# Wrapper script for run_retrospective.py that automatically activates venv

# Get project root (go up from scripts/simulations/ to project root)
PROJECT_ROOT="$(cd "$(dirname "$(dirname "$(realpath "$0")")")" && pwd)"

# Check if venv exists
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
    echo "Please create it first: python3 -m venv venv"
    exit 1
fi

# Activate venv
source "$PROJECT_ROOT/venv/bin/activate"

# Execute the Python retrospective script with all arguments
python "$PROJECT_ROOT/scripts/simulations/run_retrospective.py" "$@"


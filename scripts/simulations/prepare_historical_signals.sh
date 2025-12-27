#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Execute the Python script with all arguments
python scripts/simulations/prepare_historical_signals.py "$@"


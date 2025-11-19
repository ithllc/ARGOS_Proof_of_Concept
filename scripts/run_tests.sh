#!/bin/bash

# This script runs the unit tests for the Mini-ARGOS POC.

# Get the directory of this script to set paths correctly.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"
SRC_DIR="$PROJECT_ROOT/src"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Add the project root and 'src' directory to the PYTHONPATH to resolve module imports.
export PYTHONPATH="$PROJECT_ROOT:$SRC_DIR:$PYTHONPATH"

echo "PYTHONPATH set to: $PYTHONPATH"
echo "Running unit tests with interpreter: $VENV_PYTHON"

# Use the virtual environment's python interpreter to discover and run tests.
"$VENV_PYTHON" -m unittest discover -s "$PROJECT_ROOT/tests" -p "test_*.py"

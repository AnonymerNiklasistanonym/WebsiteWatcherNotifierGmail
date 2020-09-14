#!/usr/bin/env bash

# This script is optional and only exists to run it isolated from other Python programs.
# To run it without this script simply run 'pip install -r requirements.txt' and then
# 'python3 -m main'.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PYTHON_VENV_DIR=$SCRIPT_DIR/venv_website_watcher
PYTHON_VENV_REQUIREMENTS_FILE=$SCRIPT_DIR/requirements.txt

# Make script stop when an error happens
set -e

# Go to script directory even when run from another one
cd "$SCRIPT_DIR"

# Create/Update and enter virtual environment
if ! [ -d "$PYTHON_VENV_DIR" ]; then
    python3.8 -m venv "$PYTHON_VENV_DIR"
    source "$PYTHON_VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$PYTHON_VENV_REQUIREMENTS_FILE"
else
    source "$PYTHON_VENV_DIR/bin/activate"
fi

# Run script in virtual environment
python3 -m main

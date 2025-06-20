#!/bin/bash

# Exit on error
set -e

# Check for argument
if [ -z "$1" ]; then
    echo "Usage: $0 /path/to/mod_folder"
    exit 1
fi

MOD_PATH="$1"

# Create virtual environment if it doesn't exist
#if [ ! -d "venv" ]; then
#    python3 -m venv venv
#fi

# Activate the virtual environment
#source venv/bin/activate

# Install dependencies
#pip install -r requirements.txt

# Run the mod viewer with the provided path
python3 mod_viewer.py "$MOD_PATH"


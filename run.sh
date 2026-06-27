#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Get the absolute directory path where this script resides
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if the virtual environment exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    # Activate virtual environment
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo "Error: Python virtual environment ('venv') not found." >&2
    echo "Please ensure you have run the setup and installed requirements first." >&2
    exit 1
fi

# Run the IPTV Playlist Cleaner and pass all CLI arguments
python3 -m iptv_cleaner.main "$@"

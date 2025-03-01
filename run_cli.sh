#!/bin/bash
# This script runs the CLI version of the trading bot

# Kill any existing web server process
pkill -f "gunicorn --bind 0.0.0.0:5000"

# Run the CLI interface
python new_main.py
#!/bin/bash

# Kill any existing server processes running on port 5000 or 8080
echo "Stopping existing server processes..."
pkill -f "gunicorn --bind 0.0.0.0:5000"
pkill -f "python.*minimal_server.py"
pkill -f "python.*main.py"
pkill -f "python.*app_runner.py"
sleep 2

# Start gunicorn via the app_runner entry point
echo "Starting main web application on port 5000..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload app_runner:app &
sleep 3

# Start minimal server on port 8080
echo "Starting minimal server on port 8080..."
python minimal_server.py &
sleep 3

echo "Servers started. Main app on port 5000, minimal server on port 8080"
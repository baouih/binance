#!/bin/bash
# Script to start the Flask application

# Export necessary environment variables
export FLASK_APP=main.py
export FLASK_ENV=development

# Kill any existing processes on port 5000
lsof -ti:5000 | xargs kill -9 2>/dev/null

# Start the Flask application
flask run --host=0.0.0.0 --port=5000
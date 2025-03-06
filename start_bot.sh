#!/bin/bash

# Check if port 5000 is already in use and kill that process if necessary
PORT_PID=$(lsof -i:5000 -t)
if [ ! -z "$PORT_PID" ]; then
    echo "Port 5000 is already in use by process $PORT_PID. Stopping it..."
    kill -9 $PORT_PID
    sleep 1
fi

# Export required environment variables
export FLASK_APP=app.py
export FLASK_ENV=development

# Start the Flask application
echo "Starting Binance Trading Bot..."
python app.py &

# Wait for the server to start
sleep 2

# Check if the server started successfully
if curl -s http://localhost:5000/health > /dev/null; then
    echo "Binance Trading Bot started successfully!"
    echo "Visit http://localhost:5000 to access the trading interface"
else
    echo "Failed to start Binance Trading Bot. Check the logs for errors."
fi
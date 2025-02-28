#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot Dashboard
"""

from app import app, socketio
from app.routes import start_background_tasks

# Start background tasks for simulating real-time data
start_background_tasks()

if __name__ == "__main__":
    # Run the application with Socket.IO support
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
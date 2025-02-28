#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot Dashboard
"""

import os
import logging
from flask import Flask
from flask_socketio import SocketIO

# Set up Flask application
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.secret_key = os.environ.get("SESSION_SECRET", "cryptobot-dev-key")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard")

# Socket.IO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Import routes after app is initialized
from app.routes import start_background_tasks

# Start background tasks for simulating real-time data
start_background_tasks()

if __name__ == "__main__":
    # Run the application with Socket.IO support
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
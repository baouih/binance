#!/usr/bin/env python3
"""
Web Dashboard for cryptocurrency trading bot
"""

import os
import logging
from flask import Flask
from flask_socketio import SocketIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard")

# Create Flask application
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')
app.secret_key = os.environ.get("SESSION_SECRET", "cryptobot-dev-key")

# Configure Socket.IO for real-time updates
# Use threading mode to avoid worker timeouts with gunicorn
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
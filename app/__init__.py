#!/usr/bin/env python3
"""
Web Dashboard cho bot giao dịch tiền điện tử
"""

import os
import json
import logging
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard")

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get("SESSION_SECRET", "cryptobot-dev-key")

# Socket.IO cho real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")
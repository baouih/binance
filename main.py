#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot Dashboard
"""

import os
import logging
from flask import Flask
from flask_socketio import SocketIO

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "cryptobot-dev-key")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("dashboard")

# Import dummy data and route definitions
import json
import random
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, redirect, url_for, session

# Giả lập dữ liệu bot
bot_status = {
    "running": True,
    "last_start_time": datetime.now() - timedelta(hours=12),
    "uptime": "12 hours",
    "version": "1.0.0",
    "active_strategies": ["Composite ML Strategy", "Multi-timeframe analyzer", "Sentiment-based counter"]
}

# Giả lập dữ liệu tài khoản
account_data = {
    "balance": 10253.42,
    "change_24h": 2.3,
    "positions": [
        {
            "id": "BTCUSDT_1",
            "symbol": "BTCUSDT",
            "type": "LONG",
            "entry_price": 82458.15,
            "current_price": 83768.54,
            "quantity": 0.025,
            "pnl": 32.61,
            "pnl_percent": 1.59
        },
        {
            "id": "ETHUSDT_1",
            "symbol": "ETHUSDT",
            "type": "SHORT",
            "entry_price": 2285.36,
            "current_price": 2212.85,
            "quantity": 0.35,
            "pnl": 25.38,
            "pnl_percent": 3.18
        }
    ]
}

# Giả lập dữ liệu tín hiệu giao dịch
signals_data = [
    {
        "time": "12:35:18",
        "symbol": "BTCUSDT",
        "signal": "BUY",
        "confidence": 78,
        "price": 83518.75,
        "market_regime": "NEUTRAL",
        "executed": False
    },
    {
        "time": "11:42:06",
        "symbol": "SOLUSDT",
        "signal": "SELL",
        "confidence": 82,
        "price": 126.48,
        "market_regime": "VOLATILE",
        "executed": False
    },
    {
        "time": "10:18:32",
        "symbol": "ETHUSDT",
        "signal": "SELL",
        "confidence": 75,
        "price": 2248.36,
        "market_regime": "VOLATILE",
        "executed": True
    }
]

# Giả lập dữ liệu phân tích thị trường
market_data = {
    "btc_price": 83768.54,
    "btc_change_24h": 1.5,
    "market_regime": {
        "BTC": "VOLATILE",
        "ETH": "VOLATILE",
        "BNB": "NEUTRAL",
        "SOL": "RANGING"
    },
    "sentiment": {
        "value": 16,  # 0-100
        "state": "extreme_fear",
        "description": "Extreme Fear"
    }
}

@app.route('/')
def index():
    """Trang chủ Dashboard"""
    return render_template('index.html')

@app.route('/strategies')
def strategies():
    """Trang quản lý chiến lược"""
    return render_template('strategies.html')

@app.route('/backtest')
def backtest():
    """Trang backtest"""
    return render_template('backtest.html')

@app.route('/trades')
def trades():
    """Trang lịch sử giao dịch"""
    return render_template('trades.html')

@app.route('/settings')
def settings():
    """Trang cài đặt bot"""
    return render_template('settings.html')

# API Routes
@app.route('/api/bot/control', methods=['POST'])
def bot_control():
    """Điều khiển bot (start/stop/restart)"""
    if not request.json or 'action' not in request.json:
        return jsonify({'status': 'error', 'message': 'Missing action parameter'}), 400
    
    action = request.json['action']
    
    if action == 'start':
        bot_status["running"] = True
        bot_status["last_start_time"] = datetime.now()
        logger.info("Bot started")
    elif action == 'stop':
        bot_status["running"] = False
        logger.info("Bot stopped")
    elif action == 'restart':
        bot_status["running"] = True
        bot_status["last_start_time"] = datetime.now()
        logger.info("Bot restarted")
    else:
        return jsonify({'status': 'error', 'message': 'Invalid action parameter'}), 400
    
    return jsonify({'status': 'success', 'action': action, 'bot_status': bot_status})

@app.route('/api/positions/close', methods=['POST'])
def close_position():
    """Đóng một vị thế"""
    if not request.json or 'position_id' not in request.json:
        return jsonify({'status': 'error', 'message': 'Missing position_id parameter'}), 400
    
    position_id = request.json['position_id']
    
    # Find and remove the position
    position_index = None
    for i, position in enumerate(account_data["positions"]):
        if position["id"] == position_id:
            position_index = i
            break
    
    if position_index is not None:
        removed_position = account_data["positions"].pop(position_index)
        logger.info(f"Position closed: {removed_position}")
        return jsonify({'status': 'success', 'position': removed_position})
    else:
        return jsonify({'status': 'error', 'message': 'Position not found'}), 404

@app.route('/api/bot/status')
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    status_data = bot_status.copy()
    status_data['last_start_time'] = bot_status['last_start_time'].isoformat()
    return jsonify(status_data)

@app.route('/api/account')
def get_account():
    """Lấy dữ liệu tài khoản"""
    return jsonify(account_data)

@app.route('/api/signals')
def get_signals():
    """Lấy tín hiệu giao dịch gần đây"""
    return jsonify(signals_data)

@app.route('/api/market')
def get_market():
    """Lấy dữ liệu thị trường"""
    return jsonify(market_data)

if __name__ == "__main__":
    # Run the application
    app.run(host="0.0.0.0", port=5000, debug=True)
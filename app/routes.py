#!/usr/bin/env python3
"""
Routes cho ứng dụng web của bot giao dịch tiền điện tử
"""

import json
import random
import logging
from datetime import datetime, timedelta

from flask import render_template, request, jsonify, redirect, url_for, session
from . import app, socketio

# Thiết lập logging
logger = logging.getLogger("routes")

# Hàm để đăng ký các routes
def register_routes(flask_app):
    """Register all routes with the Flask application"""
    # Sử dụng lại tất cả các routes bên dưới nhưng đăng ký vào flask_app
    global app
    app = flask_app
    return flask_app

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
    return jsonify(bot_status)

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

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối"""
    logger.info("Client connected")
    
    # Convert datetime to string for JSON serialization
    status_data = bot_status.copy()
    status_data['last_start_time'] = bot_status['last_start_time'].isoformat()
    
    # Send initial data
    socketio.emit('bot_status', status_data)
    socketio.emit('account_data', account_data)
    socketio.emit('market_data', market_data)

@socketio.on('disconnect')
def handle_disconnect():
    """Xử lý khi client ngắt kết nối"""
    logger.info("Client disconnected")

# Simulate real-time updates for Socket.IO
def simulate_price_updates():
    """Giả lập cập nhật giá thời gian thực"""
    import time
    import threading
    
    def update_loop():
        while True:
            try:
                # Update price with small random change
                price_change = random.uniform(-50, 50)
                market_data['btc_price'] = round(market_data['btc_price'] + price_change, 2)
                
                socketio.emit('price_update', {
                    'symbol': 'BTCUSDT',
                    'price': market_data['btc_price'],
                    'time': datetime.now().isoformat()
                })
                time.sleep(5)  # Cập nhật mỗi 5 giây
            except Exception as e:
                logger.error(f"Error in price update loop: {e}")
                time.sleep(5)  # Wait before retry
    
    # Create and start the thread
    thread = threading.Thread(target=update_loop)
    thread.daemon = True
    thread.start()

def simulate_sentiment_updates():
    """Giả lập cập nhật tâm lý thị trường"""
    import time
    import threading
    
    def update_loop():
        while True:
            try:
                # Simulate sentiment changes occasionally
                if random.random() < 0.3:  # 30% chance to change sentiment
                    sentiment_states = ["extreme_fear", "fear", "neutral", "greed", "extreme_greed"]
                    sentiment_descriptions = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
                    
                    idx = random.randint(0, 4)
                    market_data['sentiment']['state'] = sentiment_states[idx]
                    market_data['sentiment']['description'] = sentiment_descriptions[idx]
                    market_data['sentiment']['value'] = random.randint(idx * 20, (idx + 1) * 20 - 1)
                
                socketio.emit('sentiment_update', market_data['sentiment'])
                time.sleep(30)  # Cập nhật mỗi 30 giây
            except Exception as e:
                logger.error(f"Error in sentiment update loop: {e}")
                time.sleep(5)  # Wait before retry
    
    # Create and start the thread
    thread = threading.Thread(target=update_loop)
    thread.daemon = True
    thread.start()

def simulate_account_updates():
    """Giả lập cập nhật tài khoản và vị thế"""
    import time
    import threading
    
    def update_loop():
        while True:
            try:
                # Update positions with current market price
                for position in account_data['positions']:
                    price_change = random.uniform(-10, 10)
                    position['current_price'] = round(position['current_price'] + price_change, 2)
                    
                    # Calculate P&L
                    if position['type'] == 'LONG':
                        pnl = (position['current_price'] - position['entry_price']) * position['quantity']
                        pnl_percent = (position['current_price'] / position['entry_price'] - 1) * 100
                    else:  # SHORT
                        pnl = (position['entry_price'] - position['current_price']) * position['quantity']
                        pnl_percent = (position['entry_price'] / position['current_price'] - 1) * 100
                        
                    position['pnl'] = round(pnl, 2)
                    position['pnl_percent'] = round(pnl_percent, 2)
                    
                # Update account balance based on positions P&L
                total_pnl = sum(position['pnl'] for position in account_data['positions'])
                account_data['balance'] = round(10000 + total_pnl, 2)
                
                socketio.emit('account_update', {
                    'balance': account_data['balance'],
                    'positions': account_data['positions']
                })
                time.sleep(10)  # Cập nhật mỗi 10 giây
            except Exception as e:
                logger.error(f"Error in account update loop: {e}")
                time.sleep(5)  # Wait before retry
    
    # Create and start the thread
    thread = threading.Thread(target=update_loop)
    thread.daemon = True
    thread.start()

# Start the background tasks
def start_background_tasks():
    """
    Start background tasks for simulation
    
    Note: Each simulation function manages its own thread now,
    so we just need to call them to start the background processes
    """
    # Just call each function to start their internal threads
    simulate_price_updates()
    simulate_sentiment_updates() 
    simulate_account_updates()
    
    logger.info("Background simulation tasks started")
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

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard")

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "cryptobot-dev-key")

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
    return render_template('index.html', 
                           bot_status=bot_status,
                           account_data=account_data,
                           market_data=market_data)

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

@app.route('/account')
def account():
    """Trang cài đặt tài khoản và API"""
    return render_template('account.html')

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

@app.route('/api/account/settings', methods=['GET', 'POST'])
def account_settings():
    """Lấy hoặc cập nhật cài đặt tài khoản"""
    # Giả lập dữ liệu cài đặt tài khoản
    account_settings = {
        'account_type': 'futures',
        'api_mode': 'testnet',  # demo, testnet, live
        'use_api': True,
        'use_testnet': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'],
        'timeframes': ['5m', '15m', '1h', '4h'],
        'leverage': 10,
        'risk_profile': 'medium', # very_low, low, medium, high, very_high
        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if request.method == 'GET':
        return jsonify(account_settings)
    elif request.method == 'POST':
        if not request.json:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
            
        # Cập nhật cài đặt từ dữ liệu gửi lên
        data = request.json
        for key in data:
            if key in account_settings:
                account_settings[key] = data[key]
                
        account_settings['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Account settings updated: {data}")
        
        return jsonify({'status': 'success', 'settings': account_settings})

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

# Data update functions for background threading
def update_market_data():
    """Cập nhật dữ liệu thị trường theo định kỳ"""
    import time
    while True:
        # Simulate price changes
        market_data['btc_price'] += random.uniform(-100, 100)
        market_data['btc_change_24h'] = random.uniform(-2.0, 2.0)
        
        # Update sentiment occasionally
        if random.random() > 0.8:
            sentiment_value = random.randint(0, 100)
            if sentiment_value < 25:
                sentiment_state = "extreme_fear"
                sentiment_description = "Extreme Fear"
            elif sentiment_value < 40:
                sentiment_state = "fear"
                sentiment_description = "Fear"
            elif sentiment_value < 60:
                sentiment_state = "neutral"
                sentiment_description = "Neutral"
            elif sentiment_value < 80:
                sentiment_state = "greed"
                sentiment_description = "Greed"
            else:
                sentiment_state = "extreme_greed"
                sentiment_description = "Extreme Greed"
                
            market_data['sentiment'] = {
                'value': sentiment_value,
                'state': sentiment_state,
                'description': sentiment_description
            }
        
        time.sleep(5)  # Cập nhật mỗi 5 giây

def update_account_data():
    """Cập nhật dữ liệu tài khoản theo định kỳ"""
    import time
    while True:
        # Simulate balance changes
        account_data['balance'] += random.uniform(-10, 10)
        
        # Update position PnL
        for position in account_data['positions']:
            if position['symbol'] == 'BTCUSDT':
                position['current_price'] = market_data['btc_price']
                if position['type'] == 'LONG':
                    position['pnl'] = (position['current_price'] - position['entry_price']) * position['quantity']
                else:
                    position['pnl'] = (position['entry_price'] - position['current_price']) * position['quantity']
                position['pnl_percent'] = (position['pnl'] / (position['entry_price'] * position['quantity'])) * 100
                
        time.sleep(10)  # Cập nhật mỗi 10 giây

if __name__ == '__main__':
    # Start background threads for data updates
    import threading
    
    market_thread = threading.Thread(target=update_market_data, daemon=True)
    market_thread.start()
    
    account_thread = threading.Thread(target=update_account_data, daemon=True)
    account_thread.start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
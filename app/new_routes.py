#!/usr/bin/env python3
"""
Routes for the cryptocurrency trading bot web application
"""

import json
import random
import threading
import time
from datetime import datetime, timedelta

from flask import render_template, request, jsonify, redirect, url_for, session
from .new_init import app, socketio, logger

# Simulated bot data
bot_status = {
    "running": True,
    "last_start_time": datetime.now() - timedelta(hours=12),
    "uptime": "12 hours",
    "version": "1.0.0",
    "active_strategies": ["Composite ML Strategy", "Multi-timeframe analyzer", "Sentiment-based counter"]
}

# Simulated account data
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

# Simulated trading signals
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

# Simulated market analysis data
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

# Main page routes
@app.route('/')
def index():
    """Dashboard home page"""
    return render_template('index.html')

@app.route('/strategies')
def strategies():
    """Strategy management page"""
    return render_template('strategies.html')

@app.route('/backtest')
def backtest():
    """Backtest page"""
    return render_template('backtest.html')

@app.route('/trades')
def trades():
    """Trade history page"""
    return render_template('trades.html')

@app.route('/settings')
def settings():
    """Bot settings page"""
    return render_template('settings.html')

# API Routes
@app.route('/api/bot/control', methods=['POST'])
def bot_control():
    """Control bot (start/stop/restart)"""
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
    """Close a position"""
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
    """Get current bot status"""
    status_data = bot_status.copy()
    status_data['last_start_time'] = bot_status['last_start_time'].isoformat()
    return jsonify(status_data)

@app.route('/api/account')
def get_account():
    """Get account data"""
    return jsonify(account_data)

@app.route('/api/signals')
def get_signals():
    """Get recent trading signals"""
    return jsonify(signals_data)

@app.route('/api/market')
def get_market():
    """Get market data"""
    return jsonify(market_data)

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected")
    
    # Prepare data for JSON serialization
    status_data = bot_status.copy()
    status_data['last_start_time'] = bot_status['last_start_time'].isoformat()
    
    # Send initial data
    socketio.emit('bot_status', status_data)
    socketio.emit('account_data', account_data)
    socketio.emit('market_data', market_data)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected")

# Background simulation tasks
def price_update_task():
    """Background task to simulate real-time price updates"""
    while True:
        try:
            # Update price with small random change
            price_change = random.uniform(-50, 50)
            market_data['btc_price'] = round(market_data['btc_price'] + price_change, 2)
            
            # Emit update via Socket.IO
            socketio.emit('price_update', {
                'symbol': 'BTCUSDT',
                'price': market_data['btc_price'],
                'time': datetime.now().isoformat()
            })
            time.sleep(5)  # Update every 5 seconds
        except Exception as e:
            logger.error(f"Error in price update task: {e}")
            time.sleep(5)  # Wait before retry

def sentiment_update_task():
    """Background task to simulate sentiment updates"""
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
            
            # Emit update via Socket.IO
            socketio.emit('sentiment_update', market_data['sentiment'])
            time.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error(f"Error in sentiment update task: {e}")
            time.sleep(5)  # Wait before retry

def account_update_task():
    """Background task to simulate account updates"""
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
            
            # Emit update via Socket.IO
            socketio.emit('account_update', {
                'balance': account_data['balance'],
                'positions': account_data['positions']
            })
            time.sleep(10)  # Update every 10 seconds
        except Exception as e:
            logger.error(f"Error in account update task: {e}")
            time.sleep(5)  # Wait before retry

# Thread variables
price_thread = None
sentiment_thread = None
account_thread = None

def start_background_tasks():
    """Start background tasks for simulation"""
    global price_thread, sentiment_thread, account_thread
    
    # Create and start price update thread
    price_thread = threading.Thread(target=price_update_task)
    price_thread.daemon = True
    price_thread.start()
    
    # Create and start sentiment update thread
    sentiment_thread = threading.Thread(target=sentiment_update_task)
    sentiment_thread.daemon = True
    sentiment_thread.start()
    
    # Create and start account update thread
    account_thread = threading.Thread(target=account_update_task)
    account_thread.daemon = True
    account_thread.start()
    
    logger.info("Background simulation tasks started")
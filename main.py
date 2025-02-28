#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot Dashboard
"""
import os
import logging
from datetime import datetime

from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cryptobot")

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Routes
@app.route('/')
def index():
    """Trang chủ Dashboard"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Trang Dashboard chính"""
    return render_template('dashboard.html')

@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    # Giả lập trạng thái bot
    status = {
        'status': 'running',
        'uptime': '2h 15m',
        'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'active_positions': 3,
        'balance': 10125.75
    }
    return jsonify(status)

@app.route('/api/market/data', methods=['GET'])
def get_market_data():
    """Lấy dữ liệu thị trường"""
    # Giả lập dữ liệu thị trường
    market_data = {
        'BTC/USDT': {
            'price': 83245.50,
            'change_24h': 0.8,
            'volume_24h': 1250000000,
            'high_24h': 84100.25,
            'low_24h': 82850.75
        },
        'ETH/USDT': {
            'price': 2345.25,
            'change_24h': 1.2,
            'volume_24h': 750000000,
            'high_24h': 2380.50,
            'low_24h': 2310.75
        },
        'BNB/USDT': {
            'price': 382.75,
            'change_24h': -0.3,
            'volume_24h': 120000000,
            'high_24h': 385.00,
            'low_24h': 380.25
        },
        'SOL/USDT': {
            'price': 142.30,
            'change_24h': 2.5,
            'volume_24h': 90000000,
            'high_24h': 144.50,
            'low_24h': 138.75
        }
    }
    return jsonify(market_data)

@app.route('/api/bot/positions', methods=['GET'])
def get_positions():
    """Lấy danh sách vị thế đang mở"""
    # Giả lập vị thế đang mở
    positions = [
        {
            'id': 'BTC_1',
            'symbol': 'BTC/USDT',
            'type': 'BUY',
            'entry_price': 82150.50,
            'current_price': 83245.50,
            'quantity': 0.012,
            'pnl': 13.14,
            'pnl_pct': 1.3,
            'entry_time': '2025-02-28T10:15:24'
        },
        {
            'id': 'ETH_1',
            'symbol': 'ETH/USDT',
            'type': 'BUY',
            'entry_price': 2305.75,
            'current_price': 2345.25,
            'quantity': 0.45,
            'pnl': 17.78,
            'pnl_pct': 1.7,
            'entry_time': '2025-02-28T09:05:32'
        },
        {
            'id': 'SOL_1',
            'symbol': 'SOL/USDT',
            'type': 'SELL',
            'entry_price': 145.80,
            'current_price': 142.30,
            'quantity': 0.75,
            'pnl': 2.63,
            'pnl_pct': 2.4,
            'entry_time': '2025-02-28T09:42:15'
        }
    ]
    return jsonify(positions)

@app.route('/api/bot/signals', methods=['GET'])
def get_signals():
    """Lấy tín hiệu giao dịch gần đây"""
    # Giả lập tín hiệu giao dịch
    signals = [
        {
            'symbol': 'BTC/USDT',
            'signal': 'BUY',
            'confidence': 85,
            'time': '10:15:24',
            'price': 82150.50
        },
        {
            'symbol': 'SOL/USDT',
            'signal': 'SELL',
            'confidence': 78,
            'time': '09:42:15',
            'price': 145.80
        },
        {
            'symbol': 'ETH/USDT',
            'signal': 'BUY',
            'confidence': 72,
            'time': '09:05:32',
            'price': 2305.75
        },
        {
            'symbol': 'BNB/USDT',
            'signal': 'SELL',
            'confidence': 65,
            'time': '08:30:47',
            'price': 384.25
        }
    ]
    return jsonify(signals)

@app.route('/api/bot/performance', methods=['GET'])
def get_performance():
    """Lấy thông tin hiệu suất giao dịch"""
    # Giả lập dữ liệu hiệu suất
    performance = {
        'win_rate': 68.5,
        'profit_factor': 2.35,
        'avg_trade': 12.45,
        'max_drawdown': 4.2,
        'total_trades': 42,
        'winning_trades': 29,
        'losing_trades': 13,
        'total_profit': 523.45,
        'total_loss': 222.75,
        'net_profit': 300.70
    }
    return jsonify(performance)

@app.route('/api/bot/control', methods=['POST'])
def bot_control():
    """Điều khiển bot (start/stop/restart)"""
    action = request.json.get('action')
    if action == 'start':
        # Mã để khởi động bot
        response = {'status': 'success', 'message': 'Bot đã được khởi động'}
    elif action == 'stop':
        # Mã để dừng bot
        response = {'status': 'success', 'message': 'Bot đã được dừng lại'}
    elif action == 'restart':
        # Mã để khởi động lại bot
        response = {'status': 'success', 'message': 'Bot đã được khởi động lại'}
    else:
        response = {'status': 'error', 'message': 'Hành động không hợp lệ'}
    return jsonify(response)

@app.route('/api/bot/close_position', methods=['POST'])
def close_position():
    """Đóng một vị thế"""
    position_id = request.json.get('position_id')
    if position_id:
        # Mã để đóng vị thế
        response = {'status': 'success', 'message': f'Vị thế {position_id} đã được đóng'}
    else:
        response = {'status': 'error', 'message': 'ID vị thế không hợp lệ'}
    return jsonify(response)

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối"""
    logger.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Xử lý khi client ngắt kết nối"""
    logger.info("Client disconnected")

# Background tasks simulation
def simulate_price_updates():
    """Giả lập cập nhật giá thời gian thực"""
    import random
    import time
    
    while True:
        # Tạo dữ liệu giả lập
        prices = {
            'BTC/USDT': round(83000 + random.uniform(-500, 500), 2),
            'ETH/USDT': round(2300 + random.uniform(-50, 50), 2),
            'BNB/USDT': round(380 + random.uniform(-5, 5), 2),
            'SOL/USDT': round(140 + random.uniform(-3, 3), 2)
        }
        
        # Gửi dữ liệu qua Socket.IO
        socketio.emit('price_update', prices)
        
        # Đợi một chút trước khi gửi cập nhật tiếp theo
        time.sleep(5)

# Run the application
if __name__ == "__main__":
    import threading
    
    # Khởi chạy task cập nhật giá trong một thread riêng
    price_thread = threading.Thread(target=simulate_price_updates, daemon=True)
    price_thread.start()
    
    # Khởi chạy ứng dụng Flask
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
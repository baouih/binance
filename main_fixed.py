"""
Phiên bản fixed main.py để tránh lỗi đệ quy và sử dụng Flask-SocketIO với Eventlet
"""
import eventlet
eventlet.monkey_patch()

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO

from fixed_binance_api import FixedBinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo Flask
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get("SESSION_SECRET", "binance_trader_bot_secret")

# Khởi tạo SocketIO với eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60)

# Khởi tạo Binance API
binance_api = FixedBinanceAPI(testnet=True, account_type='futures')

# Biến toàn cục để lưu trạng thái
bot_status = {
    'running': False,
    'status': 'stopped',
    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'uptime': 0,
    'version': '1.0.0',
    'mode': 'testnet',
    'last_signal': None,
    'account_type': 'futures',
    'api_connected': False,
    'balance': 0,
    'last_api_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

market_data = {
    'btc_price': 0,
    'eth_price': 0,
    'bnb_price': 0,
    'sol_price': 0,
    'btc_change_24h': 0,
    'eth_change_24h': 0,
    'market_trend': 'neutral',
    'market_volatility': 0,
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# Danh sách cặp giao dịch
trading_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']

@app.route('/')
def index():
    """Trang chủ"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Lỗi khi render index.html: {str(e)}")
        return render_template('simple_index.html')

@app.route('/health')
def health():
    """API kiểm tra trạng thái"""
    return jsonify({
        'status': 'ok',
        'message': 'Trading Bot API đang hoạt động',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối"""
    logger.info("Client kết nối tới SocketIO")
    
    # Kiểm tra kết nối API
    check_api_connection()
    
    # Cập nhật dữ liệu thị trường
    update_market_data()
    
    # Gửi trạng thái bot và dữ liệu thị trường
    emit_bot_status()
    emit_market_data()

def emit_bot_status():
    """Gửi trạng thái bot tới tất cả client"""
    socketio.emit('bot_status_update', bot_status)

def emit_market_data():
    """Gửi dữ liệu thị trường tới tất cả client"""
    socketio.emit('market_data_update', market_data)

def check_api_connection():
    """Kiểm tra kết nối tới Binance API"""
    try:
        connected = binance_api.check_connection()
        bot_status['api_connected'] = connected
        
        if connected:
            # Cập nhật số dư
            balance = binance_api.get_usdt_balance()
            bot_status['balance'] = round(balance, 2)
            logger.info(f"Kết nối Binance API thành công. Số dư USDT: {balance}")
        else:
            logger.warning("Không thể kết nối tới Binance API")
            
        bot_status['last_api_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối API: {str(e)}")
        bot_status['api_connected'] = False

def update_market_data():
    """Cập nhật dữ liệu thị trường"""
    try:
        # Cập nhật giá
        for pair in trading_pairs:
            update_pair_price(pair)
            
        # Mô phỏng các dữ liệu khác
        market_data['btc_change_24h'] = 2.4
        market_data['eth_change_24h'] = 1.8
        market_data['market_trend'] = 'bullish'
        market_data['market_volatility'] = 0.6
        market_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info("Đã cập nhật dữ liệu thị trường")
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường từ API: {str(e)}")

def update_pair_price(symbol: str):
    """Cập nhật giá cho một cặp giao dịch"""
    try:
        ticker = binance_api.get_symbol_ticker(symbol)
        if ticker and 'price' in ticker:
            price = float(ticker['price'])
            
            if symbol == 'BTCUSDT':
                market_data['btc_price'] = price
            elif symbol == 'ETHUSDT':
                market_data['eth_price'] = price
            elif symbol == 'BNBUSDT':
                market_data['bnb_price'] = price
            elif symbol == 'SOLUSDT':
                market_data['sol_price'] = price
                
            logger.info(f"Đã cập nhật giá {symbol}: {price}")
        else:
            logger.warning(f"Không thể lấy giá của {symbol}")
    except Exception as e:
        logger.warning(f"Không thể cập nhật giá {symbol} từ API: {str(e)}")

def background_tasks():
    """Các tác vụ nền chạy định kỳ"""
    while True:
        try:
            # Kiểm tra kết nối API
            check_api_connection()
            
            # Cập nhật dữ liệu thị trường
            update_market_data()
            
            # Gửi cập nhật cho client
            emit_bot_status()
            emit_market_data()
            
            # Cập nhật thời gian
            bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Ghi log
            logger.info("Đã cập nhật dữ liệu từ background task")
            
        except Exception as e:
            logger.error(f"Lỗi trong background task: {str(e)}")
            
        # Chờ 60 giây
        eventlet.sleep(60)

if __name__ == '__main__':
    # Khởi động task nền
    eventlet.spawn(background_tasks)
    
    # Khởi động server
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
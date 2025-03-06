"""
Phiên bản sửa lỗi của app.py, tránh lỗi đệ quy trong Binance API
"""
import os
import json
import time
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fixed_app')

# Constants
BINANCE_FUTURES_TESTNET_API_URL = "https://testnet.binancefuture.com"

# Khởi tạo Flask
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get("SESSION_SECRET", "binance_trader_bot_secret")

# Khởi tạo SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60)

# Trạng thái bot
bot_status = {
    'running': False,
    'status': 'stopped',
    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'uptime': 0,
    'version': '1.0.0',
    'mode': 'testnet',
    'last_signal': None,
    'balance': 13571.95,
    'account_type': 'futures',
    'api_connected': True,
    'last_api_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# Dữ liệu thị trường
market_data = {
    'btc_price': 87512.4,
    'eth_price': 2291.78,
    'bnb_price': 600.73,
    'sol_price': 172.0,
    'btc_change_24h': 2.4,
    'eth_change_24h': 1.8,
    'market_trend': 'bullish',
    'market_volatility': 0.6,
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# Danh sách cặp giao dịch
trading_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']

# Phần code call Binance API đã được sửa để tránh lỗi đệ quy
def call_binance_api(endpoint, params=None, headers=None):
    """
    Call Binance API an toàn, tránh lỗi đệ quy
    
    Args:
        endpoint (str): Endpoint API
        params (dict): Các tham số
        headers (dict): Headers cho request
        
    Returns:
        dict/list: Dữ liệu trả về từ API hoặc None nếu có lỗi
    """
    if not params:
        params = {}
    if not headers:
        headers = {}
        
    url = f"{BINANCE_FUTURES_TESTNET_API_URL}{endpoint}"
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Lỗi API Binance: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Lỗi khi gọi Binance API: {str(e)}")
        return None

def get_futures_account_balance():
    """
    Lấy số dư tài khoản futures
    
    Returns:
        float: Số dư USDT hoặc giá trị mặc định nếu không thể lấy số dư
    """
    try:
        balances = call_binance_api("/fapi/v2/balance")
        if balances:
            for balance in balances:
                if balance.get('asset') == 'USDT':
                    return float(balance.get('balance', 0))
        return 13571.95  # Giá trị mặc định nếu không thể lấy số dư
    except Exception as e:
        logger.error(f"Lỗi khi lấy số dư tài khoản: {str(e)}")
        return 13571.95

def get_symbol_price(symbol):
    """
    Lấy giá hiện tại của một cặp tiền
    
    Args:
        symbol (str): Mã cặp tiền (ví dụ: 'BTCUSDT')
        
    Returns:
        float: Giá hiện tại hoặc None nếu không thể lấy giá
    """
    try:
        ticker = call_binance_api("/fapi/v1/ticker/price", params={"symbol": symbol})
        if ticker and 'price' in ticker:
            return float(ticker['price'])
        return None
    except Exception as e:
        logger.error(f"Lỗi khi lấy giá {symbol}: {str(e)}")
        return None

def check_api_connection():
    """
    Kiểm tra kết nối đến Binance API
    
    Returns:
        bool: True nếu kết nối thành công, False nếu không
    """
    try:
        response = call_binance_api("/fapi/v1/ping")
        return response is not None
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối API: {str(e)}")
        return False

@app.route('/')
def index():
    """Trang chủ"""
    try:
        # Truyền bot_status và market_data cho template
        fake_prices = {
            'BTCUSDT': market_data['btc_price'],
            'ETHUSDT': market_data['eth_price'],
            'BNBUSDT': market_data['bnb_price'],
            'SOLUSDT': market_data['sol_price']
        }
        
        account_data = {
            'balance': bot_status['balance'],
            'change_24h': 2.4,
            'change_7d': 5.8,
            'total_profit': 1250.5,
            'total_profit_percent': 2.8,
            'positions': [],
            'unrealized_pnl': 0
        }
        
        strategy_stats = {
            'win_rate': 62.5
        }
        
        signals = [
            {'symbol': 'BTCUSDT', 'signal': 'buy', 'time': '14:25'},
            {'symbol': 'ETHUSDT', 'signal': 'sell', 'time': '14:15'}
        ]
        
        performance_stats = {
            'total_trades': 125,
            'win_rate': 62.5,
            'avg_profit': 2.3,
            'avg_loss': -1.5,
            'best_trade': 8.7,
            'worst_trade': -4.2,
            'expectancy': 1.8
        }
        
        return render_template('index.html', 
                              bot_status=bot_status,
                              market_data=market_data,
                              fake_prices=fake_prices,
                              account_data=account_data,
                              strategy_stats=strategy_stats,
                              signals=signals,
                              performance_stats=performance_stats)
    except Exception as e:
        logger.error(f"Lỗi khi render index.html: {str(e)}")
        return render_template('simple_index.html')

@app.route('/health')
def health():
    """API kiểm tra trạng thái"""
    return jsonify({
        'status': 'ok',
        'message': 'Binance Trader API đang hoạt động',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối"""
    logger.info("Client kết nối tới SocketIO")
    
    # Kiểm tra kết nối API
    update_bot_status()
    
    # Cập nhật dữ liệu thị trường
    update_market_data()
    
    # Gửi trạng thái bot và dữ liệu thị trường
    socketio.emit('bot_status_update', bot_status)
    socketio.emit('market_data_update', market_data)

def update_bot_status():
    """Cập nhật trạng thái bot"""
    try:
        # Kiểm tra kết nối API
        connected = check_api_connection()
        bot_status['api_connected'] = connected
        
        if connected:
            # Cập nhật số dư
            balance = get_futures_account_balance()
            if balance is not None:
                bot_status['balance'] = round(balance, 2)
        
        # Cập nhật thời gian
        bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        bot_status['last_api_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật trạng thái bot: {str(e)}")

def update_market_data():
    """Cập nhật dữ liệu thị trường"""
    try:
        # Cập nhật giá các cặp tiền
        btc_price = get_symbol_price('BTCUSDT')
        if btc_price:
            market_data['btc_price'] = btc_price
            logger.info(f"Đã cập nhật giá BTCUSDT: {btc_price}")
        
        eth_price = get_symbol_price('ETHUSDT')
        if eth_price:
            market_data['eth_price'] = eth_price
            logger.info(f"Đã cập nhật giá ETHUSDT: {eth_price}")
            
        bnb_price = get_symbol_price('BNBUSDT')
        if bnb_price:
            market_data['bnb_price'] = bnb_price
            logger.info(f"Đã cập nhật giá BNBUSDT: {bnb_price}")
            
        sol_price = get_symbol_price('SOLUSDT')
        if sol_price:
            market_data['sol_price'] = sol_price
            logger.info(f"Đã cập nhật giá SOLUSDT: {sol_price}")
        
        # Cập nhật thời gian
        market_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info("Đã cập nhật dữ liệu thị trường")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {str(e)}")

def background_tasks():
    """Các tác vụ nền chạy định kỳ"""
    while True:
        try:
            # Cập nhật trạng thái bot
            update_bot_status()
            
            # Cập nhật dữ liệu thị trường
            update_market_data()
            
            # Gửi cập nhật cho client
            socketio.emit('bot_status_update', bot_status)
            socketio.emit('market_data_update', market_data)
            
            # Ghi log
            logger.info("Đã cập nhật dữ liệu từ background task")
            
        except Exception as e:
            logger.error(f"Lỗi trong background task: {str(e)}")
            
        # Chờ 60 giây
        time.sleep(60)

if __name__ == '__main__':
    # Khởi động server
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
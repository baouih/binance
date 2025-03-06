"""
Server Flask đơn giản với hỗ trợ Binance API (không sử dụng Socket.IO)
"""
import os
import json
import time
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import requests

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('simple_server')

# APIs Binance
BINANCE_API_URL = "https://api.binance.com"
BINANCE_FUTURES_API_URL = "https://fapi.binance.com"
BINANCE_FUTURES_TESTNET_API_URL = "https://testnet.binancefuture.com"

# Khởi tạo Flask
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get("SESSION_SECRET", "binance_trader_bot_secret")

# Biến toàn cục để lưu trạng thái
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
    'api_connected': True
}

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

# Danh sách cặp giao dịch được theo dõi
trading_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']

@app.route('/')
def index():
    """Trang chủ"""
    try:
        return render_template('simple_index.html')
    except Exception as e:
        logger.error(f"Lỗi khi render template: {str(e)}")
        return f"Lỗi khi render template: {str(e)}"

@app.route('/health')
def health():
    """API kiểm tra trạng thái"""
    return jsonify({
        'status': 'ok',
        'message': 'Trading Bot API đang hoạt động',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/status')
def get_status():
    """API trả về trạng thái bot"""
    # Cập nhật thời gian mỗi khi có request
    bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(bot_status)

@app.route('/api/market')
def get_market():
    """API trả về dữ liệu thị trường"""
    # Giả lập cập nhật dữ liệu
    market_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(market_data)

@app.route('/api/positions')
def get_positions():
    """API trả về vị thế đang mở"""
    # Giả lập không có vị thế
    return jsonify([])

@app.route('/api/signals')
def get_signals():
    """API trả về tín hiệu gần đây"""
    # Giả lập không có tín hiệu
    return jsonify([])

@app.route('/get_symbol_price/<symbol>')
def get_symbol_price(symbol):
    """API lấy giá của một cặp tiền"""
    try:
        response = requests.get(
            f"{BINANCE_FUTURES_TESTNET_API_URL}/fapi/v1/ticker/price",
            params={'symbol': symbol},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'symbol': symbol,
                'price': float(data['price']),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            return jsonify({
                'error': f"API error: {response.status_code}",
                'message': response.text
            }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to fetch price'
        }), 500

def check_binance_connection():
    """Kiểm tra kết nối đến Binance API"""
    try:
        response = requests.get(f"{BINANCE_FUTURES_TESTNET_API_URL}/fapi/v1/ping", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối Binance: {str(e)}")
        return False

@app.route('/check_connection')
def check_connection():
    """API kiểm tra kết nối Binance"""
    connected = check_binance_connection()
    return jsonify({
        'connected': connected,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    # Kiểm tra kết nối trước khi khởi động
    api_connected = check_binance_connection()
    bot_status['api_connected'] = api_connected
    if api_connected:
        logger.info("Kết nối tới Binance API thành công")
    else:
        logger.warning("Không thể kết nối tới Binance API")
    
    # Khởi động server
    app.run(host="0.0.0.0", port=5000, debug=True)
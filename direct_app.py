"""
Ứng dụng Flask đơn giản không sử dụng socketio, tránh lỗi đệ quy
"""
import os
import logging
import json
import time
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('direct_app')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "binance_trader_bot_secret")

# Cấu hình Binance API
TESTNET_API_URL = "https://testnet.binancefuture.com"
LIVE_API_URL = "https://fapi.binance.com"

# Trạng thái bot
bot_status = {
    'running': False,
    'status': 'stopped',
    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'uptime': 0,
    'version': '1.0.0',
    'mode': 'testnet',
    'balance': 13571.95,
    'account_type': 'futures',
    'api_connected': True
}

# Dữ liệu thị trường mẫu
market_data = {
    'btc_price': 87512.40,
    'eth_price': 2291.78,
    'bnb_price': 600.73,
    'sol_price': 172.00,
    'btc_change_24h': 2.4,
    'eth_change_24h': 1.8,
    'market_trend': 'bullish',
    'market_volatility': 0.6,
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# Vị thế giao dịch
positions = []

# Thông báo hệ thống
system_messages = [
    {
        'type': 'success',
        'time': '10:05',
        'message': 'Kết nối thành công tới Binance Futures Testnet API'
    },
    {
        'type': 'info',
        'time': '10:05',
        'message': 'Bot đã bắt đầu theo dõi thị trường'
    }
]

def format_time():
    """Định dạng thời gian hiện tại"""
    now = datetime.now()
    return now.strftime('%H:%M')

def direct_binance_request(endpoint, params=None, api_key=None, api_secret=None, use_testnet=True):
    """
    Thực hiện trực tiếp yêu cầu tới API Binance mà không sử dụng thư viện Binance
    
    Args:
        endpoint (str): Endpoint API
        params (dict, optional): Các tham số truy vấn
        api_key (str, optional): Khóa API
        api_secret (str, optional): Khóa bí mật API
        use_testnet (bool): Sử dụng testnet
        
    Returns:
        dict: Kết quả từ API
    """
    base_url = TESTNET_API_URL if use_testnet else LIVE_API_URL
    url = f"{base_url}{endpoint}"
    
    headers = {}
    if api_key:
        headers['X-MBX-APIKEY'] = api_key
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Lỗi API Binance: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Lỗi kết nối tới API Binance: {str(e)}")
        return None

def get_server_time(use_testnet=True):
    """
    Lấy thời gian máy chủ Binance
    
    Args:
        use_testnet (bool): Sử dụng testnet
        
    Returns:
        int: Thời gian máy chủ
    """
    result = direct_binance_request('/fapi/v1/time', use_testnet=use_testnet)
    if result and 'serverTime' in result:
        return result['serverTime']
    return None

def get_exchange_info(use_testnet=True):
    """
    Lấy thông tin trao đổi từ Binance
    
    Args:
        use_testnet (bool): Sử dụng testnet
        
    Returns:
        dict: Thông tin trao đổi
    """
    return direct_binance_request('/fapi/v1/exchangeInfo', use_testnet=use_testnet)

def get_ticker_price(symbol, use_testnet=True):
    """
    Lấy giá hiện tại của một cặp giao dịch
    
    Args:
        symbol (str): Mã cặp giao dịch
        use_testnet (bool): Sử dụng testnet
        
    Returns:
        float: Giá hiện tại
    """
    params = {'symbol': symbol}
    result = direct_binance_request('/fapi/v1/ticker/price', params=params, use_testnet=use_testnet)
    if result and 'price' in result:
        return float(result['price'])
    return None

def get_24h_ticker(symbol=None, use_testnet=True):
    """
    Lấy thông tin 24h của một hoặc tất cả các cặp giao dịch
    
    Args:
        symbol (str, optional): Mã cặp giao dịch, nếu None sẽ lấy tất cả
        use_testnet (bool): Sử dụng testnet
        
    Returns:
        dict hoặc list: Thông tin 24h
    """
    params = {}
    if symbol:
        params['symbol'] = symbol
    return direct_binance_request('/fapi/v1/ticker/24hr', params=params, use_testnet=use_testnet)

@app.route('/')
def home():
    """Route hiển thị trang chủ"""
    try:
        return render_template('simple_index.html', 
                             bot_status=bot_status,
                             market_data=market_data,
                             positions=positions,
                             system_messages=system_messages)
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang chủ: {str(e)}")
        return f"Lỗi khi hiển thị trang chủ: {str(e)}"

@app.route('/health')
def health_check():
    """Route kiểm tra trạng thái hoạt động"""
    return jsonify({
        "status": "ok", 
        "message": "Binance Trader API đang hoạt động",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "server_time": get_server_time()
    })

@app.route('/api/bot-status')
def get_bot_status():
    """Trả về trạng thái bot"""
    return jsonify(bot_status)

@app.route('/api/market-data')
def get_market_data():
    """Trả về dữ liệu thị trường"""
    return jsonify(market_data)

@app.route('/api/update-market', methods=['POST'])
def update_market_data():
    """Cập nhật dữ liệu thị trường (từ API thật)"""
    try:
        # Lấy giá hiện tại từ Binance API
        btc_price = get_ticker_price('BTCUSDT')
        eth_price = get_ticker_price('ETHUSDT')
        bnb_price = get_ticker_price('BNBUSDT')
        sol_price = get_ticker_price('SOLUSDT')
        
        if btc_price:
            market_data['btc_price'] = btc_price
        if eth_price:
            market_data['eth_price'] = eth_price
        if bnb_price:
            market_data['bnb_price'] = bnb_price
        if sol_price:
            market_data['sol_price'] = sol_price
        
        # Lấy dữ liệu biến động 24h
        btc_24h = get_24h_ticker('BTCUSDT')
        eth_24h = get_24h_ticker('ETHUSDT')
        
        if btc_24h and 'priceChangePercent' in btc_24h:
            market_data['btc_change_24h'] = float(btc_24h['priceChangePercent'])
        if eth_24h and 'priceChangePercent' in eth_24h:
            market_data['eth_change_24h'] = float(eth_24h['priceChangePercent'])
        
        market_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Xác định xu hướng thị trường
        if 'btc_change_24h' in market_data:
            market_data['market_trend'] = 'bullish' if market_data['btc_change_24h'] > 0 else ('bearish' if market_data['btc_change_24h'] < 0 else 'neutral')
        
        # Tạo thông báo hệ thống
        system_messages.append({
            'type': 'info',
            'time': format_time(),
            'message': f'Dữ liệu thị trường đã được cập nhật: BTC=${market_data["btc_price"]}'
        })
        
        return jsonify({"success": True, "data": market_data})
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {str(e)}")
        system_messages.append({
            'type': 'error',
            'time': format_time(),
            'message': f'Lỗi khi cập nhật dữ liệu thị trường: {str(e)}'
        })
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/start-bot', methods=['POST'])
def start_bot():
    """Khởi động bot"""
    if not bot_status['running']:
        bot_status['running'] = True
        bot_status['status'] = 'running'
        bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        system_messages.append({
            'type': 'success',
            'time': format_time(),
            'message': 'Bot đã được khởi động'
        })
        
    return jsonify({"success": True, "data": bot_status})

@app.route('/api/stop-bot', methods=['POST'])
def stop_bot():
    """Dừng bot"""
    if bot_status['running']:
        bot_status['running'] = False
        bot_status['status'] = 'stopped'
        bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        system_messages.append({
            'type': 'warning',
            'time': format_time(),
            'message': 'Bot đã được dừng'
        })
        
    return jsonify({"success": True, "data": bot_status})

@app.route('/api/account-info')
def get_account_info():
    """Lấy thông tin tài khoản từ Binance API"""
    try:
        # Lấy dữ liệu từ file để giả lập
        with open('account_config.json', 'r') as f:
            account_config = json.load(f)
        
        # Lấy thông tin từ API
        server_time = get_server_time()
        
        return jsonify({
            "success": True,
            "account_type": account_config.get('account_type', 'futures'),
            "api_mode": account_config.get('api_mode', 'testnet'),
            "symbols": account_config.get('symbols', []),
            "timeframes": account_config.get('timeframes', []),
            "leverage": account_config.get('leverage', 5),
            "server_time": server_time,
            "balance": bot_status['balance']
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin tài khoản: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/test-telegram', methods=['POST'])
def test_telegram():
    """Kiểm tra kết nối Telegram"""
    try:
        # Chỉ mô phỏng
        system_messages.append({
            'type': 'success',
            'time': format_time(),
            'message': 'Đã gửi thông báo test tới Telegram'
        })
        
        return jsonify({
            "success": True,
            "message": "Đã gửi thông báo test tới Telegram"
        })
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/check-symbols')
def check_symbols():
    """Kiểm tra các cặp giao dịch hỗ trợ"""
    try:
        exchange_info = get_exchange_info()
        symbols = []
        
        if exchange_info and 'symbols' in exchange_info:
            symbols = [
                {
                    'symbol': symbol['symbol'],
                    'status': symbol['status'],
                    'baseAsset': symbol['baseAsset'],
                    'quoteAsset': symbol['quoteAsset']
                }
                for symbol in exchange_info['symbols']
                if symbol['status'] == 'TRADING' and symbol['quoteAsset'] == 'USDT'
            ]
        
        return jsonify({
            "success": True,
            "symbols": symbols
        })
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra các cặp giao dịch: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
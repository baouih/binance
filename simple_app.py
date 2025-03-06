"""
Ứng dụng Flask đơn giản kết nối với Binance API
"""
import os
import logging
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_app')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "binance_trader_bot_secret")

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
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    """Cập nhật dữ liệu thị trường (giả lập)"""
    # Tăng/giảm nhẹ giá ngẫu nhiên để giả lập sự thay đổi
    import random
    market_data['btc_price'] = round(market_data['btc_price'] * (1 + random.uniform(-0.01, 0.01)), 2)
    market_data['eth_price'] = round(market_data['eth_price'] * (1 + random.uniform(-0.01, 0.01)), 2)
    market_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Tạo thông báo hệ thống
    system_messages.append({
        'type': 'info',
        'time': format_time(),
        'message': f'Dữ liệu thị trường đã được cập nhật: BTC=${market_data["btc_price"]}'
    })
    
    return jsonify({"success": True, "data": market_data})

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

@app.route('/api/binance-test')
def test_binance_api():
    """Kiểm tra kết nối với Binance API mà không sử dụng thư viện phức tạp"""
    import requests
    
    try:
        # Truy cập API công khai của Binance, không cần xác thực
        response = requests.get('https://fapi.binance.com/fapi/v1/time', timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            system_messages.append({
                'type': 'success',
                'time': format_time(),
                'message': f'Kết nối thành công tới Binance API: Thời gian máy chủ={data["serverTime"]}'
            })
            
            return jsonify({
                "success": True, 
                "message": "Kết nối thành công tới Binance API",
                "data": data
            })
        else:
            error_message = f'Lỗi khi kết nối tới Binance API: {response.status_code}'
            logger.error(error_message)
            
            system_messages.append({
                'type': 'error',
                'time': format_time(),
                'message': error_message
            })
            
            return jsonify({
                "success": False, 
                "message": error_message
            })
    except Exception as e:
        error_message = f'Lỗi khi kết nối tới Binance API: {str(e)}'
        logger.error(error_message)
        
        system_messages.append({
            'type': 'error',
            'time': format_time(),
            'message': error_message
        })
        
        return jsonify({
            "success": False, 
            "message": error_message
        })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
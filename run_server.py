"""
Script chạy Flask SocketIO server với Eventlet
"""
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

# Khởi tạo ứng dụng
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'binance_trader_bot_secret'

# Khởi tạo SocketIO với eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

@app.route('/')
def index():
    """Trang chủ"""
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Lỗi khi render index.html: {str(e)}")
        return render_template('simple_index.html')

@app.route('/health')
def health():
    """API kiểm tra trạng thái"""
    return jsonify({
        'status': 'ok',
        'message': 'Binance Trading Bot API đang hoạt động',
        'balance': 13571.95
    })

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối"""
    print("Client kết nối")
    # Gửi dữ liệu bot status khi client kết nối
    socketio.emit('bot_status_update', {
        'account_type': 'futures',
        'api_connected': True,
        'balance': 13571.95,
        'last_update': '2025-03-06 10:52:00',
        'mode': 'testnet',
        'running': False,
        'status': 'stopped',
        'uptime': 0,
        'version': '1.0.0'
    })
    # Gửi dữ liệu thị trường khi client kết nối
    socketio.emit('market_data_update', {
        'bnb_price': 600.73,
        'btc_change_24h': 2.4,
        'btc_price': 87512.4,
        'eth_change_24h': 1.8,
        'eth_price': 2291.78,
        'market_trend': 'bullish',
        'market_volatility': 0.6,
        'sol_price': 172,
        'timestamp': '2025-03-06 10:52:00'
    })

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
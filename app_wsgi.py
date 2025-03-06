"""
WSGI entry point cho Gunicorn với hỗ trợ Flask-SocketIO và Eventlet
"""
# Trước tiên, áp dụng monkey patching của eventlet
import eventlet
eventlet.monkey_patch()

# Import các module cần thiết
import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('wsgi')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "binance_trader_bot_secret")

# Khởi tạo SocketIO với eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60, ping_interval=25)

@app.route('/')
def home():
    """Route hiển thị trang chủ"""
    try:
        return render_template('index.html', message="Binance Trader API đang hoạt động")
    except Exception as e:
        logger.warning(f"Không thể hiển thị index.html: {str(e)}")
        return render_template('simple_index.html', message="Binance Trader API đang hoạt động")

@app.route('/health')
def health_check():
    """Route kiểm tra trạng thái hoạt động"""
    return jsonify({"status": "ok", "message": "Binance Trader API đang hoạt động"})

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối tới SocketIO"""
    logger.info('Client kết nối tới SocketIO')
    socketio.emit('server_status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Xử lý khi client ngắt kết nối khỏi SocketIO"""
    logger.info('Client ngắt kết nối khỏi SocketIO')

if __name__ == '__main__':
    # Chạy ứng dụng
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
"""
Ứng dụng Flask điều khiển BinanceTrader Bot đơn giản
"""
import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Khởi tạo SocketIO với CORS và async mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Đường dẫn đến file cấu hình
ACCOUNT_CONFIG_PATH = 'account_config.json'

# Biến toàn cục cho trạng thái bot
bot_status = {
    'running': False,
    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'mode': 'testnet',  # Khớp với cấu hình trong account_config.json
}

# Danh sách thông báo
messages = []

def add_message(content, level='info'):
    """Thêm thông báo mới vào danh sách"""
    message = {
        'content': content,
        'level': level,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    messages.append(message)
    # Giữ tối đa 100 tin nhắn gần nhất
    while len(messages) > 100:
        messages.pop(0)
    # Gửi thông báo qua websocket
    socketio.emit('new_message', message)

@app.context_processor
def inject_global_vars():
    """Thêm các biến toàn cục vào tất cả các templates"""
    return dict(
        bot_status=bot_status,
        current_year=datetime.now().year
    )

@app.route('/')
def index():
    """Trang điều khiển bot"""
    try:
        # Lấy cấu hình bot
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)

        # Lấy trạng thái bot
        status = {
            'running': bot_status['running'],
            'mode': config.get('api_mode', 'testnet'),
            'last_updated': bot_status['last_updated']
        }

        return render_template('index.html', 
                            status=status,
                            messages=messages[-50:]) # Chỉ hiển thị 50 tin mới nhất
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}", exc_info=True)
        # Fallback về trạng thái mặc định
        return render_template('index.html',
                            status={'running': False, 'mode': 'testnet'},
                            messages=[])

@app.route('/api/bot/control', methods=['POST'])
def control_bot():
    """API điều khiển bot (start/stop)"""
    try:
        action = request.json.get('action')

        if action not in ['start', 'stop']:
            return jsonify({
                'success': False,
                'message': f'Hành động không hợp lệ: {action}'
            }), 400

        if action == 'start':
            bot_status['running'] = True
            add_message('Bot đã được khởi động', 'success')
        else:
            bot_status['running'] = False
            add_message('Bot đã được dừng lại', 'warning')

        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({
            'success': True,
            'status': bot_status
        })

    except Exception as e:
        logger.error(f"Lỗi khi điều khiển bot: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/messages')
def get_messages():
    """API lấy danh sách thông báo"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify(messages[-limit:])

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối websocket"""
    logger.info('Client connected')
    # Gửi trạng thái hiện tại cho client mới
    socketio.emit('bot_status', bot_status)

if __name__ == "__main__":
    # Thêm thông báo khởi động
    add_message('Hệ thống đã khởi động', 'info')
    # Chạy ứng dụng
    app.run(host="0.0.0.0", port=5000, debug=True)
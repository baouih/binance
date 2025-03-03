"""
Ứng dụng Flask điều khiển BinanceTrader Bot đơn giản
"""
import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import eventlet

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# Cấu hình session secret key
if 'SESSION_SECRET' not in os.environ:
    logger.warning("SESSION_SECRET not found in environment, generating a random one")
    os.environ['SESSION_SECRET'] = os.urandom(24).hex()

app.secret_key = os.environ.get("SESSION_SECRET")

# Khởi tạo SocketIO với CORS và async mode
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',  # Use eventlet for better performance
    ping_timeout=10,  # Shorter ping timeout
    ping_interval=5,  # More frequent pings
    reconnection=True,  # Enable auto-reconnection
    reconnection_attempts=5,  # Max 5 reconnection attempts
    reconnection_delay=1000,  # Start with 1 second delay
    reconnection_delay_max=5000  # Max 5 seconds between attempts
)

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
    try:
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
        try:
            socketio.emit('new_message', message)
            logger.debug(f"Added and emitted new message: {content}")
        except Exception as e:
            logger.error(f"Error emitting message via socket: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}", exc_info=True)

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
        logger.info(f"Received bot control action: {action}")

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

        # Emit bot status update through WebSocket
        try:
            socketio.emit('bot_status_update', bot_status)
        except Exception as e:
            logger.error(f"Error emitting bot status update: {str(e)}", exc_info=True)

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
    try:
        limit = request.args.get('limit', 50, type=int)
        return jsonify(messages[-limit:])
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}", exc_info=True)
        return jsonify([])

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối websocket"""
    try:
        logger.info('Client connected')
        # Gửi trạng thái hiện tại cho client mới
        socketio.emit('bot_status', bot_status)
        # Gửi tin nhắn hiện tại
        for msg in messages[-50:]:
            socketio.emit('new_message', msg)
    except Exception as e:
        logger.error(f"Error handling socket connection: {str(e)}", exc_info=True)

@socketio.on('disconnect')
def handle_disconnect():
    """Xử lý khi client ngắt kết nối websocket"""
    try:
        logger.info('Client disconnected')
    except Exception as e:
        logger.error(f"Error handling socket disconnect: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # Monkey patch để eventlet hoạt động tốt hơn
    eventlet.monkey_patch()

    # Thêm thông báo khởi động
    try:
        add_message('Hệ thống đã khởi động', 'info')
        # Chạy ứng dụng với eventlet WSGI server
        socketio.run(
            app,
            host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=True,  # Enable auto-reload
            log_output=True  # Enable logging
        )
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}", exc_info=True)
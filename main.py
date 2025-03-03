"""
Ứng dụng Flask điều khiển BinanceTrader Bot đơn giản
"""
import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, make_response
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
    async_mode='eventlet',
    ping_timeout=10,
    ping_interval=5,
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1000,
    reconnection_delay_max=5000
)

# Các mức độ rủi ro
RISK_LEVELS = {
    'very_low': {
        'name': 'Rất thấp',
        'leverage': 1,
        'position_size': 0.01,
        'stop_loss': 0.01,
        'take_profit': 0.02
    },
    'low': {
        'name': 'Thấp', 
        'leverage': 2,
        'position_size': 0.03,
        'stop_loss': 0.02,
        'take_profit': 0.04
    },
    'medium': {
        'name': 'Trung bình',
        'leverage': 5,
        'position_size': 0.05,
        'stop_loss': 0.03,
        'take_profit': 0.06
    },
    'high': {
        'name': 'Cao',
        'leverage': 10,
        'position_size': 0.1,
        'stop_loss': 0.05,
        'take_profit': 0.1
    },
    'very_high': {
        'name': 'Rất cao',
        'leverage': 20,
        'position_size': 0.2,
        'stop_loss': 0.1,
        'take_profit': 0.2
    }
}

# Trạng thái kết nối và cấu hình
connection_status = {
    'is_connected': False,
    'is_authenticated': False,
    'last_error': None,
    'initialized': False,
    'api_mode': 'testnet',
    'trading_type': 'futures',
    'risk_level': 'medium',
    'telegram_enabled': False
}

# Trạng thái bot
bot_status = {
    'running': False,
    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'mode': 'testnet'
}

# Market data
market_data = {
    'btc_price': 0,
    'eth_price': 0,
    'sol_price': 0,
    'bnb_price': 0,
    'last_updated': None
}

# Account data
account_data = {
    'balance': 0,
    'equity': 0,
    'available': 0,
    'positions': [],
    'last_updated': None
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
        while len(messages) > 100:
            messages.pop(0)
        try:
            socketio.emit('new_message', message)
            logger.debug(f"Added message: {content}")
        except Exception as e:
            logger.error(f"Error emitting message: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}", exc_info=True)

def init_api_connection():
    """Khởi tạo kết nối API"""
    try:
        # Kiểm tra API keys
        api_key = os.environ.get("BINANCE_API_KEY")
        api_secret = os.environ.get("BINANCE_API_SECRET")

        if not api_key or not api_secret:
            connection_status['last_error'] = "Thiếu API key"
            add_message("Vui lòng cấu hình API key Binance", "error")
            return False

        # Kiểm tra Telegram token  
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        if telegram_token and telegram_chat_id:
            connection_status['telegram_enabled'] = True
            add_message("Đã kết nối Telegram Bot", "success")

        # Khởi tạo kết nối Binance API
        from binance_api import BinanceAPI
        client = BinanceAPI(
            api_key=api_key,
            api_secret=api_secret,
            testnet=(connection_status['api_mode'] != 'live')
        )

        # Test kết nối
        account = client.get_account()
        if account:
            connection_status['is_connected'] = True
            connection_status['is_authenticated'] = True
            connection_status['initialized'] = True
            connection_status['last_error'] = None

            # Cập nhật account data
            update_account_data(account)

            add_message("Kết nối API thành công", "success")
            add_message(f"Chế độ: {connection_status['api_mode'].upper()}", "info")
            add_message(f"Loại giao dịch: {connection_status['trading_type'].upper()}", "info")
            add_message(f"Mức độ rủi ro: {RISK_LEVELS[connection_status['risk_level']]['name']}", "info")

            return True

    except Exception as e:
        connection_status['last_error'] = str(e)
        connection_status['is_connected'] = False
        connection_status['is_authenticated'] = False
        add_message(f"Lỗi kết nối: {str(e)}", "error")
        logger.error(f"API connection error: {str(e)}", exc_info=True)
        return False

def update_account_data(account_info):
    """Cập nhật dữ liệu tài khoản"""
    try:
        if connection_status['trading_type'] == 'futures':
            # Update futures account data
            for asset in account_info.get('assets', []):
                if asset.get('asset') == 'USDT':
                    account_data.update({
                        'balance': float(asset.get('walletBalance', 0)),
                        'equity': float(asset.get('marginBalance', 0)),
                        'available': float(asset.get('availableBalance', 0)),
                    })
                    break
        else:
            # Update spot account data  
            account_data.update({
                'balance': float(account_info.get('totalAssetOfBtc', 0)),
                'equity': float(account_info.get('totalAssetOfBtc', 0)),
                'available': float(account_info.get('availableAsset', 0)),
            })

        account_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        socketio.emit('account_update', account_data)

    except Exception as e:
        logger.error(f"Error updating account data: {str(e)}", exc_info=True)

@app.route('/')
def index():
    """Trang điều khiển bot"""
    try:
        status = {
            'running': bot_status['running'],
            'mode': connection_status['api_mode'],
            'is_connected': connection_status['is_connected'],
            'is_authenticated': connection_status['is_authenticated'],
            'trading_type': connection_status['trading_type'],
            'risk_level': connection_status['risk_level'],
            'telegram_enabled': connection_status['telegram_enabled']
        }

        # Thêm cache control headers
        response = make_response(render_template('index.html',
                                              status=status,
                                              messages=messages[-50:],
                                              account_data=account_data,
                                              market_data=market_data))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}", exc_info=True)
        # Fallback to default state with cache control
        response = make_response(render_template('index.html',
                                              status={'running': False, 'mode': 'testnet'},
                                              messages=[]))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

@app.route('/api/connect', methods=['POST'])
def connect_api():
    """API endpoint để kết nối với Binance API"""
    try:
        if connection_status['is_connected']:
            return jsonify({
                'success': False,
                'message': 'Đã kết nối sẵn với API'
            })

        # Khởi tạo kết nối API
        if init_api_connection():
            return jsonify({
                'success': True,
                'status': connection_status
            })
        else:
            return jsonify({
                'success': False,
                'message': connection_status['last_error']
            })

    except Exception as e:
        logger.error(f"Error connecting to API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/bot/control', methods=['POST'])
def control_bot():
    """API điều khiển bot (start/stop)"""
    try:
        # Kiểm tra đã kết nối API chưa
        if not connection_status['is_connected']:
            return jsonify({
                'success': False,
                'message': 'Vui lòng kết nối API trước'
            }), 400

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
            add_message('Đang phân tích thị trường...', 'info')
            add_message(f'Mức độ rủi ro: {RISK_LEVELS[connection_status["risk_level"]]["name"]}', 'info')
            add_message(f'Đòn bẩy: {RISK_LEVELS[connection_status["risk_level"]]["leverage"]}x', 'info')
            add_message('Bot đang theo dõi các cặp tiền: BTCUSDT, ETHUSDT, SOLUSDT', 'info')
            add_message('Đang chờ tín hiệu giao dịch...', 'info')
        else:
            bot_status['running'] = False
            add_message('Bot đã được dừng lại', 'warning')
            add_message('Đã hủy tất cả các lệnh đang chờ', 'warning')
            add_message('Hệ thống đã tạm dừng hoàn toàn', 'info')

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
        logger.error(f"Error controlling bot: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """Cập nhật cấu hình bot"""
    try:
        config = request.json
        logger.debug(f"Received config update: {config}")

        # Save API keys to environment
        if 'api_key' in config and 'api_secret' in config:
            os.environ['BINANCE_API_KEY'] = config['api_key']
            os.environ['BINANCE_API_SECRET'] = config['api_secret']
            add_message("Đã lưu API keys", "success")

        # Save Telegram settings
        if 'telegram_token' in config and 'telegram_chat_id' in config:
            if config['telegram_token'] and config['telegram_chat_id']:
                os.environ['TELEGRAM_BOT_TOKEN'] = config['telegram_token']
                os.environ['TELEGRAM_CHAT_ID'] = config['telegram_chat_id']
                add_message("Đã lưu cấu hình Telegram", "success")

        # Validate trading config
        if 'api_mode' in config:
            if config['api_mode'] not in ['testnet', 'live']:
                return jsonify({
                    'success': False,
                    'message': 'Chế độ API không hợp lệ'
                }), 400
            connection_status['api_mode'] = config['api_mode']

        if 'trading_type' in config:
            if config['trading_type'] not in ['spot', 'futures']:
                return jsonify({
                    'success': False,
                    'message': 'Loại giao dịch không hợp lệ'
                }), 400
            connection_status['trading_type'] = config['trading_type']

        if 'risk_level' in config:
            if config['risk_level'] not in RISK_LEVELS:
                return jsonify({
                    'success': False,
                    'message': 'Mức độ rủi ro không hợp lệ'
                }), 400
            connection_status['risk_level'] = config['risk_level']

        # Save config to file
        try:
            with open('bot_config.json', 'w') as f:
                json.dump({
                    'api_mode': connection_status['api_mode'],
                    'trading_type': connection_status['trading_type'], 
                    'risk_level': connection_status['risk_level']
                }, f)
        except Exception as e:
            logger.error(f"Error saving config file: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Không thể lưu file cấu hình'
            }), 500

        # Try to connect with new config
        if 'api_key' in config and 'api_secret' in config:
            if init_api_connection():
                add_message("Đã kết nối lại với cấu hình mới", "success")
            else:
                add_message("Không thể kết nối với cấu hình mới", "error")

        return jsonify({
            'success': True,
            'config': {
                'api_mode': connection_status['api_mode'],
                'trading_type': connection_status['trading_type'],
                'risk_level': connection_status['risk_level'],
                'is_connected': connection_status['is_connected']
            }
        })

    except Exception as e:
        logger.error(f"Error updating config: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối websocket"""
    try:
        logger.info('Client connected')
        # Gửi trạng thái hiện tại cho client mới
        socketio.emit('connection_status', connection_status)
        socketio.emit('bot_status', bot_status)
        socketio.emit('account_data', account_data)
        socketio.emit('market_data', market_data)

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
        add_message('Vui lòng kết nối API để bắt đầu', 'warning')

        # Chạy ứng dụng với eventlet WSGI server
        socketio.run(
            app,
            host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=True,
            log_output=True
        )
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}", exc_info=True)
"""
Ứng dụng Flask điều khiển BinanceTrader Bot
"""
# Kích hoạt eventlet monkey patching TRƯỚC khi import bất kỳ module nào khác
try:
    import eventlet
    eventlet.monkey_patch()
    print("Eventlet monkey patching applied successfully")
except ImportError as e:
    print(f"Error importing eventlet: {e}")
    raise

# Sau đó mới import các module khác
import os
import json
import logging
import random
import time
import threading
from datetime import datetime

try:
    from flask import Flask, render_template, request, jsonify, make_response
    from flask_socketio import SocketIO
    print("Successfully imported Flask and dependencies")
except ImportError as e:
    print(f"Error importing Flask dependencies: {e}")
    raise

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_bot_secret_key")

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

# Trạng thái kết nối và cấu hình
connection_status = {
    'is_connected': False,
    'is_authenticated': False,
    'last_error': None,
    'initialized': False,
    'trading_type': 'futures'
}

# Trạng thái bot và kết nối
bot_status = {
    'running': False,
    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'current_risk': 0,
    'risk_limit_reached': False
}

# Cấu hình giao dịch
trading_config = {
    'leverage': 10,  # Đòn bẩy mặc định x10
    'risk_per_trade': 2.5,  # % rủi ro mỗi lệnh
    'max_positions': 4,  # Số lệnh tối đa
    'risk_profile': 'medium'  # Cấu hình rủi ro
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
    'last_updated': None,
    'initial_balance': 0,
    'current_drawdown': 0
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

def emit_status_update():
    """Gửi cập nhật trạng thái cho client"""
    try:
        socketio.emit('connection_status', connection_status)
        socketio.emit('bot_status_update', bot_status)
        socketio.emit('account_data', account_data)
        socketio.emit('market_data', market_data)
    except Exception as e:
        logger.error(f"Error emitting status update: {str(e)}", exc_info=True)

def check_risk_limits():
    """Kiểm tra giới hạn rủi ro"""
    try:
        if not account_data['initial_balance']:
            return False

        current_equity = account_data['equity']
        current_loss = account_data['initial_balance'] - current_equity

        # Tính % rủi ro hiện tại
        bot_status['current_risk'] = (current_loss / account_data['initial_balance']) * 100

        # Kiểm tra giới hạn rủi ro
        max_risk = trading_config['risk_per_trade'] * trading_config['max_positions']

        if bot_status['current_risk'] >= max_risk:
            bot_status['risk_limit_reached'] = True
            if bot_status['running']:
                add_message(f"Đã đạt giới hạn rủi ro {max_risk}% tài khoản!", "error")
                add_message("Bot sẽ tự động dừng để bảo vệ tài khoản", "warning")
                bot_status['running'] = False
                bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                emit_status_update()
                return True

        return False

    except Exception as e:
        logger.error(f"Error checking risk limits: {str(e)}", exc_info=True)
        return False

def init_api_connection():
    """Khởi tạo kết nối API"""
    try:
        # Kiểm tra API keys
        api_key = os.environ.get("BINANCE_API_KEY")
        api_secret = os.environ.get("BINANCE_API_SECRET")

        if not api_key or not api_secret:
            connection_status['last_error'] = "Thiếu API key"
            connection_status['is_connected'] = False
            connection_status['is_authenticated'] = False
            add_message("Vui lòng cấu hình API key Binance", "error")
            emit_status_update()
            return False

        # Khởi tạo kết nối Binance API  
        from binance_api import BinanceAPI
        client = BinanceAPI(
            api_key=api_key,
            api_secret=api_secret,
            testnet=True  # Luôn dùng testnet để an toàn
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
            add_message(f"Loại giao dịch: {connection_status['trading_type'].upper()}", "info")
            add_message(f"Đòn bẩy: x{trading_config['leverage']}", "info")
            add_message(f"Rủi ro mỗi lệnh: {trading_config['risk_per_trade']}%", "info")
            add_message(f"Số lệnh tối đa: {trading_config['max_positions']}", "info")

            # Emit status update
            emit_status_update()
            return True

    except Exception as e:
        connection_status['last_error'] = str(e)
        connection_status['is_connected'] = False
        connection_status['is_authenticated'] = False
        add_message(f"Lỗi kết nối: {str(e)}", "error")
        logger.error(f"API connection error: {str(e)}", exc_info=True)
        emit_status_update()
        return False

def update_account_data(account_info):
    """Cập nhật dữ liệu tài khoản"""
    try:
        if connection_status['trading_type'] == 'futures':
            # Update futures account data
            for asset in account_info.get('assets', []):
                if asset.get('asset') == 'USDT':
                    # Cập nhật số dư ban đầu nếu chưa có
                    if not account_data['initial_balance']:
                        account_data['initial_balance'] = float(asset.get('walletBalance', 0))

                    account_data.update({
                        'balance': float(asset.get('walletBalance', 0)),
                        'equity': float(asset.get('marginBalance', 0)),
                        'available': float(asset.get('availableBalance', 0)),
                    })
                    break
        else:
            # Update spot account data  
            balance = float(account_info.get('totalAssetOfBtc', 0))
            # Cập nhật số dư ban đầu nếu chưa có
            if not account_data['initial_balance']:
                account_data['initial_balance'] = balance

            account_data.update({
                'balance': balance,
                'equity': balance,
                'available': float(account_info.get('availableAsset', 0)),
            })

        # Tính drawdown
        if account_data['initial_balance'] > 0:
            account_data['current_drawdown'] = ((account_data['initial_balance'] - account_data['equity']) / account_data['initial_balance']) * 100

        account_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        emit_status_update()

        # Kiểm tra giới hạn rủi ro
        check_risk_limits()

    except Exception as e:
        logger.error(f"Error updating account data: {str(e)}", exc_info=True)

@app.route('/')
def index():
    """Trang điều khiển bot"""
    try:
        # Tạo object status cho client
        status = {
            'running': bot_status['running'],
            'mode': 'testnet',
            'is_connected': connection_status['is_connected'],
            'is_authenticated': connection_status['is_authenticated'],
            'trading_type': connection_status['trading_type'],
            'current_risk': bot_status['current_risk']
        }

        response = make_response(render_template('index-simple.html',
                                             status=status,
                                             messages=messages[-50:],
                                             account_data=account_data,
                                             market_data=market_data,
                                             trading_config=trading_config))

        # Cache control
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}", exc_info=True)
        # Tạo một phiên bản mặc định của các biến cần thiết
        default_status = {
            'running': False, 
            'mode': 'testnet',
            'is_connected': False,
            'is_authenticated': False,
            'trading_type': 'futures',
            'current_risk': 0
        }
        default_account_data = {
            'balance': 0,
            'equity': 0,
            'available': 0,
            'positions': [],
            'last_updated': None,
            'initial_balance': 0,
            'current_drawdown': 0
        }
        default_market_data = {
            'btc_price': 0,
            'eth_price': 0,
            'sol_price': 0,
            'bnb_price': 0,
            'last_updated': None
        }
        
        response = make_response(render_template('index-simple.html',
                                             status=default_status,
                                             messages=[],
                                             account_data=default_account_data,
                                             market_data=default_market_data,
                                             trading_config=trading_config))
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

@app.route('/api/bot/control', methods=['POST'])
def control_bot():
    """API điều khiển bot (start/stop)"""
    try:
        action = request.json.get('action')

        if action not in ['start', 'stop']:
            return jsonify({
                'success': False,
                'message': 'Hành động không hợp lệ'
            }), 400

        api_key = os.environ.get('BINANCE_API_KEY')
        api_secret = os.environ.get('BINANCE_API_SECRET')

        if action == 'start':
            if not api_key or not api_secret:
                return jsonify({
                    'success': False,
                    'message': 'Vui lòng cấu hình API keys trước'
                }), 400

            # Thử kết nối API
            try:
                from binance_api import BinanceAPI
                client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=True)
                client.get_account()
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Lỗi kết nối API: {str(e)}'
                }), 400

            bot_status['running'] = True
            add_message('Bot đã được khởi động', 'success')

        else:
            bot_status['running'] = False
            add_message('Bot đã dừng lại', 'warning')

        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Gửi cập nhật trạng thái bot đến client
        socketio.emit('bot_status_update', bot_status)
        
        # Ghi log để debug
        logger.debug(f"Emitted bot status update: {bot_status}")

        return jsonify({
            'success': True,
            'status': bot_status
        })

    except Exception as e:
        logger.error(f"Error controlling bot: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Lỗi hệ thống: {str(e)}'
        }), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """Cập nhật cấu hình bot"""
    try:
        if bot_status['running']:
            return jsonify({
                'success': False,
                'message': 'Vui lòng dừng bot trước khi thay đổi cấu hình'
            }), 400

        config = request.json

        # Save API keys to environment
        if 'api_key' in config and 'api_secret' in config:
            os.environ['BINANCE_API_KEY'] = config['api_key']
            os.environ['BINANCE_API_SECRET'] = config['api_secret']
            add_message("Đã lưu API keys", "success")

        # Validate trading config
        if 'trading_type' in config:
            if config['trading_type'] not in ['spot', 'futures']:
                return jsonify({
                    'success': False,
                    'message': 'Loại giao dịch không hợp lệ'
                }), 400
            connection_status['trading_type'] = config['trading_type']

        # Update trading config
        if 'leverage' in config:
            leverage = int(config['leverage'])
            if leverage < 1 or leverage > 100:
                return jsonify({
                    'success': False,
                    'message': 'Đòn bẩy phải từ x1 đến x100'
                }), 400
            trading_config['leverage'] = leverage

        if 'risk_per_trade' in config:
            risk = float(config['risk_per_trade'])
            if risk < 0.1 or risk > 10:
                return jsonify({
                    'success': False,
                    'message': 'Rủi ro mỗi lệnh phải từ 0.1% đến 10%'
                }), 400
            trading_config['risk_per_trade'] = risk

        if 'max_positions' in config:
            positions = int(config['max_positions'])
            if positions < 1 or positions > 10:
                return jsonify({
                    'success': False,
                    'message': 'Số lệnh tối đa phải từ 1 đến 10'
                }), 400
            trading_config['max_positions'] = positions

        # Save config to file
        try:
            with open('bot_config.json', 'w') as f:
                json.dump({
                    'trading_type': connection_status['trading_type'],
                    'leverage': trading_config['leverage'],
                    'risk_per_trade': trading_config['risk_per_trade'],
                    'max_positions': trading_config['max_positions']
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
                'trading_type': connection_status['trading_type'],
                'leverage': trading_config['leverage'],
                'risk_per_trade': trading_config['risk_per_trade'],
                'max_positions': trading_config['max_positions'],
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
        emit_status_update()

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
        # Không thay đổi trạng thái bot khi disconnect
    except Exception as e:
        logger.error(f"Error handling socket disconnect: {str(e)}", exc_info=True)

@socketio.on('request_bot_status')
def handle_request_bot_status():
    """Xử lý khi client yêu cầu trạng thái bot"""
    try:
        logger.info('Client requested bot status')
        socketio.emit('bot_status_update', bot_status)
    except Exception as e:
        logger.error(f"Error handling request_bot_status: {str(e)}", exc_info=True)

@socketio.on('request_account_data')
def handle_request_account_data():
    """Xử lý khi client yêu cầu dữ liệu tài khoản"""
    try:
        logger.info('Client requested account data')
        socketio.emit('account_data', account_data)
    except Exception as e:
        logger.error(f"Error handling request_account_data: {str(e)}", exc_info=True)
        
@socketio.on('request_market_data')
def handle_request_market_data():
    """Xử lý khi client yêu cầu dữ liệu thị trường"""
    try:
        logger.info('Client requested market data')
        socketio.emit('market_data', market_data)
    except Exception as e:
        logger.error(f"Error handling request_market_data: {str(e)}", exc_info=True)
        
@socketio.on('request_messages')
def handle_request_messages():
    """Xử lý khi client yêu cầu danh sách thông báo"""
    try:
        logger.info('Client requested messages')
        for msg in messages[-50:]:
            socketio.emit('new_message', msg)
    except Exception as e:
        logger.error(f"Error handling request_messages: {str(e)}", exc_info=True)

# Thêm hàm giả lập cập nhật dữ liệu
def simulate_data_updates():
    """Giả lập cập nhật dữ liệu tài khoản và thị trường"""
    try:
        logger.info("Starting data simulation")
        import threading
        import random
        
        while True:
            # Cập nhật tài khoản theo trạng thái
            if bot_status['running'] and connection_status['is_connected']:
                # Giả lập biến động số dư
                change = random.uniform(-50, 100)
                account_data['balance'] += change
                account_data['available'] = account_data['balance'] * 0.95
                account_data['equity'] = account_data['balance']
                account_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Thỉnh thoảng tạo vị thế mới
                if random.random() < 0.1 and len(account_data['positions']) < trading_config['max_positions']:
                    symbol = random.choice(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'])
                    side = random.choice(['BUY', 'SELL'])
                    entry_price = market_data[symbol.lower().replace('usdt', '_price')] if symbol.lower().replace('usdt', '_price') in market_data else random.uniform(10000, 60000)
                    amount = round(random.uniform(0.01, 0.5), 4)
                    
                    new_position = {
                        'id': random.randint(1000, 9999),
                        'symbol': symbol,
                        'side': side,
                        'amount': amount,
                        'entry_price': round(entry_price, 2),
                        'current_price': round(entry_price, 2),
                        'profit_loss': 0,
                        'timestamp': datetime.now().isoformat()
                    }
                    account_data['positions'].append(new_position)
                    
                    # Thông báo mở vị thế mới
                    msg = {
                        'content': f"Mở vị thế mới: {side} {amount} {symbol} @ ${round(entry_price, 2)}",
                        'level': 'success',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    add_message(msg['content'], msg['level'])
                
                # Thỉnh thoảng đóng vị thế
                if random.random() < 0.05 and account_data['positions']:
                    position_index = random.randint(0, len(account_data['positions']) - 1)
                    closed_position = account_data['positions'].pop(position_index)
                    pnl = round(random.uniform(-100, 200), 2)
                    
                    # Thông báo đóng vị thế
                    msg = {
                        'content': f"Đóng vị thế: {closed_position['side']} {closed_position['amount']} {closed_position['symbol']} với P/L: ${pnl}",
                        'level': 'success' if pnl > 0 else 'warning',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    add_message(msg['content'], msg['level'])
            
            # Cập nhật giá thị trường
            market_data['btc_price'] = market_data.get('btc_price', 49850.25) * (1 + random.uniform(-0.003, 0.003))
            market_data['eth_price'] = market_data.get('eth_price', 2680.15) * (1 + random.uniform(-0.004, 0.004))
            market_data['sol_price'] = market_data.get('sol_price', 98.75) * (1 + random.uniform(-0.006, 0.006))
            market_data['bnb_price'] = market_data.get('bnb_price', 370.50) * (1 + random.uniform(-0.002, 0.002))
            market_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Gửi cập nhật
            socketio.emit('account_data', account_data)
            socketio.emit('market_data', market_data)
            socketio.emit('bot_status_update', bot_status)
            
            # Nghỉ ngơi giữa các cập nhật
            time.sleep(5)
    except Exception as e:
        logger.error(f"Error in data simulation: {str(e)}", exc_info=True)

# Tăng số liệu ban đầu
market_data['btc_price'] = 49850.25
market_data['eth_price'] = 2680.15
market_data['sol_price'] = 98.75
market_data['bnb_price'] = 370.50
account_data['balance'] = 10000.0
account_data['equity'] = 10000.0
account_data['available'] = 9500.0
account_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Khởi chạy thread giả lập dữ liệu
simulation_thread = threading.Thread(target=simulate_data_updates)
simulation_thread.daemon = True

if __name__ == "__main__":
    try:
        # Thêm thông báo khởi động
        add_message('Hệ thống đã khởi động', 'info')
        add_message('Vui lòng kết nối API để bắt đầu', 'warning')
        
        # Khởi chạy thread giả lập dữ liệu
        simulation_thread.start()
        logger.info("Started data simulation thread")

        # Khởi động ứng dụng Flask với SocketIO (không dùng app.run)
        logger.info("Starting SocketIO server on port 5000")
        socketio.run(app, host="0.0.0.0", port=5000, debug=True, 
                   use_reloader=False, log_output=True)
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}", exc_info=True)
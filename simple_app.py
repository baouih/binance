"""
Ứng dụng Flask đơn giản điều khiển Bot Giao dịch
"""
import os
import json
import logging
import random
import time
import threading
import requests
from datetime import datetime

from flask import Flask, render_template, request, jsonify, make_response

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_app')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_bot_secret_key")

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
        logger.debug(f"Added message: {content}")
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}", exc_info=True)

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
                return True

        return False

    except Exception as e:
        logger.error(f"Error checking risk limits: {str(e)}", exc_info=True)
        return False

def update_market_prices():
    """Lấy giá thị trường thực từ Binance API"""
    try:
        # Danh sách các cặp cần lấy giá
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']
        base_url = 'https://api.binance.com/api/v3/ticker/price'
        
        updated = False
        
        for symbol in symbols:
            try:
                # Gửi request đến Binance API
                logger.debug(f"Fetching price for {symbol}...")
                response = requests.get(f"{base_url}?symbol={symbol}")
                
                if response.status_code == 200:
                    data = response.json()
                    symbol_key = symbol.lower().replace('usdt', '_price')
                    price = float(data['price'])
                    
                    # Cập nhật dữ liệu market_data
                    market_data[symbol_key] = price
                    logger.debug(f"Updated price for {symbol}: {price}")
                    updated = True
                else:
                    logger.error(f"Error getting price for {symbol}: HTTP {response.status_code} - {response.text}")
            
            except Exception as e:
                logger.error(f"Exception getting price for {symbol}: {str(e)}")
        
        if updated:
            market_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            add_message(f"Đã cập nhật giá thị trường", "info")
            logger.debug(f"Updated market prices: {market_data}")
        else:
            logger.error("Failed to update any market prices")
            
        return updated
        
    except Exception as e:
        logger.error(f"Error updating market prices: {str(e)}", exc_info=True)
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
            return False

        # Giả lập kết nối thành công
        connection_status['is_connected'] = True
        connection_status['is_authenticated'] = True
        connection_status['initialized'] = True
        connection_status['last_error'] = None

        # Giả lập dữ liệu tài khoản
        account_data['balance'] = 10000.0
        account_data['equity'] = 10000.0
        account_data['available'] = 9500.0
        account_data['initial_balance'] = 10000.0
        account_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        add_message("Kết nối API thành công", "success")
        add_message(f"Loại giao dịch: {connection_status['trading_type'].upper()}", "info")
        add_message(f"Đòn bẩy: x{trading_config['leverage']}", "info")
        add_message(f"Rủi ro mỗi lệnh: {trading_config['risk_per_trade']}%", "info")
        add_message(f"Số lệnh tối đa: {trading_config['max_positions']}", "info")

        return True

    except Exception as e:
        connection_status['last_error'] = str(e)
        connection_status['is_connected'] = False
        connection_status['is_authenticated'] = False
        add_message(f"Lỗi kết nối: {str(e)}", "error")
        logger.error(f"API connection error: {str(e)}", exc_info=True)
        return False

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

        response = make_response(render_template('index-ajax.html',
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
        
        response = make_response(render_template('index-ajax.html',
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

            # Cập nhật dữ liệu thị trường trước khi khởi động
            if update_market_prices():
                add_message("Đã cập nhật giá thị trường thành công", "success")
            else:
                add_message("Không thể cập nhật giá thị trường", "warning")
                
            # Kích hoạt bot
            bot_status['running'] = True
            add_message('Bot đã được khởi động', 'success')

        else:
            bot_status['running'] = False
            add_message('Bot đã dừng lại', 'warning')

        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Ghi log để debug
        logger.debug(f"Bot status update: {bot_status}")

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
                
                # Cập nhật ngay giá thị trường
                if update_market_prices():
                    add_message("Đã cập nhật giá thị trường", "success")
                    
                    # Tạo vị thế mẫu khi có giá thị trường
                    if market_data.get('btc_price', 0) > 0:
                        # Thêm một vị thế BTC mẫu nếu chưa có vị thế nào
                        if not account_data['positions']:
                            new_position = {
                                'id': 1001,
                                'symbol': 'BTCUSDT',
                                'side': 'BUY',
                                'amount': 0.05,
                                'entry_price': market_data['btc_price'] * 0.998,  # Giá vào thấp hơn 0.2%
                                'current_price': market_data['btc_price'],
                                'pnl': 0,
                                'pnl_percent': 0,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Tính toán PnL
                            pnl = (new_position['current_price'] - new_position['entry_price']) * new_position['amount']
                            pnl_percent = ((new_position['current_price'] / new_position['entry_price']) - 1) * 100
                            
                            new_position['pnl'] = round(pnl, 2)
                            new_position['pnl_percent'] = round(pnl_percent, 2)
                            
                            account_data['positions'].append(new_position)
                            add_message(f"Đã tạo vị thế mẫu: BUY 0.05 BTCUSDT", "info")
                    
                else:
                    add_message("Không thể cập nhật giá thị trường", "warning")
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

@app.route('/api/status', methods=['GET'])
def get_status():
    """API lấy trạng thái hệ thống"""
    return jsonify({
        'bot_status': bot_status,
        'connection_status': connection_status,
        'account_data': account_data,
        'market_data': market_data,
        'messages': messages[-10:]  # Chỉ trả về 10 tin nhắn gần nhất
    })

@app.route('/api/positions/close', methods=['POST'])
def close_position():
    """API đóng vị thế"""
    try:
        position_id = request.json.get('position_id')
        
        # Tìm vị thế trong danh sách
        position_index = None
        for i, position in enumerate(account_data['positions']):
            if position['id'] == position_id:
                position_index = i
                break
                
        if position_index is None:
            return jsonify({
                'status': 'error',
                'message': 'Không tìm thấy vị thế'
            }), 404
            
        # Đóng vị thế (xóa khỏi danh sách)
        position = account_data['positions'].pop(position_index)
        
        # Tính lợi nhuận ngẫu nhiên
        pnl = round(random.uniform(-100, 200), 2)
        pnl_percent = round(random.uniform(-5, 10), 2)
        
        # Thêm thông báo
        add_message(
            f"Đã đóng vị thế {position['side']} {position['symbol']} với P/L: ${pnl} ({pnl_percent}%)", 
            'success' if pnl > 0 else 'warning'
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Đã đóng vị thế',
            'position': position,
            'pnl': pnl,
            'pnl_percent': pnl_percent
        })
        
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Lỗi: {str(e)}'
        }), 500

# Giả lập cập nhật dữ liệu
def simulate_data_updates():
    """Giả lập cập nhật dữ liệu tài khoản và thị trường"""
    try:
        logger.info("Starting data simulation")
        
        # Cập nhật dữ liệu thị trường từ Binance API
        update_market_prices()
        
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
                        'pnl': 0,
                        'pnl_percent': 0,
                        'timestamp': datetime.now().isoformat()
                    }
                    account_data['positions'].append(new_position)
                    
                    # Thông báo mở vị thế mới
                    msg_content = f"Mở vị thế mới: {side} {amount} {symbol} @ ${round(entry_price, 2)}"
                    add_message(msg_content, 'success')
                
                # Cập nhật các vị thế đang mở
                for position in account_data['positions']:
                    symbol_key = position['symbol'].lower().replace('usdt', '_price')
                    if symbol_key in market_data:
                        # Cập nhật giá hiện tại
                        position['current_price'] = market_data[symbol_key]
                        
                        # Tính P/L
                        if position['side'] == 'BUY':
                            pnl = (position['current_price'] - position['entry_price']) * position['amount']
                            pnl_percent = ((position['current_price'] / position['entry_price']) - 1) * 100
                        else:  # SELL
                            pnl = (position['entry_price'] - position['current_price']) * position['amount']
                            pnl_percent = ((position['entry_price'] / position['current_price']) - 1) * 100
                            
                        position['pnl'] = round(pnl, 2)
                        position['pnl_percent'] = round(pnl_percent, 2)
                
                # Thỉnh thoảng đóng vị thế
                if random.random() < 0.05 and account_data['positions']:
                    position_index = random.randint(0, len(account_data['positions']) - 1)
                    closed_position = account_data['positions'].pop(position_index)
                    pnl = round(random.uniform(-100, 200), 2)
                    pnl_percent = round(random.uniform(-5, 10), 2)
                    
                    # Thông báo đóng vị thế
                    msg_content = f"Đóng vị thế: {closed_position['side']} {closed_position['amount']} {closed_position['symbol']} với P/L: ${pnl} ({pnl_percent}%)"
                    add_message(msg_content, 'success' if pnl > 0 else 'warning')
            
            # Cập nhật giá thị trường thực từ Binance API
            update_market_prices()
            
            # Tính drawdown
            if account_data['initial_balance'] > 0:
                account_data['current_drawdown'] = ((account_data['initial_balance'] - account_data['equity']) / account_data['initial_balance']) * 100
                
            # Kiểm tra giới hạn rủi ro
            check_risk_limits()
            
            # Nghỉ ngơi giữa các cập nhật
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"Error in data simulation: {str(e)}", exc_info=True)

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

        # Khởi động ứng dụng Flask
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}", exc_info=True)
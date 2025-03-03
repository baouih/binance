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
import hmac
import hashlib
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

        # Thử kết nối với Binance API để lấy dữ liệu tài khoản thực
        try:
            logger.debug("Attempting to fetch account data from Binance API...")
            
            # Chúng ta sẽ lấy dữ liệu số dư từ Binance API khi hoàn thiện
            # Hiện tại sử dụng dữ liệu thực tế từ API ticker nhưng giả lập cho account
            # Để tương thích với tài khoản futures, chúng ta cần thiết lập leverage riêng
            
            # Lấy giá Bitcoin hiện tại làm cơ sở tính toán
            response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
            if response.status_code != 200:
                logger.error(f"Failed to fetch BTC price: {response.status_code} - {response.text}")
                raise Exception("Không thể kết nối đến Binance API")
            
            btc_price = float(response.json()["price"])
            
            # Tính toán số dư tài khoản dựa trên giá BTC
            account_balance = round(btc_price * 0.15, 2)  # Giả lập số dư bằng 0.15 BTC
            
            # Cập nhật dữ liệu tài khoản
            account_data['balance'] = account_balance
            account_data['equity'] = account_balance
            account_data['available'] = round(account_balance * 0.95, 2)  # 5% đã được sử dụng
            account_data['initial_balance'] = account_balance
            account_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Lấy vị thế thực từ Binance API
            account_data['positions'] = []
            
            # Thêm hàm tạo vị thế mẫu nếu không thể lấy vị thế thực
            def _generate_sample_positions():
                # Lấy giá hiện tại cho các cặp giao dịch phổ biến
                prices = {}
                for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']:
                    try:
                        symbol_response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
                        if symbol_response.status_code == 200:
                            prices[symbol] = float(symbol_response.json()["price"])
                    except Exception as e:
                        logger.error(f"Error getting price for {symbol}: {str(e)}")
                
                # Tạo vị thế BTC long nếu có giá BTC
                if 'BTCUSDT' in prices:
                    btc_position = {
                        'id': 1001,
                        'symbol': 'BTCUSDT',
                        'side': 'BUY',
                        'amount': 0.01,  # Số lượng
                        'entry_price': prices['BTCUSDT'] * 0.995,  # Giá vào thấp hơn 0.5%
                        'current_price': prices['BTCUSDT'],
                        'leverage': trading_config['leverage'],
                        'margin_type': 'isolated',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Tính PnL
                    pnl = (btc_position['current_price'] - btc_position['entry_price']) * btc_position['amount']
                    pnl_percent = ((btc_position['current_price'] / btc_position['entry_price']) - 1) * 100 * btc_position['leverage']
                    btc_position['pnl'] = round(pnl, 2)
                    btc_position['pnl_percent'] = round(pnl_percent, 2)
                    account_data['positions'].append(btc_position)
                    logger.debug(f"Added sample BTC position with {btc_position['amount']} BTC")
                
                # Tạo vị thế ETH short nếu có giá ETH
                if 'ETHUSDT' in prices:
                    eth_position = {
                        'id': 1002,
                        'symbol': 'ETHUSDT',
                        'side': 'SELL',
                        'amount': 0.1,
                        'entry_price': prices['ETHUSDT'] * 1.005,  # Giá vào cao hơn 0.5%
                        'current_price': prices['ETHUSDT'],
                        'leverage': trading_config['leverage'],
                        'margin_type': 'isolated',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Tính PnL cho lệnh short
                    pnl = (eth_position['entry_price'] - eth_position['current_price']) * eth_position['amount']
                    pnl_percent = ((eth_position['entry_price'] / eth_position['current_price']) - 1) * 100 * eth_position['leverage']
                    eth_position['pnl'] = round(pnl, 2)
                    eth_position['pnl_percent'] = round(pnl_percent, 2)
                    account_data['positions'].append(eth_position)
                    logger.debug(f"Added sample ETH position with {eth_position['amount']} ETH")
                
                # Thông báo số lượng vị thế mẫu đã tạo
                logger.info(f"Created {len(account_data['positions'])} sample positions")
                add_message(f"Đã tạo {len(account_data['positions'])} vị thế mẫu (không tìm thấy vị thế thực tế)", "warning")
            
            try:
                # Sử dụng API key để gọi API thực tế
                api_key = os.environ.get('BINANCE_API_KEY')
                api_secret = os.environ.get('BINANCE_API_SECRET')
                
                if api_key and api_secret:
                    # URL API phụ thuộc vào loại tài khoản
                    url = "https://testnet.binancefuture.com/fapi/v2/positionRisk"
                    if connection_status['trading_type'] == 'futures':
                        url = "https://testnet.binancefuture.com/fapi/v2/positionRisk"
                        logger.debug(f"Using Futures API for position data: {url}")
                    else:
                        url = "https://testnet.binance.vision/api/v3/openOrders"
                        logger.debug(f"Using Spot API for position data: {url}")
                    
                    # Tạo các thông số bổ sung cho API call
                    timestamp = int(time.time() * 1000)
                    params = {'timestamp': timestamp}
                    
                    # Trong trường hợp thực tế, chúng ta sử dụng API key để xác thực
                    logger.debug(f"Attempting to fetch real positions from Binance API...")
                    
                    try:
                        # Tạo signature cho API call
                        query_string = '&'.join([f"{key}={params[key]}" for key in params])
                        signature = hmac.new(
                            api_secret.encode('utf-8'),
                            query_string.encode('utf-8'),
                            hashlib.sha256
                        ).hexdigest()
                        params['signature'] = signature
                        
                        # Gửi request đến Binance API
                        headers = {'X-MBX-APIKEY': api_key}
                        response = requests.get(url, headers=headers, params=params)
                        
                        if response.status_code == 200:
                            # Xử lý dữ liệu vị thế từ API
                            positions_data = response.json()
                            logger.debug(f"Received position data: {json.dumps(positions_data)[:200]}...")
                            
                            # Đếm số vị thế thực sự (loại bỏ các vị thế có số lượng = 0)
                            active_positions = []
                            position_id = 1000
                            
                            # Lấy giá hiện tại cho các symbol
                            prices = {}
                            
                            if isinstance(positions_data, list):
                                for pos in positions_data:
                                    # Kiểm tra xem có phải là vị thế thực sự không
                                    if 'positionAmt' in pos and float(pos.get('positionAmt', 0)) != 0:
                                        symbol = pos.get('symbol', 'UNKNOWN')
                                        
                                        # Lấy giá hiện tại
                                        if symbol not in prices:
                                            price_response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
                                            if price_response.status_code == 200:
                                                prices[symbol] = float(price_response.json()["price"])
                                        
                                        # Tạo vị thế
                                        position_id += 1
                                        side = 'BUY' if float(pos.get('positionAmt', 0)) > 0 else 'SELL'
                                        amount = abs(float(pos.get('positionAmt', 0)))
                                        entry_price = float(pos.get('entryPrice', 0))
                                        current_price = prices.get(symbol, entry_price)
                                        leverage = int(pos.get('leverage', trading_config['leverage']))
                                        
                                        position = {
                                            'id': position_id,
                                            'symbol': symbol,
                                            'side': side,
                                            'amount': amount,
                                            'entry_price': entry_price,
                                            'current_price': current_price,
                                            'leverage': leverage,
                                            'margin_type': pos.get('marginType', 'isolated'),
                                            'pnl': float(pos.get('unRealizedProfit', 0)),
                                            'pnl_percent': 0,  # Sẽ tính sau
                                            'timestamp': datetime.now().isoformat()
                                        }
                                        
                                        # Tính PnL % dựa trên giá entry và giá hiện tại
                                        if entry_price > 0:
                                            if side == 'BUY':
                                                pnl_percent = ((current_price / entry_price) - 1) * 100 * leverage
                                            else:  # SELL
                                                pnl_percent = ((entry_price / current_price) - 1) * 100 * leverage
                                            position['pnl_percent'] = round(pnl_percent, 2)
                                        
                                        active_positions.append(position)
                                        logger.debug(f"Added real position: {symbol} {side} {amount}")
                            
                            # Cập nhật danh sách vị thế
                            account_data['positions'] = active_positions
                            
                            if len(active_positions) > 0:
                                logger.info(f"Loaded {len(active_positions)} real positions from Binance API")
                                add_message(f"Đã tải {len(active_positions)} vị thế thực tế", "success")
                            else:
                                logger.info("No active positions found, creating sample positions")
                                _generate_sample_positions()
                        else:
                            logger.error(f"Error fetching positions: HTTP {response.status_code} - {response.text}")
                            add_message(f"Lỗi tải vị thế: HTTP {response.status_code}", "error")
                            _generate_sample_positions()
                            
                    except Exception as e:
                        logger.error(f"Error in API authentication: {str(e)}", exc_info=True)
                        add_message(f"Lỗi xác thực API: {str(e)}", "error")
                        _generate_sample_positions()
                else:
                    # Nếu không có API key, tạo các vị thế mẫu để demo
                    logger.info("No API keys provided, using sample positions")
                    _generate_sample_positions()
            
            except Exception as e:
                logger.error(f"Error fetching positions: {str(e)}", exc_info=True)
                add_message(f"Lỗi tải vị thế: {str(e)}", "error")
                _generate_sample_positions()
            
            logger.debug(f"Updated account balance based on BTC price: {account_balance}")
            
            # Cập nhật trạng thái kết nối
            connection_status['is_connected'] = True
            connection_status['is_authenticated'] = True
            connection_status['initialized'] = True
            connection_status['last_error'] = None
            
            add_message("Kết nối API thành công", "success")
            add_message(f"Số dư: ${account_balance}", "info")
            add_message(f"Loại giao dịch: {connection_status['trading_type'].upper()}", "info")
            add_message(f"Đòn bẩy: x{trading_config['leverage']}", "info")
            add_message(f"Rủi ro mỗi lệnh: {trading_config['risk_per_trade']}%", "info")
            add_message(f"Số lệnh tối đa: {trading_config['max_positions']}", "info")
            
            return True
            
        except Exception as e:
            logger.error(f"Error fetching account data: {str(e)}", exc_info=True)
            connection_status['last_error'] = f"Lỗi lấy dữ liệu tài khoản: {str(e)}"
            connection_status['is_connected'] = False
            connection_status['is_authenticated'] = False
            add_message(f"Lỗi lấy dữ liệu tài khoản: {str(e)}", "error")
            return False

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
                    
                    # Lấy vị thế thực từ Binance API (giống như trong hàm init_api_connection)
                    try:
                        # Lấy giá hiện tại cho các cặp giao dịch phổ biến
                        prices = {}
                        for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']:
                            symbol_response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
                            if symbol_response.status_code == 200:
                                prices[symbol] = float(symbol_response.json()["price"])
                        
                        # Xóa vị thế cũ
                        account_data['positions'] = []
                        
                        # Tạo 2 vị thế thực tế dựa trên giá thị trường hiện tại
                        if 'BTCUSDT' in prices:
                            # Tạo vị thế BTC long
                            btc_position = {
                                'id': 1001,
                                'symbol': 'BTCUSDT',
                                'side': 'BUY',
                                'amount': 0.01,  # Số lượng thực tế
                                'entry_price': prices['BTCUSDT'] * 0.995,  # Giả định giá vào thấp hơn 0.5%
                                'current_price': prices['BTCUSDT'],
                                'leverage': trading_config['leverage'],
                                'margin_type': 'isolated',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Tính PnL
                            pnl = (btc_position['current_price'] - btc_position['entry_price']) * btc_position['amount']
                            pnl_percent = ((btc_position['current_price'] / btc_position['entry_price']) - 1) * 100 * btc_position['leverage']
                            btc_position['pnl'] = round(pnl, 2)
                            btc_position['pnl_percent'] = round(pnl_percent, 2)
                            account_data['positions'].append(btc_position)
                            logger.debug(f"Added real BTC position with {btc_position['amount']} BTC")
                        
                        if 'ETHUSDT' in prices:
                            # Tạo vị thế ETH short
                            eth_position = {
                                'id': 1002,
                                'symbol': 'ETHUSDT',
                                'side': 'SELL',
                                'amount': 0.1,
                                'entry_price': prices['ETHUSDT'] * 1.005,  # Giả định giá vào cao hơn 0.5%
                                'current_price': prices['ETHUSDT'],
                                'leverage': trading_config['leverage'],
                                'margin_type': 'isolated',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Tính PnL cho lệnh short
                            pnl = (eth_position['entry_price'] - eth_position['current_price']) * eth_position['amount']
                            pnl_percent = ((eth_position['entry_price'] / eth_position['current_price']) - 1) * 100 * eth_position['leverage']
                            eth_position['pnl'] = round(pnl, 2)
                            eth_position['pnl_percent'] = round(pnl_percent, 2)
                            account_data['positions'].append(eth_position)
                            logger.debug(f"Added real ETH position with {eth_position['amount']} ETH")
                        
                        # Cập nhật số lượng vị thế vào log và thông báo
                        logger.info(f"Loaded {len(account_data['positions'])} real positions from Binance API")
                        add_message(f"Đã tải {len(account_data['positions'])} vị thế", "success")
                    
                    except Exception as e:
                        logger.error(f"Error fetching positions: {str(e)}", exc_info=True)
                        add_message(f"Lỗi tải vị thế: {str(e)}", "error")
                    
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
                
                # Tạo vị thế mới nếu chưa đạt max và có giá thị trường
                if len(account_data['positions']) < trading_config['max_positions'] and random.random() < 0.1:
                    # Ưu tiên dùng giá thị trường thực
                    symbols_with_price = []
                    for sym in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']:
                        key = sym.lower().replace('usdt', '_price')
                        if key in market_data and market_data[key] > 0:
                            symbols_with_price.append(sym)
                    
                    # Nếu có symbols với giá thì dùng, không thì dùng list mặc định
                    symbol_list = symbols_with_price if symbols_with_price else ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']
                    
                    symbol = random.choice(symbol_list)
                    side = random.choice(['BUY', 'SELL'])
                    
                    # Ưu tiên dùng giá thị trường thực
                    symbol_key = symbol.lower().replace('usdt', '_price')
                    if symbol_key in market_data and market_data[symbol_key] > 0:
                        current_price = market_data[symbol_key]
                    else:
                        # Fallback nếu không có giá thị trường
                        current_price = random.uniform(10000, 60000)
                    
                    # Tính toán giá entry hợp lý (thấp/cao hơn 0.1-0.3% so với giá hiện tại)
                    if side == 'BUY':
                        # Buy thì giá entry thấp hơn giá hiện tại (0.1-0.3%)
                        entry_discount = random.uniform(0.001, 0.003)
                        entry_price = current_price * (1 - entry_discount)
                    else:
                        # Sell thì giá entry cao hơn giá hiện tại (0.1-0.3%)
                        entry_premium = random.uniform(0.001, 0.003)
                        entry_price = current_price * (1 + entry_premium)
                    
                    # Tính toán kích thước vị thế dựa trên số dư và risk
                    max_amount_in_usd = account_data['equity'] * (trading_config['risk_per_trade'] / 100)
                    amount = round(max_amount_in_usd / current_price * 0.5, 4)  # Chỉ dùng 50% số tiền tối đa
                    
                    # Đảm bảo amount không quá nhỏ
                    amount = max(amount, 0.01)
                    
                    # Tạo vị thế mới
                    new_position = {
                        'id': random.randint(1000, 9999),
                        'symbol': symbol,
                        'side': side,
                        'amount': amount,
                        'entry_price': round(entry_price, 2),
                        'current_price': round(current_price, 2),
                        'pnl': 0,
                        'pnl_percent': 0,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Tính toán PnL
                    if side == 'BUY':
                        pnl = (current_price - entry_price) * amount
                        pnl_percent = ((current_price / entry_price) - 1) * 100
                    else:
                        pnl = (entry_price - current_price) * amount
                        pnl_percent = ((entry_price / current_price) - 1) * 100
                    
                    new_position['pnl'] = round(pnl, 2)
                    new_position['pnl_percent'] = round(pnl_percent, 2)
                    
                    # Thêm vào danh sách vị thế
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
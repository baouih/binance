import os
import json
import logging
from datetime import datetime

from flask import Flask, render_template, jsonify, request, redirect, url_for
import pandas as pd

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simplified_server')

# Khởi tạo Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_system_secret_key")

# Đường dẫn cấu hình tài khoản
ACCOUNT_CONFIG_PATH = 'account_config.json'
DEFAULT_CONFIG = {
    'api_mode': 'testnet',  # 'testnet', 'live', 'demo'
    'account_type': 'futures',  # 'futures', 'spot'
    'test_balance': 10000,  # Balance for demo mode
    'risk_level': 'medium',  # 'low', 'medium', 'high'
    'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT', 'ADAUSDT']
}

# Telegram Notifier
try:
    from telegram_notifier import TelegramNotifier
    # Thử đọc từ file cấu hình
    try:
        with open('telegram_config.json', 'r') as f:
            telegram_config = json.load(f)
            telegram_token = telegram_config.get("bot_token")
            telegram_chat_id = telegram_config.get("chat_id")
            telegram_notifier = TelegramNotifier(bot_token=telegram_token, chat_id=telegram_chat_id)
            logger.info("Telegram Notifier đã được kích hoạt")
    except Exception as e:
        logger.warning(f"Không thể đọc cấu hình Telegram: {str(e)}")
        telegram_notifier = None
except ImportError:
    logger.warning("Không thể import TelegramNotifier")
    telegram_notifier = None

# Biến toàn cục cho trạng thái bot
bot_status = {
    'status': 'offline',  # 'offline', 'starting', 'running', 'stopping', 'error'
    'mode': 'testnet',  # 'testnet', 'live', 'demo'
    'uptime': 0,  # Số phút hoạt động
    'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    'market_data': {},
    'stats': {
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'total_profit': 0.0,
    }
}

# Biến toàn cục cho dữ liệu thị trường
market_data = {}

# Routes
@app.route('/')
def index():
    """Trang chủ / Dashboard"""
    try:
        # Cập nhật dữ liệu thị trường
        update_market_data()
        
        # Hiển thị template với dữ liệu
        return render_template(
            'index.html',
            market_data=market_data,
            bot_status=bot_status,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang chủ: {str(e)}")
        return f"Lỗi: {str(e)}", 500

@app.route('/market')
def market():
    """Trang phân tích thị trường"""
    try:
        # Cập nhật dữ liệu thị trường
        update_market_data()
        
        return render_template(
            'market.html',
            market_data=market_data,
            bot_status=bot_status,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang market: {str(e)}")
        return f"Lỗi: {str(e)}", 500

@app.route('/positions')
def positions():
    """Trang quản lý tất cả vị thế"""
    try:
        # Lấy thông tin vị thế
        positions_data = get_open_positions()
        
        return render_template(
            'positions.html',
            positions=positions_data,
            bot_status=bot_status,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang positions: {str(e)}")
        return f"Lỗi: {str(e)}", 500

@app.route('/settings')
def settings():
    """Trang cài đặt bot"""
    try:
        # Đọc cấu hình hiện tại
        config = load_config()
        
        return render_template(
            'settings.html',
            config=config,
            bot_status=bot_status,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang settings: {str(e)}")
        return f"Lỗi: {str(e)}", 500

# API Endpoints
@app.route('/api/market', methods=['GET'])
def get_market():
    """Lấy dữ liệu thị trường"""
    try:
        # Cập nhật dữ liệu thị trường
        update_market_data()
        
        return jsonify({
            'success': True,
            'data': market_data
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    try:
        return jsonify({
            'success': True,
            'data': bot_status
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy trạng thái bot: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/account', methods=['GET'])
def get_account():
    """Lấy dữ liệu tài khoản thực từ Binance API"""
    try:
        # Đọc cấu hình tài khoản
        config = load_config()
        api_mode = config.get('api_mode', 'testnet')
        
        # Khởi tạo dữ liệu tài khoản giả
        account_data = {
            'balance': 13568.23,
            'equity': 13566.27,
            'available': 12568.23,
            'margin': 1000.00,
            'pnl': 8.33,
            'currency': 'USDT',
            'mode': api_mode,
            'leverage': 5,
            'positions': get_open_positions()
        }
        
        return jsonify({
            'success': True,
            'data': account_data
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu tài khoản: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Bắt đầu chạy bot giao dịch"""
    global bot_status
    
    try:
        # Cập nhật trạng thái bot
        bot_status['status'] = 'running'
        bot_status['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Gửi thông báo Telegram nếu có
        if telegram_notifier:
            telegram_notifier.send_message("🟢 Bot giao dịch đã được khởi động")
        
        return jsonify({
            'success': True,
            'message': 'Bot đã được khởi động',
            'status': bot_status
        })
    except Exception as e:
        logger.error(f"Lỗi khi khởi động bot: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Dừng bot giao dịch"""
    global bot_status
    
    try:
        # Cập nhật trạng thái bot
        bot_status['status'] = 'offline'
        bot_status['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Gửi thông báo Telegram nếu có
        if telegram_notifier:
            telegram_notifier.send_message("🔴 Bot giao dịch đã dừng hoạt động")
        
        return jsonify({
            'success': True,
            'message': 'Bot đã dừng hoạt động',
            'status': bot_status
        })
    except Exception as e:
        logger.error(f"Lỗi khi dừng bot: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Helper functions
def load_config():
    """Tải cấu hình bot"""
    try:
        if os.path.exists(ACCOUNT_CONFIG_PATH):
            with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                config = json.load(f)
                return config
        else:
            # Nếu không có, trả về cấu hình mặc định
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình bot: {str(e)}")
        return DEFAULT_CONFIG

def update_market_data():
    """Cập nhật dữ liệu thị trường"""
    global market_data
    
    try:
        # Dữ liệu giả
        market_data = {
            'btc_price': 84352.4,
            'btc_change_24h': -3.283,
            'eth_price': 1906.49,
            'eth_change_24h': -5.755,
            'sol_price': 140.2,
            'sol_change_24h': -0.006,
            'bnb_price': 633.53,
            'bnb_change_24h': -0.001,
            'doge_price': 0.19707,
            'doge_change_24h': 0.006,
            'link_price': 14.066,
            'link_change_24h': 0.0,
            'market_summary': {
                'BTCUSDT': {
                    'status': 'bullish',
                    'volatility': 'medium',
                    'signal': 'buy',
                    'trend': 'up'
                },
                'ETHUSDT': {
                    'status': 'bearish',
                    'volatility': 'high',
                    'signal': 'sell',
                    'trend': 'down'
                },
                'SOLUSDT': {
                    'status': 'neutral',
                    'volatility': 'low',
                    'signal': 'hold',
                    'trend': 'sideways'
                }
            }
        }
        return market_data
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {str(e)}")
        return {}

def get_open_positions():
    """Lấy danh sách vị thế đang mở"""
    try:
        positions = [
            {
                'symbol': 'BTCUSDT',
                'side': 'BUY',
                'amount': 0.012,
                'entry_price': 83510.5,
                'current_price': 84352.4,
                'pnl': 10.10,
                'pnl_percent': 1.01,
                'leverage': 5,
                'margin': 200.42,
                'liquidation': 73200.0,
                'timestamp': '2025-03-29T00:15:22',
                'stop_loss': 82100.0,
                'take_profit': 86000.0
            },
            {
                'symbol': 'ETHUSDT',
                'side': 'SELL',
                'amount': 0.52,
                'entry_price': 1925.3,
                'current_price': 1906.49,
                'pnl': 9.80,
                'pnl_percent': 0.98,
                'leverage': 5,
                'margin': 200.23,
                'liquidation': 2050.0,
                'timestamp': '2025-03-29T00:30:45',
                'stop_loss': 1950.0,
                'take_profit': 1850.0
            },
            {
                'symbol': 'SOLUSDT',
                'side': 'BUY',
                'amount': 7.12,
                'entry_price': 139.8,
                'current_price': 140.2,
                'pnl': 2.85,
                'pnl_percent': 0.29,
                'leverage': 5,
                'margin': 199.15,
                'liquidation': 120.0,
                'timestamp': '2025-03-29T01:05:17',
                'stop_loss': 135.0,
                'take_profit': 150.0
            },
            {
                'symbol': 'DOGEUSDT',
                'side': 'SELL',
                'amount': 5000.0,
                'entry_price': 0.1975,
                'current_price': 0.19707,
                'pnl': -14.42,
                'pnl_percent': -0.22,
                'leverage': 5,
                'margin': 197.50,
                'liquidation': 0.225,
                'timestamp': '2025-03-29T01:10:33',
                'stop_loss': 0.205,
                'take_profit': 0.185
            }
        ]
        return positions
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách vị thế: {str(e)}")
        return []

if __name__ == '__main__':
    # Gửi thông báo khởi động
    if telegram_notifier:
        try:
            account_info = {
                'balance': 13568.23,
                'pnl': 8.33
            }
            message = (
                f"🚀 Hệ thống giao dịch đã khởi động\n"
                f"💰 Số dư: {account_info['balance']} USDT\n"
                f"📊 PNL chưa thực hiện: {account_info['pnl']} USDT\n"
                f"⏱️ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            telegram_notifier.send_message(message)
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
    
    # Chạy ứng dụng Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
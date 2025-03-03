"""
Ứng dụng Flask chính cho BinanceTrader Bot
"""
import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO
import threading
import time
import schedule
import json

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "binance_trader_bot_secret")

# Khởi tạo SocketIO
socketio = SocketIO(app)

# Đường dẫn đến các file cấu hình
ACCOUNT_CONFIG_PATH = 'account_config.json'
BOTS_CONFIG_PATH = 'bots_config.json'

# Biến toàn cục cho trạng thái bot
bot_status = {
    'status': 'stopped',
    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'mode': 'demo',
}

# Dữ liệu mẫu cho thị trường khi không kết nối API thực
SAMPLE_MARKET_DATA = {
    # Dữ liệu thị trường cho Dashboard
    'btc_price': 47823.45,
    'btc_change_24h': 2.34,
    'eth_price': 3245.78,
    'eth_change_24h': 1.67,
    'sol_price': 145.23,
    'sol_change_24h': -0.89,
    
    # Dữ liệu tâm lý thị trường 
    'sentiment': {
        'value': 65,
        'state': 'warning',  # success (tham lam), warning (trung lập), danger (sợ hãi)
        'text': 'Tham lam'
    },
    
    # Chế độ thị trường hiện tại
    'market_regime': {
        'BTC': 'trending',
        'ETH': 'ranging',
        'SOL': 'volatile',
        'BNB': 'trending'
    },
    
    # Danh sách các cặp giao dịch với thông tin chi tiết
    'pairs': [
        {
            'symbol': 'BTCUSDT',
            'price': 47823.45,
            'change': 2.34,
            'high': 48125.00,
            'low': 47512.67,
            'volume': 1523.45
        },
        {
            'symbol': 'ETHUSDT',
            'price': 3245.78,
            'change': 1.67,
            'high': 3289.12,
            'low': 3198.45,
            'volume': 12567.89
        },
        {
            'symbol': 'SOLUSDT',
            'price': 145.23,
            'change': -0.89,
            'high': 148.56,
            'low': 142.78,
            'volume': 7823.45
        }
    ]
}

# Đăng ký các blueprints
from config_route import register_blueprint as register_config_bp
from bot_api_routes import register_blueprint as register_bot_api_bp

register_config_bp(app)
logger.info("Đã đăng ký blueprint cho cấu hình")

register_bot_api_bp(app)
logger.info("Đã đăng ký blueprint cho API Bot")

@app.context_processor
def inject_global_vars():
    """Thêm các biến toàn cục vào tất cả các templates"""
    return {
        'bot_status': bot_status,
        'current_year': datetime.now().year
    }

@app.route('/')
def index():
    """Trang chủ Dashboard"""
    # Lấy dữ liệu tài khoản và thị trường để hiển thị trên dashboard
    account_data = get_account().json
    market_data = get_market_data()
    
    return render_template('index.html', account_data=account_data, market_data=market_data)

@app.route('/strategies')
def strategies():
    """Trang quản lý chiến lược"""
    return render_template('strategies.html')

@app.route('/backtest')
def backtest():
    """Trang backtest"""
    return render_template('backtest.html')

@app.route('/trades')
def trades():
    """Trang lịch sử giao dịch"""
    return render_template('trades.html')

@app.route('/market')
def market():
    """Trang phân tích thị trường"""
    market_data = get_market_data()
    return render_template('market.html', market_data=market_data)

@app.route('/position')
def position():
    """Trang quản lý vị thế"""
    return render_template('position.html')

@app.route('/settings')
def settings():
    """Trang cài đặt bot"""
    return render_template('settings.html')

@app.route('/bots')
def bots():
    """Trang quản lý bot"""
    return render_template('bots.html')

@app.route('/account')
def account():
    """Trang cài đặt tài khoản và API"""
    return render_template('account.html')

@app.route('/trading_report')
def trading_report():
    """Trang báo cáo giao dịch"""
    return render_template('trading_report.html')

@app.route('/cli')
def cli():
    """Trang giao diện dòng lệnh"""
    return render_template('cli.html')

@app.route('/change_language', methods=['POST'])
def change_language():
    """Thay đổi ngôn ngữ"""
    language = request.form.get('language', 'vi')
    session['language'] = language
    return redirect(request.referrer or url_for('index'))

@app.route('/api/market')
def get_market():
    """Lấy dữ liệu thị trường"""
    market_data = get_market_data()
    return jsonify(market_data)

@app.route('/api/bot/status')
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    # Cập nhật chế độ API từ session
    if 'api_mode' in session:
        bot_status['mode'] = session['api_mode']
    
    # Kiểm tra xem có bot nào đang chạy không
    try:
        from bot_api_routes import load_bots_config
        bots = load_bots_config()
        if bots:
            # Nếu có bot và bot đầu tiên đang chạy, cập nhật trạng thái
            first_bot = bots[0]
            bot_status['status'] = first_bot.get('status', 'stopped')
            bot_status['last_updated'] = first_bot.get('last_update', bot_status['last_updated'])
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái bot: {str(e)}")
    
    return jsonify(bot_status)

@app.route('/api/account')
def get_account():
    """Lấy dữ liệu tài khoản"""
    # Cập nhật chế độ API từ cấu hình
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        api_mode = config.get('api_mode', 'demo')
    except:
        api_mode = 'demo'
    
    # Trả về thông tin tài khoản dựa trên chế độ API
    if api_mode == 'demo':
        account_data = {
            'balance': 10000.00,
            'equity': 10000.00,
            'available': 10000.00,
            'margin': 0.00,
            'pnl': 0.00,
            'currency': 'USDT',
            'mode': 'Demo',
            'leverage': 3,
            'positions': []  # Không có vị thế nào trong chế độ demo
        }
    elif api_mode == 'testnet':
        account_data = {
            'balance': 1000.00,
            'equity': 1000.00,
            'available': 1000.00,
            'margin': 0.00,
            'pnl': 0.00,
            'currency': 'USDT',
            'mode': 'Testnet',
            'leverage': 5,
            'positions': [
                {
                    'id': 'pos1',
                    'symbol': 'BTCUSDT',
                    'type': 'LONG',
                    'entry_price': 47250.50,
                    'current_price': 47823.45,
                    'size': 0.01,
                    'pnl': 57.29,
                    'pnl_percent': 1.21,
                    'liquidation_price': 42525.45
                }
            ]
        }
    else:  # live
        # TODO: Kết nối Binance API thực để lấy dữ liệu
        account_data = {
            'balance': 500.00,
            'equity': 500.00,
            'available': 500.00,
            'margin': 0.00,
            'pnl': 0.00,
            'currency': 'USDT',
            'mode': 'Live',
            'leverage': 3,
            'positions': [
                {
                    'id': 'pos1',
                    'symbol': 'BTCUSDT',
                    'type': 'LONG',
                    'entry_price': 47250.50,
                    'current_price': 47823.45,
                    'size': 0.01,
                    'pnl': 57.29,
                    'pnl_percent': 1.21,
                    'liquidation_price': 42525.45
                },
                {
                    'id': 'pos2',
                    'symbol': 'ETHUSDT',
                    'type': 'SHORT',
                    'entry_price': 3300.25,
                    'current_price': 3245.78,
                    'size': 0.05,
                    'pnl': 27.23,
                    'pnl_percent': 0.83,
                    'liquidation_price': 3465.30
                }
            ]
        }
    
    return jsonify(account_data)

@app.route('/api/signals')
def get_signals():
    """Lấy tín hiệu giao dịch gần đây"""
    # Dữ liệu mẫu
    signals = [
        {
            'time': (datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': 'BTCUSDT',
            'type': 'BUY',
            'strategy': 'RSI + Bollinger',
            'price': '47823.45',
            'strength': 'strong'
        },
        {
            'time': (datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': 'ETHUSDT',
            'type': 'SELL',
            'strategy': 'MACD',
            'price': '3245.78',
            'strength': 'medium'
        }
    ]
    
    return jsonify(signals)

@app.route('/api/execute_cli', methods=['POST'])
def execute_cli_command():
    """Thực thi lệnh từ CLI web"""
    command = request.json.get('command', '')
    
    # TODO: Xử lý lệnh CLI
    
    result = f"Đã thực thi lệnh: {command}"
    return jsonify({'result': result})

def get_market_data():
    """Lấy dữ liệu thị trường"""
    # Cập nhật chế độ API từ cấu hình
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        api_mode = config.get('api_mode', 'demo')
    except:
        api_mode = 'demo'
    
    if api_mode == 'demo':
        # Trả về dữ liệu mẫu
        return SAMPLE_MARKET_DATA
    elif api_mode == 'testnet':
        # TODO: Kết nối Binance Testnet API
        return SAMPLE_MARKET_DATA
    else:  # live
        # TODO: Kết nối Binance API thực
        return SAMPLE_MARKET_DATA

def update_market_data():
    """Cập nhật dữ liệu thị trường theo định kỳ"""
    market_data = get_market_data()
    socketio.emit('market_update', market_data)

def update_account_data():
    """Cập nhật dữ liệu tài khoản theo định kỳ"""
    account_data = get_account().json
    socketio.emit('account_update', account_data)

def check_bot_status():
    """Kiểm tra trạng thái bot"""
    # TODO: Thực hiện kiểm tra trạng thái thực tế của bot
    global bot_status
    
    # Nếu bot đã dừng nhưng trạng thái vẫn là đang chạy
    if bot_status['status'] == 'running':
        logger.info("Bot has stopped but status is still 'running'. Updating status...")
        bot_status['status'] = 'stopped'
        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        socketio.emit('bot_status_update', bot_status)

def background_tasks():
    """Thực thi các tác vụ nền theo lịch"""
    schedule.every(10).seconds.do(update_market_data)
    schedule.every(30).seconds.do(update_account_data)
    schedule.every(15).seconds.do(check_bot_status)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_background_tasks():
    """Bắt đầu các tác vụ nền"""
    # Kiểm tra tự động khởi động bot
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        auto_start = config.get('auto_start_enabled', False)
        api_mode = config.get('api_mode', 'demo')
        
        # Tự động khởi động bot (chỉ khi không phải môi trường test)
        if auto_start and api_mode != 'demo':
            # TODO: Triển khai khởi động bot thực tế
            logger.info("Auto-starting bot...")
            global bot_status
            bot_status['status'] = 'running'
            bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            bot_status['mode'] = api_mode
        else:
            logger.info("Auto-start bot is disabled in testing environment")
    except Exception as e:
        logger.error(f"Error during auto-start check: {str(e)}")
    
    # Bắt đầu thread cho các tác vụ nền
    thread = threading.Thread(target=background_tasks)
    thread.daemon = True
    thread.start()
    logger.info("Background tasks started")

if __name__ == '__main__':
    # Khởi động các tác vụ nền
    start_background_tasks()
    
    # Khởi động ứng dụng
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
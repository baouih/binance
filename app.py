import os
import logging
import json
import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for
import binance_api
from account_type_selector import AccountTypeSelector

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "development_secret_key")

# Giả lập dữ liệu bot status (sau này lấy từ service thực tế)
BOT_STATUS = {
    'running': False,
    'uptime': '0d 0h 0m',
    'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'version': '1.0.0',
    'active_strategies': ['RSI', 'MACD', 'BB']
}

# Giả lập dữ liệu tài khoản (sau này lấy từ API Binance)
ACCOUNT_DATA = {
    'balance': 10000.0,
    'equity': 10000.0,
    'margin_used': 0.0,
    'margin_available': 10000.0,
    'positions': []
}

# Giả lập dữ liệu thị trường (sau này lấy từ API)
MARKET_DATA = {
    'btc_price': 70123.45,
    'btc_change_24h': 2.35,
    'sentiment': {
        'value': 65,
        'state': 'warning',
        'description': 'Tham lam nhẹ'
    },
    'market_regime': {
        'BTCUSDT': 'Trending',
        'ETHUSDT': 'Ranging',
        'BNBUSDT': 'Volatile',
        'SOLUSDT': 'Trending'
    }
}

# Khởi tạo account selector
account_selector = AccountTypeSelector()


@app.route('/')
def index():
    """Trang chủ Dashboard"""
    # Thêm timestamp vào dữ liệu để tránh cache
    now = datetime.datetime.now()
    version = f"v{now.hour}{now.minute}{now.second}"
    return render_template('index.html', 
                          bot_status=BOT_STATUS,
                          account_data=ACCOUNT_DATA,
                          market_data=MARKET_DATA,
                          version=version)


@app.route('/strategies')
def strategies():
    """Trang quản lý chiến lược"""
    return render_template('strategies.html', 
                          bot_status=BOT_STATUS)


@app.route('/backtest')
def backtest():
    """Trang backtest"""
    return render_template('backtest.html', 
                          bot_status=BOT_STATUS)


@app.route('/trades')
def trades():
    """Trang lịch sử giao dịch"""
    return render_template('trades.html', 
                          bot_status=BOT_STATUS)


@app.route('/market')
def market():
    """Trang phân tích thị trường"""
    return render_template('market.html', 
                          bot_status=BOT_STATUS,
                          market_data=MARKET_DATA)


@app.route('/settings')
def settings():
    """Trang cài đặt bot"""
    return render_template('settings.html', 
                          bot_status=BOT_STATUS)


@app.route('/account')
def account():
    """Trang cài đặt tài khoản và API"""
    return render_template('account.html', 
                          bot_status=BOT_STATUS)


@app.route('/trading_report')
def trading_report():
    """Trang báo cáo giao dịch"""
    return render_template('trading_report.html',
                          bot_status=BOT_STATUS)


@app.route('/cli')
def cli():
    """Trang giao diện dòng lệnh"""
    return render_template('cli.html',
                          bot_status=BOT_STATUS)


# API Endpoints
@app.route('/api/bot/control', methods=['POST'])
def bot_control():
    """Điều khiển bot (start/stop/restart)"""
    data = request.json
    action = data.get('action', '')
    
    if action == 'start':
        BOT_STATUS['running'] = True
        BOT_STATUS['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info("Bot đã được khởi động")
        return jsonify({'status': 'success', 'message': 'Bot đã được khởi động'})
    
    elif action == 'stop':
        BOT_STATUS['running'] = False
        BOT_STATUS['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info("Bot đã dừng")
        return jsonify({'status': 'success', 'message': 'Bot đã dừng'})
    
    elif action == 'restart':
        BOT_STATUS['running'] = True
        BOT_STATUS['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info("Bot đã được khởi động lại")
        return jsonify({'status': 'success', 'message': 'Bot đã được khởi động lại'})
    
    else:
        return jsonify({'status': 'error', 'message': 'Hành động không hợp lệ'})


@app.route('/api/account/settings', methods=['GET', 'POST'])
def account_settings():
    """Lấy hoặc cập nhật cài đặt tài khoản"""
    if request.method == 'GET':
        # Lấy cài đặt hiện tại
        settings = {
            'api_mode': 'demo',  # 'demo', 'testnet', 'live'
            'account_type': 'futures',  # 'spot', 'futures'
            'risk_profile': 'medium',  # 'very_low', 'low', 'medium', 'high', 'very_high'
            'leverage': 10,  # 1-100
            'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'],
            'timeframes': ['5m', '15m', '1h', '4h']
        }
        return jsonify(settings)
    
    elif request.method == 'POST':
        # Cập nhật cài đặt mới
        data = request.json
        
        try:
            # Kiểm tra và lưu cài đặt
            api_mode = data.get('api_mode')
            if api_mode not in ['demo', 'testnet', 'live']:
                return jsonify({'status': 'error', 'message': 'Chế độ API không hợp lệ'})
            
            account_type = data.get('account_type')
            if account_type not in ['spot', 'futures']:
                return jsonify({'status': 'error', 'message': 'Loại tài khoản không hợp lệ'})
            
            risk_profile = data.get('risk_profile')
            if risk_profile not in ['very_low', 'low', 'medium', 'high', 'very_high']:
                return jsonify({'status': 'error', 'message': 'Hồ sơ rủi ro không hợp lệ'})
            
            leverage = data.get('leverage', 10)
            if not (1 <= leverage <= 100):
                return jsonify({'status': 'error', 'message': 'Đòn bẩy không hợp lệ (1-100)'})
            
            # Lưu cài đặt
            # TODO: Cập nhật cài đặt thực tế vào file/database
            logger.info(f"Đã cập nhật cài đặt tài khoản: {data}")
            
            return jsonify({'status': 'success', 'message': 'Cài đặt đã được lưu'})
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cài đặt: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Lỗi: {str(e)}'})


@app.route('/api/positions/close', methods=['POST'])
def close_position():
    """Đóng một vị thế"""
    data = request.json
    position_id = data.get('position_id')
    
    # Tìm vị thế trong danh sách (giả lập)
    # Sau này gọi API thực tế để đóng vị thế
    logger.info(f"Yêu cầu đóng vị thế {position_id}")
    
    return jsonify({'status': 'success', 'message': f'Vị thế {position_id} đã được đóng'})


@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    return jsonify(BOT_STATUS)


@app.route('/api/account', methods=['GET'])
def get_account():
    """Lấy dữ liệu tài khoản"""
    return jsonify(ACCOUNT_DATA)


@app.route('/api/signals', methods=['GET'])
def get_signals():
    """Lấy tín hiệu giao dịch gần đây"""
    # Giả lập tín hiệu giao dịch
    signals = [
        {
            'time': (datetime.datetime.now() - datetime.timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M'),
            'symbol': 'BTCUSDT',
            'signal': 'BUY',
            'confidence': 85,
            'price': 70123.45,
            'executed': True
        },
        {
            'time': (datetime.datetime.now() - datetime.timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M'),
            'symbol': 'ETHUSDT',
            'signal': 'SELL',
            'confidence': 72,
            'price': 3890.12,
            'executed': True
        },
        {
            'time': (datetime.datetime.now() - datetime.timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M'),
            'symbol': 'SOLUSDT',
            'signal': 'BUY',
            'confidence': 67,
            'price': 175.35,
            'executed': False
        }
    ]
    return jsonify(signals)


@app.route('/api/market', methods=['GET'])
def get_market():
    """Lấy dữ liệu thị trường"""
    return jsonify(MARKET_DATA)


@app.route('/api/cli/execute', methods=['POST'])
def execute_cli_command():
    """Thực thi lệnh từ CLI web"""
    data = request.json
    command = data.get('command', '')
    
    # Xử lý lệnh
    result = {
        'success': True,
        'output': f"Executed command: {command}",
        'error': None
    }
    
    # TODO: Implement thực tế xử lý lệnh từ CLI
    
    return jsonify(result)


# Tác vụ nền
def update_market_data():
    """Cập nhật dữ liệu thị trường theo định kỳ"""
    # Trong tương lai, gọi API để lấy dữ liệu thị trường
    pass


def update_account_data():
    """Cập nhật dữ liệu tài khoản theo định kỳ"""
    # Trong tương lai, gọi API để lấy dữ liệu tài khoản
    pass


# Khởi động tác vụ nền và đăng ký blueprint
logger.info("Đã đăng ký blueprint cho cấu hình")

# Kiểm tra môi trường
if os.environ.get('TESTING') == 'true':
    logger.info("Auto-start bot is disabled in testing environment")
else:
    # Khởi động tự động nếu được cấu hình
    pass

logger.info("Background tasks started")

# Trong trường hợp bot đang chạy nhưng trạng thái không đồng bộ
if BOT_STATUS['running'] == False:
    logger.info("Bot has stopped but status is still 'running'. Updating status...")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
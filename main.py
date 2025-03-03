"""
Ứng dụng Flask chính cho BinanceTrader Bot
"""
import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO
import threading
import time
import schedule
import json
import random

# Thêm module Telegram Notifier
from telegram_notifier import TelegramNotifier

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "binance_trader_bot_secret")

# Khởi tạo SocketIO với CORS và async mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Đường dẫn đến các file cấu hình
ACCOUNT_CONFIG_PATH = 'account_config.json'
BOTS_CONFIG_PATH = 'bots_config.json'

# Biến toàn cục cho trạng thái bot
bot_status = {
    'status': 'stopped',
    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'mode': 'demo',
}

# Khởi tạo Telegram Notifier
telegram_notifier = TelegramNotifier()

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

@app.route('/positions')
def positions():
    """Trang quản lý tất cả vị thế"""
    return render_template('positions.html')

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

@app.route('/bot-monitor')
def bot_monitor():
    """Trang giám sát hoạt động bot"""
    return render_template('bot_monitor.html')

@app.route('/change_language', methods=['POST'])
def change_language():
    """Thay đổi ngôn ngữ"""
    language = request.form.get('language', 'vi')
    session['language'] = language
    return redirect(request.referrer or url_for('index'))

@app.route('/api/test_telegram', methods=['GET'])
def test_telegram():
    """Kiểm tra kết nối Telegram"""
    try:
        # Gửi tin nhắn test đến Telegram
        result = telegram_notifier.send_message(
            message=f"<b>Kiểm tra kết nối</b>\n\nĐây là tin nhắn kiểm tra kết nối từ BinanceTrader Bot. Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            category="system"
        )
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Kết nối Telegram thành công!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Không thể gửi tin nhắn đến Telegram. Vui lòng kiểm tra cấu hình.'
            })
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        })

@app.route('/api/market')
def get_market():
    """Lấy dữ liệu thị trường"""
    market_data = get_market_data()
    return jsonify(market_data)

@app.route('/api/bot/status')
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    global bot_status
    
    # Cập nhật chế độ API từ cấu hình
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        api_mode = config.get('api_mode', 'demo')
        # Đảm bảo mode nhất quán trong toàn bộ hệ thống
        bot_status['mode'] = api_mode.lower()
        logger.debug(f"Đã cập nhật chế độ API: {bot_status['mode']}")
    except Exception as e:
        logger.error(f"Lỗi khi đọc cấu hình api_mode: {str(e)}")
    
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
            'mode': 'demo',  # Quan trọng: để chữ thường cho đồng bộ với chế độ
            'leverage': 3,
            'positions': [
                # Tạo dữ liệu mẫu cho chế độ demo
            ]
        }
    elif api_mode == 'testnet':
        account_data = {
            'balance': 1000.00,
            'equity': 1000.00,
            'available': 1000.00,
            'margin': 0.00,
            'pnl': 0.00,
            'currency': 'USDT',
            'mode': 'testnet',  # Quan trọng: để chữ thường cho đồng bộ với chế độ
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
            'mode': 'live',  # Quan trọng: để chữ thường cho đồng bộ với chế độ
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

@app.route('/api/bot/logs', methods=['GET'])
def get_bot_logs():
    """Lấy nhật ký hoạt động của bot"""
    bot_id = request.args.get('bot_id')
    
    # Giới hạn số lượng log
    limit = int(request.args.get('limit', 50))
    
    # Dữ liệu mẫu cho logs
    current_time = datetime.now()
    logs = [
        {
            'timestamp': (current_time - timedelta(minutes=1)).isoformat(),
            'category': 'market',
            'message': 'Phân tích thị trường BTC: Xu hướng tăng, RSI = 65.2, Bollinger Bands đang mở rộng'
        },
        {
            'timestamp': (current_time - timedelta(minutes=2)).isoformat(),
            'category': 'analysis',
            'message': 'Đã hoàn thành phân tích kỹ thuật cho BTCUSDT trên khung thời gian 1h'
        },
        {
            'timestamp': (current_time - timedelta(minutes=3)).isoformat(),
            'category': 'decision',
            'message': 'Quyết định: MUA BTCUSDT tại 83,250 USDT, SL: 82,150 USDT, TP: 85,500 USDT'
        },
        {
            'timestamp': (current_time - timedelta(minutes=4)).isoformat(),
            'category': 'action',
            'message': 'Đã đặt lệnh: MUA 0.05 BTCUSDT với giá 83,250 USDT'
        },
        {
            'timestamp': (current_time - timedelta(minutes=5)).isoformat(),
            'category': 'market',
            'message': 'Phân tích thị trường ETH: Xu hướng giảm, MACD chuyển sang tiêu cực'
        },
        {
            'timestamp': (current_time - timedelta(minutes=6)).isoformat(),
            'category': 'decision',
            'message': 'Quyết định: BÁN ETHUSDT tại 4,120 USDT, SL: 4,220 USDT, TP: 3,950 USDT'
        },
        {
            'timestamp': (current_time - timedelta(minutes=7)).isoformat(),
            'category': 'action',
            'message': 'Đã đặt lệnh: BÁN 0.2 ETHUSDT với giá 4,120 USDT'
        },
        {
            'timestamp': (current_time - timedelta(minutes=8)).isoformat(),
            'category': 'market',
            'message': 'Phân tích thị trường SOL: Biến động cao, khó xác định xu hướng'
        },
        {
            'timestamp': (current_time - timedelta(minutes=9)).isoformat(),
            'category': 'decision',
            'message': 'Quyết định: GIỮ SOLUSDT, chờ thị trường ổn định'
        },
        {
            'timestamp': (current_time - timedelta(minutes=10)).isoformat(),
            'category': 'analysis',
            'message': 'Phân tích mẫu hình giá: BTC đang hình thành mẫu hình cờ tăng'
        }
    ]
    
    # Nếu có bot_id, lọc log chỉ của bot đó
    if bot_id and bot_id != 'all':
        # TODO: Trong thực tế, sẽ lọc log theo bot_id
        # Hiện tại chỉ giả lập cho demo
        pass
    
    return jsonify({
        'success': True,
        'logs': logs[:limit]
    })

@app.route('/api/bot/logs/<bot_id>', methods=['GET'])
def get_bot_logs_by_id(bot_id):
    """Lấy nhật ký hoạt động của một bot cụ thể"""
    return get_bot_logs()

@app.route('/api/bot/decisions', methods=['GET'])
def get_bot_decisions():
    """Lấy quyết định giao dịch gần đây của bot"""
    bot_id = request.args.get('bot_id')
    limit = int(request.args.get('limit', 5))
    
    # Dữ liệu mẫu
    current_time = datetime.now()
    decisions = [
        {
            'timestamp': (current_time - timedelta(minutes=3)).isoformat(),
            'symbol': 'BTCUSDT',
            'action': 'BUY',
            'entry_price': 83250.00,
            'take_profit': 85500.00,
            'stop_loss': 82150.00,
            'reasons': [
                'RSI vượt ngưỡng 30 từ dưới lên',
                'Giá đang nằm trên MA50',
                'Khối lượng giao dịch tăng'
            ]
        },
        {
            'timestamp': (current_time - timedelta(minutes=6)).isoformat(),
            'symbol': 'ETHUSDT',
            'action': 'SELL',
            'entry_price': 4120.00,
            'take_profit': 3950.00,
            'stop_loss': 4220.00,
            'reasons': [
                'MACD đường chính cắt xuống đường tín hiệu',
                'Giá chạm kháng cự mạnh',
                'Đồng thời phân kỳ âm'
            ]
        },
        {
            'timestamp': (current_time - timedelta(minutes=9)).isoformat(),
            'symbol': 'SOLUSDT',
            'action': 'HOLD',
            'reasons': [
                'Thị trường đang biến động cao',
                'Chưa có tín hiệu vào lệnh rõ ràng',
                'Chờ giá ổn định trước khi ra quyết định'
            ]
        }
    ]
    
    # Nếu có bot_id, lọc quyết định chỉ của bot đó
    if bot_id and bot_id != 'all':
        # TODO: Trong thực tế, sẽ lọc theo bot_id
        pass
    
    return jsonify({
        'success': True,
        'decisions': decisions[:limit]
    })

@app.route('/api/bot/stats', methods=['GET'])
def get_bot_stats():
    """Lấy thống kê hoạt động của bot"""
    bot_id = request.args.get('bot_id')
    
    # Dữ liệu mẫu
    stats = {
        'uptime': '14h 35m',
        'analyses': 342,
        'decisions': 28,
        'orders': 12
    }
    
    return jsonify({
        'success': True,
        'stats': stats
    })

@app.route('/api/execute_cli', methods=['POST'])
def execute_cli_command():
    """Thực thi lệnh từ CLI web"""
    command = request.json.get('command', '')
    
    # TODO: Xử lý lệnh CLI
    
    result = f"Đã thực thi lệnh: {command}"
    return jsonify({'result': result})

@app.route('/api/bot/control/<bot_id>', methods=['POST'])
def control_bot(bot_id):
    """API endpoint để điều khiển bot (start/stop/restart/delete)"""
    global bot_status
    
    # Kiểm tra dữ liệu từ request
    data = request.json
    action = data.get('action', '')
    
    if action not in ['start', 'stop', 'restart', 'delete']:
        return jsonify({
            'success': False,
            'message': f'Hành động không hợp lệ: {action}'
        })
    
    # Xử lý các hành động
    if action == 'start':
        bot_status['status'] = 'running'
        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Thông báo qua Socket.IO
        socketio.emit('bot_status_change', {
            'status': 'running',
            'message': f'Bot {"tất cả" if bot_id == "all" else bot_id} đã được khởi động'
        })
        
        # Gửi thông báo qua Telegram
        telegram_notifier.send_bot_status(
            status='running',
            mode=bot_status['mode'],
            uptime='0h 0m',
            stats={
                'Trạng thái': 'Đã khởi động'
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Bot {"tất cả" if bot_id == "all" else bot_id} đã được khởi động',
            'status': 'running'
        })
        
    elif action == 'stop':
        bot_status['status'] = 'stopped'
        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Thông báo qua Socket.IO
        socketio.emit('bot_status_change', {
            'status': 'stopped',
            'message': f'Bot {"tất cả" if bot_id == "all" else bot_id} đã được dừng'
        })
        
        # Gửi thông báo qua Telegram
        telegram_notifier.send_bot_status(
            status='stopped',
            mode=bot_status['mode'],
            uptime='--',
            stats={
                'Trạng thái': 'Đã dừng',
                'Thời gian': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Bot {"tất cả" if bot_id == "all" else bot_id} đã được dừng',
            'status': 'stopped'
        })
        
    elif action == 'restart':
        bot_status['status'] = 'running'
        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Thông báo qua Socket.IO
        socketio.emit('bot_status_change', {
            'status': 'running',
            'message': f'Bot {"tất cả" if bot_id == "all" else bot_id} đã được khởi động lại'
        })
        
        # Gửi thông báo qua Telegram
        telegram_notifier.send_bot_status(
            status='running',
            mode=bot_status['mode'],
            uptime='0h 0m',
            stats={
                'Trạng thái': 'Đã khởi động lại',
                'Thời gian': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Bot {"tất cả" if bot_id == "all" else bot_id} đã được khởi động lại',
            'status': 'running'
        })
        
    elif action == 'delete':
        # Chỉ áp dụng với bot cụ thể, không với 'all'
        if bot_id == 'all':
            return jsonify({
                'success': False,
                'message': 'Không thể xóa tất cả các bot cùng lúc'
            })
            
        # Xử lý xóa bot (giả lập)
        return jsonify({
            'success': True,
            'message': f'Bot {bot_id} đã được xóa',
            'status': 'deleted'
        })

def get_market_data():
    """Lấy dữ liệu thị trường thực từ Binance API"""
    # Lấy cấu hình tài khoản
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        api_mode = config.get('api_mode', 'demo')
    except:
        api_mode = 'demo'
    
    # Khởi tạo kết nối Binance API
    from binance_api import BinanceAPI
    # Tải khóa API từ biến môi trường
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")
    
    # Xác định chế độ sử dụng testnet hay mainnet
    use_testnet = api_mode != 'live'
    
    # Tạo đối tượng Binance API
    binance_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
    
    # Tạo market_data từ dữ liệu thực
    market_data = {}
    
    try:
        # Lấy giá BTC hiện tại
        btc_ticker = binance_client.get_symbol_ticker('BTCUSDT')
        if 'price' in btc_ticker:
            market_data['btc_price'] = float(btc_ticker['price'])
        else:
            market_data['btc_price'] = 0
            
        # Lấy giá ETH hiện tại
        eth_ticker = binance_client.get_symbol_ticker('ETHUSDT')
        if 'price' in eth_ticker:
            market_data['eth_price'] = float(eth_ticker['price'])
        else:
            market_data['eth_price'] = 0
            
        # Lấy giá SOL hiện tại
        sol_ticker = binance_client.get_symbol_ticker('SOLUSDT')
        if 'price' in sol_ticker:
            market_data['sol_price'] = float(sol_ticker['price'])
        else:
            market_data['sol_price'] = 0
            
        # Lấy dữ liệu ticker 24h cho BTC
        btc_24h = binance_client.get_24h_ticker('BTCUSDT')
        if 'priceChangePercent' in btc_24h:
            market_data['btc_change_24h'] = float(btc_24h['priceChangePercent'])
        else:
            market_data['btc_change_24h'] = 0
            
        # Lấy dữ liệu ticker 24h cho ETH
        eth_24h = binance_client.get_24h_ticker('ETHUSDT')
        if 'priceChangePercent' in eth_24h:
            market_data['eth_change_24h'] = float(eth_24h['priceChangePercent'])
        else:
            market_data['eth_change_24h'] = 0
            
        # Lấy dữ liệu ticker 24h cho SOL
        sol_24h = binance_client.get_24h_ticker('SOLUSDT')
        if 'priceChangePercent' in sol_24h:
            market_data['sol_change_24h'] = float(sol_24h['priceChangePercent'])
        else:
            market_data['sol_change_24h'] = 0
            
        # Tạo danh sách các cặp giao dịch từ dữ liệu thực
        market_data['pairs'] = [
            {
                'symbol': 'BTCUSDT',
                'price': market_data['btc_price'],
                'change': market_data['btc_change_24h'],
                'volume': btc_24h.get('volume', 0) if isinstance(btc_24h, dict) else 0
            },
            {
                'symbol': 'ETHUSDT',
                'price': market_data['eth_price'],
                'change': market_data['eth_change_24h'],
                'volume': eth_24h.get('volume', 0) if isinstance(eth_24h, dict) else 0
            },
            {
                'symbol': 'SOLUSDT',
                'price': market_data['sol_price'],
                'change': market_data['sol_change_24h'],
                'volume': sol_24h.get('volume', 0) if isinstance(sol_24h, dict) else 0
            }
        ]
        
        # Thêm chế độ thị trường và dữ liệu khác
        market_data['market_regime'] = {
            'BTC': 'neutral',
            'ETH': 'neutral',
            'SOL': 'neutral',
            'BNB': 'neutral'
        }
        
        # Thêm sentiment cho chỉ số sợ hãi/tham lam
        # Trong thực tế, điều này nên được tính toán dựa trên dữ liệu phân tích
        market_data['sentiment'] = {
            'value': 65,  # 0-100
            'state': 'warning',  # danger, warning, success tương ứng với sợ hãi, trung lập, tham lam
            'text': 'Tham lam nhẹ'
        }
        
        # Thêm các thông tin khối lượng và xu hướng giao dịch
        market_data['volume_24h'] = {
            'BTC': btc_24h.get('volume', 0) if isinstance(btc_24h, dict) else 12345.67,
            'ETH': eth_24h.get('volume', 0) if isinstance(eth_24h, dict) else 45678.90,
            'SOL': sol_24h.get('volume', 0) if isinstance(sol_24h, dict) else 987654.32
        }
        
        # Cập nhật thông tin thị trường hiện tại
        market_data['market_summary'] = {
            'total_volume_24h': 15234567.89,
            'gainers_count': 12,
            'losers_count': 8,
            'stable_count': 5
        }
        
        # Thêm thông tin các mức hỗ trợ/kháng cự
        market_data['btc_levels'] = {
            'support': [
                {'price': market_data['btc_price'] * 0.97, 'strength': 'strong'},
                {'price': market_data['btc_price'] * 0.95, 'strength': 'medium'}
            ],
            'resistance': [
                {'price': market_data['btc_price'] * 1.03, 'strength': 'medium'},
                {'price': market_data['btc_price'] * 1.05, 'strength': 'strong'}
            ]
        }
            
        logger.info(f"Đã lấy dữ liệu thị trường thực từ Binance API: BTC=${market_data['btc_price']}")
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường từ Binance API: {str(e)}")
        # Sử dụng dữ liệu mẫu nếu không lấy được dữ liệu thực
        market_data = SAMPLE_MARKET_DATA.copy()
    
    # Cập nhật danh sách cặp giao dịch
    for pair in market_data['pairs']:
        if pair['symbol'] == 'BTCUSDT':
            pair['price'] = market_data['btc_price']
            pair['change'] = market_data['btc_change_24h']
        elif pair['symbol'] == 'ETHUSDT':
            pair['price'] = market_data['eth_price']
            pair['change'] = market_data['eth_change_24h']
        elif pair['symbol'] == 'SOLUSDT':
            pair['price'] = market_data['sol_price']
            pair['change'] = market_data['sol_change_24h']
    
    # Trả về dữ liệu thị trường đã được cập nhật
    return market_data

def update_market_data():
    """Cập nhật dữ liệu thị trường theo định kỳ"""
    market_data = get_market_data()
    
    # Bổ sung thêm thông tin chỉ báo kỹ thuật chi tiết cho mỗi coin
    if not 'indicators' in market_data:
        market_data['indicators'] = {
            'BTC': {
                'rsi': 62.5,
                'macd': 0.0025,
                'ma_short': 47750.32,
                'ma_long': 46982.78,
                'bb_upper': 48950.12,
                'bb_lower': 46250.67,
                'bb_middle': 47650.45,
                'trend': market_data.get('market_regime', {}).get('BTC', 'neutral')
            },
            'ETH': {
                'rsi': 48.2,
                'macd': -0.0012,
                'ma_short': 3230.45,
                'ma_long': 3185.26,
                'bb_upper': 3350.68,
                'bb_lower': 3125.35,
                'bb_middle': 3238.12,
                'trend': market_data.get('market_regime', {}).get('ETH', 'neutral')
            },
            'SOL': {
                'rsi': 35.8,
                'macd': -0.0045,
                'ma_short': 142.35,
                'ma_long': 147.82,
                'bb_upper': 152.45,
                'bb_lower': 138.76,
                'bb_middle': 145.65,
                'trend': market_data.get('market_regime', {}).get('SOL', 'neutral')
            },
            'BNB': {
                'rsi': 58.3,
                'macd': 0.0018,
                'ma_short': 390.25,
                'ma_long': 385.45,
                'bb_upper': 402.35,
                'bb_lower': 378.65,
                'bb_middle': 390.50,
                'trend': market_data.get('market_regime', {}).get('BNB', 'neutral')
            }
        }
    
    # Bổ sung thêm tín hiệu giao dịch chi tiết cho mỗi coin
    if not 'signals' in market_data:
        market_data['signals'] = {
            'BTC': {
                'type': 'BUY',
                'strength': 'strong',
                'price': market_data.get('btc_price', 0),
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'strategy': 'RSI + Bollinger Bands'
            },
            'ETH': {
                'type': 'SELL',
                'strength': 'medium',
                'price': market_data.get('eth_price', 0),
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'strategy': 'MACD + EMA Cross'
            },
            'SOL': {
                'type': 'HOLD',
                'strength': 'weak',
                'price': market_data.get('sol_price', 0),
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'strategy': 'Trend Analysis'
            },
            'BNB': {
                'type': 'BUY',
                'strength': 'medium',
                'price': 388.75,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'strategy': 'Bollinger Breakout'
            }
        }
    
    # Phát sự kiện cập nhật dữ liệu
    socketio.emit('market_update', market_data)
    
    # Thêm log hoạt động phân tích thị trường
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'category': 'market',
        'message': f'Phân tích thị trường BTC: {market_data["market_regime"]["BTC"]}, RSI = {market_data["indicators"]["BTC"]["rsi"]}'
    }
    socketio.emit('bot_log', log_data)
    
    # Thỉnh thoảng tạo quyết định giao dịch mới
    # Chỉ demo, trong thực tế sẽ dựa trên logic phân tích thực của bot
    if random.random() < 0.2:  # 20% khả năng
        # Chỉ chọn các coin có dữ liệu giá thực
        available_coins = []
        if market_data.get('btc_price', 0) > 0:
            available_coins.append('BTC')
        if market_data.get('eth_price', 0) > 0:
            available_coins.append('ETH')
        if market_data.get('sol_price', 0) > 0:
            available_coins.append('SOL')
        
        # Nếu không có coin nào có giá thực, thêm BNB với giá mặc định
        if not available_coins:
            available_coins = ['BNB']
        
        coin = random.choice(available_coins)
        action = market_data['signals'][coin]['type']
        
        # Tạo một quyết định giao dịch và báo cáo
        if action in ['BUY', 'SELL']:
            # Lấy giá thực từ market_data
            price = market_data.get(f'{coin.lower()}_price', 0)
            
            # Hiển thị giá đang sử dụng trong log
            logger.info(f"Tạo tín hiệu giao dịch {action} cho {coin} với giá: {price}")
            
            # Sử dụng giá mặc định cho BNB nếu không có hoặc giá = 0
            if coin.lower() == 'bnb' or price <= 0:
                price = 388.75
                
            # Tính toán stop loss và take profit
            if action == 'BUY':
                stop_loss = price * 0.985  # -1.5%
                take_profit = price * 1.03  # +3%
            else:  # SELL
                stop_loss = price * 1.015  # +1.5%
                take_profit = price * 0.97  # -3%
                
            decision = {
                'timestamp': datetime.now().isoformat(),
                'symbol': f'{coin}USDT',
                'action': action,
                'entry_price': price,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'reasons': [
                    f'RSI = {market_data["indicators"][coin]["rsi"]}',
                    f'MACD = {market_data["indicators"][coin]["macd"]}',
                    f'Xu hướng: {market_data["indicators"][coin]["trend"]}'
                ]
            }
            socketio.emit('trading_decision', decision)
            
            # Thêm log quyết định
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'category': 'decision',
                'message': f'Quyết định: {action} {coin}USDT tại {price:.2f} USDT, SL: {stop_loss:.2f} USDT, TP: {take_profit:.2f} USDT'
            }
            socketio.emit('bot_log', log_data)
            
            # Cập nhật chế độ API từ cấu hình
            try:
                with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                api_mode = config.get('api_mode', 'demo')
            except:
                api_mode = 'demo'
            
            # Xác định số lượng giao dịch dựa trên loại coin
            quantity = 0.01 if coin == 'BTC' else (0.2 if coin == 'ETH' else 1.0)
            symbol = f"{coin}USDT"
            
            # Chỉ tạo lệnh thực sự nếu không phải chế độ demo và có API keys
            order_result = None
            order_placed = False
            order_error = None
            
            if api_mode in ['testnet', 'live']:
                try:
                    # Tạo lệnh giao dịch thực tế thông qua Binance API
                    with app.app_context():
                        binance_client = BinanceAPI()
                        
                        # Kiểm tra đủ điều kiện tạo lệnh
                        if not binance_client.api_key or not binance_client.api_secret:
                            logger.warning(f"Không thể tạo lệnh {action} {symbol}: Thiếu API keys")
                            order_error = "Thiếu API keys"
                        elif not price or price <= 0:
                            logger.warning(f"Không thể tạo lệnh {action} {symbol}: Giá không hợp lệ")
                            order_error = "Giá không hợp lệ"
                        else:
                            # Thử tạo lệnh thực tế
                            try:
                                # Tạo client order ID duy nhất
                                client_order_id = f"bot_{int(time.time()*1000)}_{random.randint(1000, 9999)}"
                                
                                # Tham số gửi lệnh
                                order_params = {
                                    'timeInForce': 'GTC',
                                    'quantity': quantity,
                                    'price': price,
                                    'newClientOrderId': client_order_id
                                }
                                
                                # Thực thi lệnh
                                order_result = binance_client.create_order(
                                    symbol=symbol,
                                    side=action,
                                    type='LIMIT',
                                    **order_params
                                )
                                
                                if order_result and 'orderId' in order_result:
                                    order_placed = True
                                    logger.info(f"Đã tạo lệnh {action} {symbol} thành công: ID={order_result['orderId']}")
                                else:
                                    logger.warning(f"Tạo lệnh {action} {symbol} không thành công: {order_result}")
                                    order_error = "API trả về kết quả không hợp lệ"
                            except Exception as e:
                                logger.error(f"Lỗi khi tạo lệnh {action} {symbol}: {str(e)}")
                                order_error = f"Lỗi API: {str(e)}"
                except Exception as e:
                    logger.error(f"Lỗi khởi tạo Binance API: {str(e)}")
                    order_error = f"Lỗi kết nối: {str(e)}"
            else:
                # Chế độ demo không thực sự tạo lệnh
                logger.info(f"Chế độ {api_mode.upper()}: Mô phỏng lệnh {action} {symbol}")
                order_error = f"Chế độ {api_mode.upper()} chỉ mô phỏng lệnh"
            
            # Lịch sử giao dịch lưu vào log
            trade_log = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': action,
                'price': price,
                'quantity': quantity,
                'mode': api_mode,
                'success': order_placed,
                'error': order_error,
                'order_id': order_result.get('orderId') if order_result else None
            }
            
            # Lưu vào file log để kiểm tra sau này
            try:
                with open('trade_history.json', 'a+') as f:
                    f.write(json.dumps(trade_log) + '\n')
            except Exception as e:
                logger.error(f"Không thể lưu lịch sử giao dịch: {str(e)}")
                
            # Gửi thông báo qua Telegram
            reason_text = f"RSI = {market_data['indicators'][coin]['rsi']}, MACD = {market_data['indicators'][coin]['macd']}, Xu hướng: {market_data['indicators'][coin]['trend']}"
            
            # Thêm thông tin về kết quả tạo lệnh
            if order_placed:
                reason_text += f"\n✅ Đã đặt lệnh thành công: ID={order_result['orderId']}"
            elif order_error:
                reason_text += f"\n❌ Chưa đặt lệnh: {order_error}"
            
            telegram_notifier.send_trade_entry(
                symbol=symbol,
                side=action,
                entry_price=price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=reason_text,
                mode=api_mode,
                order_id=order_result.get('orderId') if order_result else None,
                order_placed=order_placed
            )

def update_account_data():
    """Cập nhật dữ liệu tài khoản theo định kỳ"""
    with app.app_context():
        account_data = get_account().json
        socketio.emit('account_update', account_data)
    
    # Cập nhật vị thế
    if account_data.get('positions'):
        socketio.emit('positions_update', account_data['positions'])
        
        # Thỉnh thoảng (chỉ demo) tạo log thực thi giao dịch
        if random.random() < 0.1:  # 10% khả năng
            position = random.choice(account_data['positions'])
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'category': 'action',
                'message': f'Cập nhật vị thế: {position["symbol"]} {position["type"]}, Giá hiện tại: {position["current_price"]}, P&L: {position["pnl"]:.2f} USDT'
            }
            socketio.emit('bot_log', log_data)
            
            # Thỉnh thoảng gửi thông báo lãi/lỗ qua Telegram (mô phỏng thoát lệnh)
            if random.random() < 0.05:  # 5% khả năng sẽ mô phỏng thoát lệnh
                is_profit = position['pnl'] > 0
                side = 'BUY' if position['type'] == 'LONG' else 'SELL'
                exit_price = position['current_price']
                entry_price = position['entry_price']
                
                # Cập nhật chế độ API từ cấu hình
                try:
                    with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                        config = json.load(f)
                    api_mode = config.get('api_mode', 'demo')
                except:
                    api_mode = 'demo'

                # Gửi thông báo thoát lệnh qua Telegram
                telegram_notifier.send_trade_exit(
                    symbol=position['symbol'],
                    side=side,
                    exit_price=exit_price,
                    entry_price=entry_price,
                    quantity=position['size'],
                    profit_loss=position['pnl'],
                    profit_loss_percent=position['pnl_percent'],
                    exit_reason="Đạt mức take profit" if is_profit else "Kích hoạt stop loss",
                    mode=api_mode
                )
                
                # Gửi cảnh báo thị trường nếu có biến động lớn
                if random.random() < 0.2:  # 20% khả năng gửi thêm cảnh báo
                    symbol = position['symbol'].replace('USDT', '')
                    telegram_notifier.send_market_alert(
                        symbol=position['symbol'],
                        alert_type=f"Biến động lớn cho {symbol}",
                        price=exit_price,
                        message=f"Giá {symbol} đã biến động {position['pnl_percent']:.2f}% trong thời gian ngắn"
                    )

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
        
    # Thêm thống kê hoạt động của bot (trong thực tế sẽ lấy từ dữ liệu thật)
    stats = {
        'uptime': '14h 35m',
        'analyses': 342,
        'decisions': 28,
        'orders': 12
    }
    
    # Cập nhật bot status với thêm thông tin stats
    bot_status_update = bot_status.copy()
    bot_status_update['stats'] = stats
    
    # Bổ sung thêm thông tin phiên bản
    bot_status_update['version'] = '3.2.1'
    
    socketio.emit('bot_status_update', bot_status_update)

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
            # Đảm bảo mode nhất quán trong toàn bộ hệ thống
            bot_status['mode'] = api_mode.lower()
        else:
            logger.info("Auto-start bot is disabled in testing environment")
            bot_status['mode'] = api_mode.lower()  # Set mode anyway
        
        # Lấy thông tin tài khoản và gửi thông báo khởi động
        try:
            # Lấy dữ liệu thị trường
            market_data = get_market_data()
            
            # Lấy dữ liệu tài khoản
            with app.app_context():
                account_data = get_account().json
                
            # Xác định thông tin tài khoản
            try:
                account_balance = float(account_data.get('totalWalletBalance', 0))
                # Nếu số dư từ API là 0 hoặc không hợp lệ, gán số dư mặc định là 10,000 USDT cho môi trường testnet/demo
                if account_balance <= 0 and api_mode in ['testnet', 'demo']:
                    logger.warning("Số dư từ API không hợp lệ, sử dụng số dư mặc định cho môi trường testnet/demo")
                    account_balance = 10000.0
            except (ValueError, TypeError) as e:
                logger.error(f"Lỗi khi xử lý số dư tài khoản: {str(e)}")
                account_balance = 10000.0 if api_mode in ['testnet', 'demo'] else 0.0
                
            positions = account_data.get('positions', [])
            
            # Tính tổng lãi/lỗ chưa thực hiện
            unrealized_pnl = 0.0
            active_positions = []
            
            # Lọc các vị thế đang mở (có positionAmt khác 0)
            for position in positions:
                if float(position.get('positionAmt', 0)) != 0:
                    position_size = abs(float(position.get('positionAmt', 0)))
                    entry_price = float(position.get('entryPrice', 0))
                    mark_price = float(position.get('markPrice', 0)) 
                    
                    # Xác định hướng vị thế
                    position_side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
                    
                    # Tính PNL
                    pnl = 0
                    if position_side == 'LONG':
                        pnl = (mark_price - entry_price) * position_size
                    else:
                        pnl = (entry_price - mark_price) * position_size
                    
                    # Tính % PNL
                    pnl_percent = 0
                    if entry_price > 0:
                        if position_side == 'LONG':
                            pnl_percent = (mark_price - entry_price) / entry_price * 100
                        else:
                            pnl_percent = (entry_price - mark_price) / entry_price * 100
                    
                    # Cập nhật Unrealized PNL
                    unrealized_pnl += pnl
                    
                    # Tạo dữ liệu vị thế đơn giản
                    active_positions.append({
                        'symbol': position.get('symbol', 'UNKNOWN'),
                        'type': position_side,
                        'size': position_size,
                        'entry_price': entry_price,
                        'current_price': mark_price,
                        'pnl': pnl,
                        'pnl_percent': pnl_percent
                    })
            
            # Gửi thông báo trạng thái hệ thống qua Telegram
            telegram_notifier.send_system_status(
                account_balance=account_balance,
                positions=active_positions,
                unrealized_pnl=unrealized_pnl,
                market_data=market_data,
                mode=api_mode
            )
            
            logger.info(f"Đã gửi thông báo khởi động hệ thống với dữ liệu tài khoản: số dư={account_balance}, PNL chưa thực hiện={unrealized_pnl}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo khởi động hệ thống: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error during auto-start check: {str(e)}")
    
    # Bắt đầu thread cho các tác vụ nền
    thread = threading.Thread(target=background_tasks)
    thread.daemon = True
    thread.start()
    logger.info("Background tasks started")

# Khởi động các tác vụ nền
start_background_tasks()
    
# Không chạy ứng dụng ở đây - được quản lý bởi gunicorn
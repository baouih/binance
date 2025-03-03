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
        coin = random.choice(['BTC', 'ETH', 'SOL', 'BNB'])
        action = market_data['signals'][coin]['type']
        
        # Tạo một quyết định giao dịch và báo cáo
        if action in ['BUY', 'SELL']:
            price = market_data.get(f'{coin.lower()}_price', 0)
            if coin.lower() == 'bnb':
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

def update_account_data():
    """Cập nhật dữ liệu tài khoản theo định kỳ"""
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
    # Sử dụng gunicorn cho môi trường production
    # socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
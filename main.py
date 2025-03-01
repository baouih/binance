#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot Dashboard
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import os
import json
import logging
import random
import threading
import time
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Khởi tạo Flask app và Socket.IO
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=10, ping_interval=5)

# Import Blueprint cho cấu hình
try:
    from config_route import config_bp
    app.register_blueprint(config_bp)
    logger.info("Đã đăng ký blueprint cho cấu hình")
except ImportError:
    logger.warning("Không thể import config_route blueprint")

# Các giá trị mẫu cho các biểu đồ và bảng
sample_prices = {
    "BTCUSDT": 80000 + random.uniform(-2000, 2000),
    "ETHUSDT": 2300 + random.uniform(-100, 100),
    "BNBUSDT": 380 + random.uniform(-20, 20),
    "SOLUSDT": 140 + random.uniform(-10, 10)
}

sample_account = {
    "balance": 10000.0,
    "equity": 10250.0,
    "margin": 500.0,
    "free_balance": 9500.0,
    "positions": [
        {
            "id": "pos1",
            "symbol": "BTCUSDT",
            "type": "LONG",
            "entry_price": 75000.0,
            "current_price": 80000.0,
            "quantity": 0.05,
            "pnl": 250.0,
            "pnl_percent": 6.67
        }
    ]
}

sample_signals = [
    {
        "time": "10:30",
        "symbol": "BTCUSDT",
        "signal": "BUY",
        "confidence": 85
    },
    {
        "time": "11:45",
        "symbol": "ETHUSDT",
        "signal": "SELL",
        "confidence": 75
    }
]

bot_status = {
    "status": "running",
    "last_update": datetime.now().strftime("%H:%M:%S"),
    "last_action": "Monitoring market conditions"
}

# Các hàm trợ giúp
def load_trading_state():
    """Load trading state from file"""
    try:
        if os.path.exists("trading_state.json"):
            with open("trading_state.json", "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading trading state: {e}")
    return None

def load_multi_coin_config():
    """Load multi-coin configuration"""
    try:
        if os.path.exists("multi_coin_config.json"):
            with open("multi_coin_config.json", "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading multi-coin config: {e}")
    return None

# Routes
@app.route('/')
def index():
    """Trang chủ Dashboard"""
    return render_template('dashboard.html')

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

@app.route('/settings')
def settings():
    """Trang cài đặt bot"""
    return render_template('settings.html')

@app.route('/report')
def report():
    """Trang báo cáo giao dịch"""
    return render_template('trading_report.html')

# API Endpoints
@app.route('/api/bot/control', methods=['POST'])
def bot_control():
    """Điều khiển bot (start/stop/restart)"""
    action = request.json.get('action')
    
    if action == 'start':
        # Thực thi lệnh khởi động bot
        os.system("python multi_coin_bot.py &")
        bot_status['status'] = 'running'
        bot_status['last_action'] = 'Bot started'
    elif action == 'stop':
        # Thực thi lệnh dừng bot
        os.system("pkill -f 'python multi_coin_bot.py'")
        bot_status['status'] = 'stopped'
        bot_status['last_action'] = 'Bot stopped'
    elif action == 'restart':
        # Thực thi lệnh khởi động lại bot
        os.system("pkill -f 'python multi_coin_bot.py'")
        os.system("python multi_coin_bot.py &")
        bot_status['status'] = 'running'
        bot_status['last_action'] = 'Bot restarted'
    
    bot_status['last_update'] = datetime.now().strftime("%H:%M:%S")
    
    # Emit status to all clients
    socketio.emit('bot_status', bot_status)
    
    return jsonify({"success": True, "status": bot_status})

@app.route('/api/positions/close', methods=['POST'])
def close_position():
    """Đóng một vị thế"""
    position_id = request.json.get('position_id')
    
    # Tìm và xóa vị thế khỏi danh sách mẫu
    for i, pos in enumerate(sample_account['positions']):
        if pos['id'] == position_id:
            sample_account['positions'].pop(i)
            sample_account['balance'] += pos['pnl']
            socketio.emit('account_update', sample_account)
            return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Position not found"})

@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    # Kiểm tra xem bot có đang chạy không
    result = os.popen("ps aux | grep 'python multi_coin_bot.py' | grep -v grep").read()
    if result:
        bot_status['status'] = 'running'
    else:
        bot_status['status'] = 'stopped'
    
    bot_status['last_update'] = datetime.now().strftime("%H:%M:%S")
    return jsonify(bot_status)

@app.route('/api/account', methods=['GET'])
def get_account():
    """Lấy dữ liệu tài khoản"""
    # Tải trạng thái giao dịch từ file
    state = load_trading_state()
    if state:
        balance = state.get('current_balance', 10000.0)
        positions = state.get('open_positions', [])
        equity = balance
        for pos in positions:
            equity += pos.get('pnl', 0)
        
        account_data = {
            "balance": balance,
            "equity": equity,
            "margin": 0,
            "free_balance": balance,
            "positions": positions
        }
        return jsonify(account_data)
    
    return jsonify(sample_account)

@app.route('/api/signals', methods=['GET'])
def get_signals():
    """Lấy tín hiệu giao dịch gần đây"""
    return jsonify({"signals": sample_signals})

@app.route('/api/market', methods=['GET'])
def get_market():
    """Lấy dữ liệu thị trường"""
    return jsonify({"prices": sample_prices})

@app.route('/api/coins', methods=['GET'])
def get_coins():
    """Lấy danh sách coin đang giao dịch"""
    config = load_multi_coin_config()
    if config:
        trading_pairs = []
        for pair in config.get('trading_pairs', []):
            if pair.get('enabled', False):
                trading_pairs.append({
                    "symbol": pair.get('symbol'),
                    "timeframes": pair.get('timeframes'),
                    "strategies": pair.get('strategies')
                })
        return jsonify({"trading_pairs": trading_pairs})
    
    # Trả về dữ liệu mẫu nếu không tìm thấy config
    return jsonify({"trading_pairs": [
        {"symbol": "BTCUSDT", "timeframes": ["1h", "4h", "1d"], "strategies": ["composite", "ml"]},
        {"symbol": "ETHUSDT", "timeframes": ["1h", "4h", "1d"], "strategies": ["composite", "ml"]}
    ]})

# WebSocket Endpoints
@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối"""
    logger.info('Client connected')
    emit('bot_status', bot_status)
    emit('account_update', sample_account)
    emit('market_update', {"prices": sample_prices})
    emit('signal_update', {"signals": sample_signals})

@socketio.on('disconnect')
def handle_disconnect():
    """Xử lý khi client ngắt kết nối"""
    logger.info('Client disconnected')

# Các hàm giả lập cập nhật dữ liệu theo thời gian thực
def simulate_price_updates():
    """Giả lập cập nhật giá thời gian thực"""
    while True:
        try:
            for symbol in sample_prices:
                # Thêm biến động ngẫu nhiên (0.1% - 0.5%)
                change_pct = random.uniform(-0.005, 0.005)
                sample_prices[symbol] *= (1 + change_pct)
            
            socketio.emit('price_update', {"prices": sample_prices})
            time.sleep(60)  # Tăng khoảng thời gian cập nhật từ 5 lên 60 giây để giảm tải
        except Exception as e:
            logger.error(f"Lỗi trong quá trình cập nhật giá: {e}")
            time.sleep(60)  # Dừng một lúc nếu có lỗi

def simulate_sentiment_updates():
    """Giả lập cập nhật tâm lý thị trường"""
    while True:
        try:
            sentiment = {
                "value": random.randint(30, 70),
                "change": random.uniform(-5, 5),
                "trend": "neutral"
            }
            
            socketio.emit('sentiment_update', sentiment)
            time.sleep(120)  # Tăng lên 2 phút để giảm tải
        except Exception as e:
            logger.error(f"Lỗi trong quá trình cập nhật tâm lý thị trường: {e}")
            time.sleep(120)

def simulate_account_updates():
    """Giả lập cập nhật tài khoản và vị thế"""
    while True:
        try:
            # Tải trạng thái giao dịch từ file
            state = load_trading_state()
            if state:
                balance = state.get('current_balance', 10000.0)
                positions = state.get('open_positions', [])
                equity = balance
                for pos in positions:
                    equity += pos.get('pnl', 0)
                
                account_data = {
                    "balance": balance,
                    "equity": equity,
                    "margin": 0,
                    "free_balance": balance,
                    "positions": positions
                }
                socketio.emit('account_update', account_data)
            else:
                # Cập nhật giá hiện tại cho các vị thế
                for pos in sample_account['positions']:
                    pos['current_price'] = sample_prices.get(pos['symbol'], pos['current_price'])
                    
                    # Tính lại P&L
                    if pos['type'] == 'LONG':
                        pos['pnl'] = (pos['current_price'] - pos['entry_price']) * pos['quantity']
                        pos['pnl_percent'] = (pos['current_price'] / pos['entry_price'] - 1) * 100
                    else:  # SHORT
                        pos['pnl'] = (pos['entry_price'] - pos['current_price']) * pos['quantity']
                        pos['pnl_percent'] = (pos['entry_price'] / pos['current_price'] - 1) * 100
                
                # Cập nhật equity
                sample_account['equity'] = sample_account['balance']
                for pos in sample_account['positions']:
                    sample_account['equity'] += pos['pnl']
                
                socketio.emit('account_update', sample_account)
            
            time.sleep(60)  # Tăng thời gian cập nhật từ 10 lên 60 giây để giảm tải
        except Exception as e:
            logger.error(f"Lỗi trong quá trình cập nhật tài khoản: {e}")
            time.sleep(60)

def check_and_restart_bot():
    """Kiểm tra và khởi động lại bot nếu cần"""
    while True:
        try:
            # Tạm dừng chức năng auto-restart bot để giảm tải hệ thống
            # result = os.popen("ps aux | grep 'python multi_coin_bot.py' | grep -v grep").read()
            # if not result and bot_status['status'] == 'running':
            #     logger.info("Bot is not running but status is 'running'. Restarting...")
            #     os.system("python multi_coin_bot.py &")
            #     bot_status['last_action'] = 'Bot auto-restarted'
            #     bot_status['last_update'] = datetime.now().strftime("%H:%M:%S")
            #     socketio.emit('bot_status', bot_status)
            
            # Thay vì tự động khởi động lại bot, chỉ cập nhật trạng thái
            bot_status['last_update'] = datetime.now().strftime("%H:%M:%S")
            bot_status['last_action'] = 'Monitoring market conditions'
            time.sleep(120)  # Tăng thời gian kiểm tra lên 2 phút để giảm tải
        except Exception as e:
            logger.error(f"Lỗi trong quá trình kiểm tra bot: {e}")
            time.sleep(120)

def generate_daily_report():
    """Tạo báo cáo hàng ngày theo lịch"""
    while True:
        now = datetime.now()
        # Tạo báo cáo vào 00:01 mỗi ngày
        if now.hour == 0 and now.minute == 1:
            logger.info("Generating daily report...")
            os.system("python daily_report.py")
        
        time.sleep(60)  # Kiểm tra mỗi phút

# Khởi chạy các giả lập khi bắt đầu
def start_background_tasks():
    """Khởi chạy các tác vụ nền khi có request đầu tiên"""
    threading.Thread(target=simulate_price_updates, daemon=True).start()
    threading.Thread(target=simulate_sentiment_updates, daemon=True).start()
    threading.Thread(target=simulate_account_updates, daemon=True).start()
    threading.Thread(target=check_and_restart_bot, daemon=True).start()
    threading.Thread(target=generate_daily_report, daemon=True).start()
    
    # Tạm thời tắt chức năng khởi động bot tự động để giảm tải
    # result = os.popen("ps aux | grep 'python multi_coin_bot.py' | grep -v grep").read()
    # if not result:
    #     logger.info("Starting trading bot...")
    #     os.system("python multi_coin_bot.py &")
    logger.info("Skipping auto-start bot to reduce system load")
    
    logger.info("Background tasks started")

# Khởi động các tác vụ nền khi ứng dụng khởi động
with app.app_context():
    start_background_tasks()

if __name__ == '__main__':
    # Giảm số lượng thread backgroundtrên eventlet để tránh quá tải
    import eventlet
    eventlet.monkey_patch()
    
    # Giảm memory footprint của các background thread
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True,
                threaded=False, max_size=200)
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

# Cấu hình logging cho các module
logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Khởi tạo Flask app và Socket.IO
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Loại bỏ Socket.IO để cải thiện hiệu suất 
# và giảm thiểu lỗi kết nối
# Thay vào đó sử dụng AJAX hoặc fetch API để cập nhật dữ liệu

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
    # Generate sample data for dashboard
    current_balance = 12500.0
    initial_balance = 10000.0
    profit_percentage = ((current_balance / initial_balance) - 1) * 100
    
    win_rate = 65
    winning_trades = 13
    total_trades = 20
    
    risk_reward_ratio = 1.8
    profit_factor = 2.3
    
    max_drawdown_percent = 12.5
    recovery_factor = 2.1
    
    market_regime = "Trending"
    volatility = "Medium"
    trend_strength = 75
    
    composite_score = 0.7
    
    # Sample open positions
    open_positions = [
        {
            "id": "pos1",
            "symbol": "BTCUSDT",
            "type": "LONG",
            "entry_price": 72000.00,
            "current_price": 75000.00,
            "quantity": 0.1000,
            "pnl": 300.00,
            "pnl_percent": 4.17,
            "leverage": 5,
            "stop_loss": 69500.00,
            "take_profit": 78000.00,
            "entry_time": "2025-02-28 18:30"
        },
        {
            "id": "pos2",
            "symbol": "SOLUSDT",
            "type": "LONG",
            "entry_price": 125.00,
            "current_price": 137.50,
            "quantity": 1.0000,
            "pnl": 12.50,
            "pnl_percent": 10.00,
            "leverage": 3,
            "stop_loss": 115.00,
            "take_profit": 150.00,
            "entry_time": "2025-02-28 20:10"
        },
        {
            "id": "pos3",
            "symbol": "BNBUSDT",
            "type": "SHORT",
            "entry_price": 410.00,
            "current_price": 420.00,
            "quantity": 0.2000,
            "pnl": -2.00,
            "pnl_percent": -2.44,
            "leverage": 2,
            "stop_loss": 430.00,
            "take_profit": 390.00,
            "entry_time": "2025-02-28 22:05"
        }
    ]
    
    # Sample closed positions
    closed_positions = [
        {
            "id": "trade10",
            "symbol": "SHIBUSDT",
            "type": "LONG",
            "entry_price": 0.00,
            "exit_price": 0.00,
            "quantity": 5000000.0000,
            "pnl": 10.00,
            "pnl_percent": 10.00,
            "entry_time": "2025-02-28 07:30",
            "exit_time": "2025-02-28 08:15",
            "exit_reason": "take_profit"
        },
        {
            "id": "trade9",
            "symbol": "XRPUSDT",
            "type": "LONG",
            "entry_price": 0.80,
            "exit_price": 0.78,
            "quantity": 500.0000,
            "pnl": -10.00,
            "pnl_percent": -2.50,
            "entry_time": "2025-02-27 14:00",
            "exit_time": "2025-02-27 15:45",
            "exit_reason": "stop_loss"
        },
        {
            "id": "trade8",
            "symbol": "ADAUSDT",
            "type": "SHORT",
            "entry_price": 0.65,
            "exit_price": 0.62,
            "quantity": 500.0000,
            "pnl": 15.00,
            "pnl_percent": 4.62,
            "entry_time": "2025-02-27 10:15",
            "exit_time": "2025-02-27 13:30",
            "exit_reason": "take_profit"
        },
        {
            "id": "trade7",
            "symbol": "ETHUSDT",
            "type": "LONG",
            "entry_price": 3150.00,
            "exit_price": 3300.00,
            "quantity": 0.2000,
            "pnl": 30.00,
            "pnl_percent": 4.76,
            "entry_time": "2025-02-27 08:45",
            "exit_time": "2025-02-27 10:30",
            "exit_reason": "take_profit"
        },
        {
            "id": "trade6",
            "symbol": "BTCUSDT",
            "type": "LONG",
            "entry_price": 66000.00,
            "exit_price": 69500.00,
            "quantity": 0.1000,
            "pnl": 350.00,
            "pnl_percent": 5.30,
            "entry_time": "2025-02-26 22:30",
            "exit_time": "2025-02-27 09:00",
            "exit_reason": "take_profit"
        }
    ]
    
    # Check if bot is running
    result = os.popen("ps aux | grep 'python multi_coin_bot.py' | grep -v grep").read()
    bot_running = bool(result)
    
    return render_template('dashboard.html',
                          current_balance=current_balance,
                          initial_balance=initial_balance,
                          profit_percentage=profit_percentage,
                          win_rate=win_rate,
                          winning_trades=winning_trades,
                          total_trades=total_trades,
                          risk_reward_ratio=risk_reward_ratio,
                          profit_factor=profit_factor,
                          max_drawdown_percent=max_drawdown_percent,
                          recovery_factor=recovery_factor,
                          market_regime=market_regime,
                          volatility=volatility,
                          trend_strength=trend_strength,
                          composite_score=composite_score,
                          open_positions=open_positions,
                          closed_positions=closed_positions,
                          bot_running=bot_running)

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
    # Sample data
    total_trades = 20
    winning_trades = 13
    losing_trades = 7
    win_rate = 65
    total_profit = 755.50
    profit_factor = 2.3
    
    # Sample closed trades
    trades = [
        {
            "id": "trade10",
            "symbol": "SHIBUSDT",
            "type": "LONG",
            "entry_price": 0.00,
            "exit_price": 0.00,
            "quantity": 5000000.0000,
            "pnl": 10.00,
            "pnl_percent": 10.00,
            "entry_time": "2025-02-28 07:30",
            "exit_time": "2025-02-28 08:15",
            "exit_reason": "take_profit"
        },
        {
            "id": "trade9",
            "symbol": "XRPUSDT",
            "type": "LONG",
            "entry_price": 0.80,
            "exit_price": 0.78,
            "quantity": 500.0000,
            "pnl": -10.00,
            "pnl_percent": -2.50,
            "entry_time": "2025-02-27 14:00",
            "exit_time": "2025-02-27 15:45",
            "exit_reason": "stop_loss"
        },
        {
            "id": "trade8",
            "symbol": "ADAUSDT",
            "type": "SHORT",
            "entry_price": 0.65,
            "exit_price": 0.62,
            "quantity": 500.0000,
            "pnl": 15.00,
            "pnl_percent": 4.62,
            "entry_time": "2025-02-27 10:15",
            "exit_time": "2025-02-27 13:30",
            "exit_reason": "take_profit"
        },
        {
            "id": "trade7",
            "symbol": "ETHUSDT",
            "type": "LONG",
            "entry_price": 3150.00,
            "exit_price": 3300.00,
            "quantity": 0.2000,
            "pnl": 30.00,
            "pnl_percent": 4.76,
            "entry_time": "2025-02-27 08:45",
            "exit_time": "2025-02-27 10:30",
            "exit_reason": "take_profit"
        },
        {
            "id": "trade6",
            "symbol": "BTCUSDT",
            "type": "LONG",
            "entry_price": 66000.00,
            "exit_price": 69500.00,
            "quantity": 0.1000,
            "pnl": 350.00,
            "pnl_percent": 5.30,
            "entry_time": "2025-02-26 22:30",
            "exit_time": "2025-02-27 09:00",
            "exit_reason": "take_profit"
        },
        {
            "id": "trade5",
            "symbol": "DOGEUSDT",
            "type": "SHORT",
            "entry_price": 0.15,
            "exit_price": 0.16,
            "quantity": 5000.0000,
            "pnl": -50.00,
            "pnl_percent": -6.67,
            "entry_time": "2025-02-26 14:30",
            "exit_time": "2025-02-26 16:45",
            "exit_reason": "stop_loss"
        },
        {
            "id": "trade4",
            "symbol": "SOLUSDT",
            "type": "LONG",
            "entry_price": 110.00,
            "exit_price": 125.00,
            "quantity": 1.0000,
            "pnl": 15.00,
            "pnl_percent": 13.64,
            "entry_time": "2025-02-26 10:15",
            "exit_time": "2025-02-26 14:00",
            "exit_reason": "take_profit"
        },
        {
            "id": "trade3",
            "symbol": "BNBUSDT",
            "type": "SHORT",
            "entry_price": 450.00,
            "exit_price": 420.00,
            "quantity": 0.5000,
            "pnl": 15.00,
            "pnl_percent": 6.67,
            "entry_time": "2025-02-26 09:00",
            "exit_time": "2025-02-26 11:30",
            "exit_reason": "take_profit"
        },
        {
            "id": "trade2",
            "symbol": "ETHUSDT",
            "type": "LONG",
            "entry_price": 3200.00,
            "exit_price": 3100.00,
            "quantity": 0.2000,
            "pnl": -20.00,
            "pnl_percent": -3.12,
            "entry_time": "2025-02-25 08:30",
            "exit_time": "2025-02-25 10:45",
            "exit_reason": "stop_loss"
        },
        {
            "id": "trade1",
            "symbol": "BTCUSDT",
            "type": "LONG",
            "entry_price": 65000.00,
            "exit_price": 69000.00,
            "quantity": 0.1000,
            "pnl": 400.00,
            "pnl_percent": 6.15,
            "entry_time": "2025-02-25 05:30",
            "exit_time": "2025-02-25 09:15",
            "exit_reason": "take_profit"
        }
    ]
    
    # Check if bot is running
    result = os.popen("ps aux | grep 'python multi_coin_bot.py' | grep -v grep").read()
    bot_running = bool(result)
    
    return render_template('trades.html',
                          trades=trades,
                          total_trades=total_trades,
                          winning_trades=winning_trades,
                          losing_trades=losing_trades,
                          win_rate=win_rate,
                          total_profit=total_profit,
                          profit_factor=profit_factor,
                          bot_running=bot_running)

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
    
    # Đã loại bỏ socket.io, không cần emit status nữa
    
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
            # Đã loại bỏ socket.io, không cần emit account_update nữa
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

# REST API thay thế cho WebSocket để tăng hiệu năng
@app.route('/api/realtime/account', methods=['GET'])
def get_realtime_account():
    """API lấy dữ liệu tài khoản theo thời gian thực"""
    # Tải trạng thái giao dịch từ file
    state = load_trading_state()
    if state:
        return jsonify(get_account_from_state(state))
    return jsonify(sample_account)

@app.route('/api/realtime/market', methods=['GET'])
def get_realtime_market():
    """API lấy dữ liệu thị trường theo thời gian thực"""
    return jsonify({"prices": sample_prices})

@app.route('/api/realtime/signals', methods=['GET'])
def get_realtime_signals():
    """API lấy tín hiệu giao dịch theo thời gian thực"""
    return jsonify({"signals": sample_signals})

def get_account_from_state(state):
    """Tạo dữ liệu tài khoản từ trạng thái"""
    balance = state.get('current_balance', 10000.0)
    positions = state.get('open_positions', [])
    equity = balance
    for pos in positions:
        equity += pos.get('pnl', 0)
    
    return {
        "balance": balance,
        "equity": equity,
        "margin": 0,
        "free_balance": balance,
        "positions": positions
    }

# Các hàm giả lập cập nhật dữ liệu theo thời gian thực
def simulate_price_updates():
    """Giả lập cập nhật giá thời gian thực"""
    while True:
        try:
            for symbol in sample_prices:
                # Thêm biến động ngẫu nhiên (0.1% - 0.5%)
                change_pct = random.uniform(-0.005, 0.005)
                sample_prices[symbol] *= (1 + change_pct)
            
            # Không cần emit qua socket.io nữa
            time.sleep(60)  # Tăng khoảng thời gian cập nhật từ 5 lên 60 giây để giảm tải
        except Exception as e:
            logger.error(f"Lỗi trong quá trình cập nhật giá: {e}")
            time.sleep(60)  # Dừng một lúc nếu có lỗi

def simulate_sentiment_updates():
    """Giả lập cập nhật tâm lý thị trường"""
    while True:
        try:
            # Tạo dữ liệu sentiment ngẫu nhiên
            sentiment = {
                "value": random.randint(30, 70),
                "change": random.uniform(-5, 5),
                "trend": "neutral"
            }
            
            # Không cần emit qua socket.io nữa
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
            if not state:
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
            
            time.sleep(60)  # Tăng thời gian cập nhật từ 10 lên 60 giây để giảm tải
        except Exception as e:
            logger.error(f"Lỗi trong quá trình cập nhật tài khoản: {e}")
            time.sleep(60)

def check_and_restart_bot():
    """Kiểm tra và khởi động lại bot nếu cần"""
    # Kiểm tra nếu cần tự động khởi động lại bot khi gặp sự cố
    AUTO_RESTART_BOT = os.environ.get("AUTO_RESTART_BOT", "false").lower() == "true"
    
    while True:
        try:
            if AUTO_RESTART_BOT:
                # Kiểm tra nếu bot đã dừng nhưng trạng thái vẫn là đang chạy
                result = os.popen("ps aux | grep 'python multi_coin_bot.py' | grep -v grep").read()
                if not result and bot_status['status'] == 'running':
                    logger.info("Bot is not running but status is 'running'. Restarting...")
                    os.system("python multi_coin_bot.py &")
                    bot_status['last_action'] = 'Bot auto-restarted'
                    bot_status['last_update'] = datetime.now().strftime("%H:%M:%S")
                    # Không cần emit qua socket.io nữa
            else:
                # Nếu không ở chế độ tự động khởi động lại, chỉ cập nhật trạng thái
                result = os.popen("ps aux | grep 'python multi_coin_bot.py' | grep -v grep").read()
                if not result and bot_status['status'] == 'running':
                    logger.info("Bot has stopped but status is still 'running'. Updating status...")
                    bot_status['status'] = 'stopped'
                    bot_status['last_action'] = 'Bot stopped unexpectedly'
                    # Không cần emit qua socket.io nữa
            
            # Cập nhật trạng thái
            bot_status['last_update'] = datetime.now().strftime("%H:%M:%S")
            if bot_status['status'] == 'running':
                bot_status['last_action'] = 'Monitoring market conditions'
            time.sleep(120)  # Thời gian kiểm tra 2 phút để giảm tải
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
    
    # Kiểm tra nếu cần tự động khởi động bot (dựa trên biến môi trường)
    AUTO_START_BOT = os.environ.get("AUTO_START_BOT", "false").lower() == "true"
    
    if AUTO_START_BOT:
        result = os.popen("ps aux | grep 'python multi_coin_bot.py' | grep -v grep").read()
        if not result:
            logger.info("Starting trading bot automatically...")
            os.system("python multi_coin_bot.py &")
    else:
        logger.info("Auto-start bot is disabled in testing environment")
    
    logger.info("Background tasks started")

# Khởi động các tác vụ nền khi ứng dụng khởi động
with app.app_context():
    start_background_tasks()

if __name__ == '__main__':
    # Chạy Flask App trực tiếp không qua Socket.IO để tăng hiệu suất
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
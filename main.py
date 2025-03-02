#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot Dashboard
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
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
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Khởi tạo Flask app
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
    
    # Tạo dữ liệu mẫu cho bot_status để tránh lỗi template
    bot_status = {
        'running': False,
        'mode': 'demo',
        'account_type': 'futures',
        'strategy_mode': 'auto'
    }
    
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
    
    # Tạo dữ liệu mẫu cho account_data
    account_data = {
        'balance': 10400,
        'equity': 10710.5,
        'free_balance': 10400,
        'margin': 0,
        'leverage': 3,
        'positions': open_positions
    }
    
    # Tạo dữ liệu thị trường
    market_data = {
        'btc_price': sample_prices.get('BTCUSDT', 80000),
        'eth_price': sample_prices.get('ETHUSDT', 2300),
        'bnb_price': sample_prices.get('BNBUSDT', 380),
        'sol_price': sample_prices.get('SOLUSDT', 140),
        'btc_change_24h': random.uniform(-5, 5),
        'eth_change_24h': random.uniform(-7, 7),
        'bnb_change_24h': random.uniform(-4, 4),
        'sol_change_24h': random.uniform(-10, 10),
        'sentiment': {
            'value': random.randint(30, 70),
            'state': random.choice(['success', 'danger', 'warning', 'info']),
            'change': random.uniform(-5, 5),
            'trend': 'neutral'
        },
        'market_regime': {
            'BTCUSDT': 'Trending',
            'ETHUSDT': 'Ranging',
            'BNBUSDT': 'Volatile',
            'SOLUSDT': 'Ranging'
        }
    }
    
    market_regime = "Trending"
    volatility = "Medium"
    trend_strength = 75
    
    composite_score = 0.7
    
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
    
    return render_template('index.html',
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
                          bot_status=bot_status,
                          bot_running=bot_running,
                          account_data=account_data,
                          market_data=market_data)

@app.route('/market')
def market():
    """Trang phân tích thị trường"""
    # Tạo dữ liệu mẫu cho market_data nếu cần
    market_data = {
        'btc_price': sample_prices.get('BTCUSDT', 80000),
        'eth_price': sample_prices.get('ETHUSDT', 2300),
        'bnb_price': sample_prices.get('BNBUSDT', 380),
        'sol_price': sample_prices.get('SOLUSDT', 140),
        'btc_change_24h': random.uniform(-5, 5),
        'eth_change_24h': random.uniform(-7, 7),
        'bnb_change_24h': random.uniform(-4, 4),
        'sol_change_24h': random.uniform(-10, 10),
        'sentiment': {
            'value': random.randint(30, 70),
            'state': random.choice(['success', 'danger', 'warning', 'info']),
            'change': random.uniform(-5, 5),
            'trend': 'neutral'
        },
        'market_regime': {
            'BTCUSDT': 'Trending',
            'ETHUSDT': 'Ranging',
            'BNBUSDT': 'Volatile',
            'SOLUSDT': 'Ranging'
        }
    }
    
    return render_template('market.html', market_data=market_data)

@app.route('/strategies')
def strategies():
    """Trang quản lý chiến lược"""
    return render_template('strategies.html')

@app.route('/backtest')
def backtest():
    """Trang backtest"""
    # Lấy danh sách các tệp dữ liệu lịch sử đã tải
    history_files = []
    data_directories = ['test_data', 'real_data', 'data']
    
    # Tìm kiếm trong tất cả các thư mục để xác định các tệp dữ liệu có sẵn
    for directory in data_directories:
        if os.path.exists(directory):
            # Tìm kiếm tệp CSV trong thư mục gốc
            files = [f for f in os.listdir(directory) if f.endswith('.csv')]
            for file in files:
                parts = file.split('_')
                if len(parts) >= 2:
                    symbol = parts[0]
                    # Xử lý trường hợp có '_sample' trong tên tệp
                    if parts[1].endswith('sample.csv'):
                        timeframe = parts[1][:-11]  # Loại bỏ '.sample.csv'
                    else:
                        timeframe = parts[1].replace('.csv', '')
                else:
                    symbol = file.replace('.csv', '')
                    timeframe = '1h'  # Mặc định
                
                history_files.append({
                    'path': os.path.join(directory, file),
                    'symbol': symbol,
                    'timeframe': timeframe
                })
            
            # Tìm kiếm trong các thư mục con theo cặp giao dịch
            subdirectories = [d for d in os.listdir(directory) 
                             if os.path.isdir(os.path.join(directory, d)) 
                             and not d.startswith('.')]
            
            for subdir in subdirectories:
                subdir_path = os.path.join(directory, subdir)
                
                # Kiểm tra nếu là thư mục cặp giao dịch (VD: BTCUSDT, ETHUSDT, v.v.)
                if subdir.endswith('USDT') or subdir in ['1_month', '3_months', '6_months']:
                    subdir_files = [f for f in os.listdir(subdir_path) if f.endswith('.csv')]
                    
                    for file in subdir_files:
                        if subdir.endswith('USDT'):  # Thư mục theo cặp giao dịch
                            symbol = subdir
                            if '_' in file:
                                timeframe = file.split('_')[0]
                            else:
                                timeframe = file.replace('.csv', '')
                        else:  # Thư mục theo thời gian (1_month, 3_months, 6_months)
                            parts = file.split('_')
                            if len(parts) >= 2:
                                symbol = parts[0]
                                timeframe = parts[1].replace('.csv', '').replace('sample', '')
                            else:
                                continue  # Bỏ qua nếu không đúng định dạng
                        
                        history_files.append({
                            'path': os.path.join(subdir_path, file),
                            'symbol': symbol,
                            'timeframe': timeframe
                        })
    
    # Xóa các mục trùng lặp
    seen = set()
    unique_history_files = []
    for file in history_files:
        key = f"{file['symbol']}_{file['timeframe']}"
        if key not in seen:
            seen.add(key)
            unique_history_files.append(file)
    
    # Danh sách các chiến lược có sẵn
    strategies = [
        {"id": "rsi_strategy", "name": "RSI Strategy", "description": "Giao dịch dựa trên chỉ báo RSI"},
        {"id": "macd_strategy", "name": "MACD Strategy", "description": "Giao dịch dựa trên chỉ báo MACD"},
        {"id": "bollinger_strategy", "name": "Bollinger Bands Strategy", "description": "Giao dịch dựa trên dải Bollinger"},
        {"id": "ml_strategy", "name": "ML Strategy", "description": "Giao dịch sử dụng Machine Learning"},
        {"id": "composite_strategy", "name": "Composite Strategy", "description": "Kết hợp nhiều chỉ báo"}
    ]
    
    # Kết quả backtest gần đây (nếu có)
    recent_results = []
    backtest_results_dir = 'backtest_results'
    if os.path.exists(backtest_results_dir):
        result_files = [f for f in os.listdir(backtest_results_dir) if f.endswith('.json')]
        for file in sorted(result_files, reverse=True)[:5]:  # 5 kết quả gần nhất
            try:
                with open(os.path.join(backtest_results_dir, file), 'r') as f:
                    result = json.load(f)
                    recent_results.append({
                        'file': file,
                        'symbol': result.get('symbol', 'Unknown'),
                        'strategy': result.get('strategy', 'Unknown'),
                        'start_date': result.get('start_date', 'Unknown'),
                        'end_date': result.get('end_date', 'Unknown'),
                        'profit_pct': result.get('profit_pct', 0),
                        'win_rate': result.get('win_rate', 0),
                        'total_trades': result.get('total_trades', 0)
                    })
            except Exception as e:
                logger.error(f"Error loading backtest result {file}: {e}")
    
    return render_template('backtest.html', 
                          history_files=unique_history_files,
                          strategies=strategies,
                          recent_results=recent_results)

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
    # Tạo dữ liệu mẫu cho bot_status để tránh lỗi template
    bot_status = {
        'running': False,
        'mode': 'demo',
        'account_type': 'futures',
        'strategy_mode': 'auto'
    }
    return render_template('settings.html', bot_status=bot_status)

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

@app.route('/api/backtest/run', methods=['POST'])
def run_backtest():
    """API thực thi backtest"""
    try:
        # Lấy tham số từ request
        strategy = request.form.get('strategy', 'rsi_strategy')
        symbol = request.form.get('symbol', 'BTCUSDT')
        timeframe = request.form.get('timeframe', '1h')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        initial_balance = float(request.form.get('initial_balance', 10000))
        risk_per_trade = float(request.form.get('risk_per_trade', 1.0))
        leverage = int(request.form.get('leverage', 1))
        optimize_params = request.form.get('optimize_params', 'false').lower() == 'true'
        
        # Lấy tham số chiến lược từ form nếu có
        strategy_params = {}
        for key, value in request.form.items():
            if key not in ['strategy', 'symbol', 'timeframe', 'start_date', 'end_date', 
                         'initial_balance', 'risk_per_trade', 'leverage', 'optimize_params']:
                try:
                    # Cố gắng chuyển đổi giá trị thành số nếu có thể
                    if value.replace('.', '').isdigit():
                        if '.' in value:
                            strategy_params[key] = float(value)
                        else:
                            strategy_params[key] = int(value)
                    elif value.lower() in ['true', 'false']:
                        strategy_params[key] = value.lower() == 'true'
                    else:
                        strategy_params[key] = value
                except:
                    strategy_params[key] = value
        
        # Tạo ID cho backtest này
        backtest_id = f"{strategy}_{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Tạo thư mục kết quả nếu chưa tồn tại
        backtest_results_dir = 'backtest_results'
        if not os.path.exists(backtest_results_dir):
            os.makedirs(backtest_results_dir)
        
        # Tìm kiếm toàn diện file dữ liệu từ tất cả các thư mục
        data_found = False
        data_file = None
        data_directories = ['test_data', 'real_data', 'data']
        
        # Kiểm tra tệp tin trực tiếp
        for directory in data_directories:
            if os.path.exists(directory):
                # Danh sách các định dạng tên file có thể
                potential_files = [
                    f"{symbol}_{timeframe}.csv",
                    f"{symbol}_{timeframe}_sample.csv",
                    f"{symbol.lower()}_{timeframe}.csv",
                    f"{symbol}.csv"
                ]
                for filename in potential_files:
                    full_path = os.path.join(directory, filename)
                    if os.path.exists(full_path):
                        data_file = full_path
                        data_found = True
                        logger.info(f"Tìm thấy file dữ liệu: {full_path}")
                        break
                
                # Kiểm tra trong thư mục con theo cặp giao dịch
                if not data_found and os.path.exists(os.path.join(directory, symbol)):
                    symbol_dir = os.path.join(directory, symbol)
                    potential_files = [
                        f"{timeframe}.csv",
                        f"{symbol}_{timeframe}.csv",
                        f"{symbol}_{timeframe}_sample.csv"
                    ]
                    for filename in potential_files:
                        full_path = os.path.join(symbol_dir, filename)
                        if os.path.exists(full_path):
                            data_file = full_path
                            data_found = True
                            logger.info(f"Tìm thấy file dữ liệu trong thư mục con: {full_path}")
                            break
                
                # Kiểm tra trong thư mục theo thời gian (1_month, 3_months, 6_months)
                time_subdirs = ['1_month', '3_months', '6_months']
                if not data_found:
                    for time_dir in time_subdirs:
                        if os.path.exists(os.path.join(directory, time_dir)):
                            time_path = os.path.join(directory, time_dir)
                            potential_files = [
                                f"{symbol}_{timeframe}.csv",
                                f"{symbol}_{timeframe}_sample.csv"
                            ]
                            for filename in potential_files:
                                full_path = os.path.join(time_path, filename)
                                if os.path.exists(full_path):
                                    data_file = full_path
                                    data_found = True
                                    logger.info(f"Tìm thấy file dữ liệu trong thư mục thời gian: {full_path}")
                                    break
                
                if data_found:
                    break
        
        if not data_found:
            return jsonify({
                "success": False,
                "error": f"Không tìm thấy dữ liệu cho {symbol} với khung thời gian {timeframe}. Vui lòng tải dữ liệu trước."
            })
        
        # Chạy backtest (thực sự sẽ gọi một script Python riêng)
        # Đây là ví dụ, cần thay thế bằng lệnh thực sự để chạy backtest
        backtest_command = f"python comprehensive_backtest.py --strategy {strategy} --symbol {symbol} --timeframe {timeframe}"
        
        if start_date:
            backtest_command += f" --start_date {start_date}"
        if end_date:
            backtest_command += f" --end_date {end_date}"
            
        backtest_command += f" --initial_balance {initial_balance} --risk_percentage {risk_per_trade} --leverage {leverage}"
        
        if optimize_params:
            backtest_command += " --optimize"
            
        backtest_command += f" --output_file {os.path.join(backtest_results_dir, backtest_id + '.json')}"
        
        # Trong môi trường thật, chúng ta sẽ thực thi lệnh và đợi kết quả
        # Ở đây chúng ta mô phỏng kết quả
        logger.info(f"Chạy lệnh backtest: {backtest_command}")
        
        # Mô phỏng kết quả
        total_trades = random.randint(30, 80)
        winning_trades = random.randint(15, total_trades-10)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100
        
        # Tính lợi nhuận
        pnl_percent = random.uniform(-15, 35)
        final_balance = initial_balance * (1 + pnl_percent/100)
        
        # Tạo danh sách giao dịch mẫu
        trades = []
        current_date = datetime.now() - timedelta(days=30)
        balance = initial_balance
        
        for i in range(total_trades):
            is_win = random.random() < (win_rate / 100)
            trade_type = random.choice(["LONG", "SHORT"])
            
            if symbol == "BTCUSDT":
                entry_price = random.uniform(60000, 80000)
            elif symbol == "ETHUSDT":
                entry_price = random.uniform(2000, 3500)
            else:
                entry_price = random.uniform(10, 1000)
                
            pnl_percent_trade = random.uniform(1, 5) if is_win else random.uniform(-5, -1)
            
            if trade_type == "LONG":
                exit_price = entry_price * (1 + pnl_percent_trade/100)
            else:
                exit_price = entry_price * (1 - pnl_percent_trade/100)
                
            quantity = (balance * (risk_per_trade/100)) / (abs(entry_price - exit_price) / entry_price)
            pnl = (exit_price - entry_price) * quantity if trade_type == "LONG" else (entry_price - exit_price) * quantity
            
            entry_time = current_date
            exit_time = entry_time + timedelta(hours=random.randint(2, 24))
            current_date = exit_time + timedelta(hours=random.randint(1, 12))
            
            exit_reason = "take_profit" if is_win else "stop_loss"
            if random.random() < 0.1:  # 10% trường hợp là trailing stop
                exit_reason = "trailing_stop"
            
            trades.append({
                "id": f"trade{i+1}",
                "symbol": symbol,
                "type": trade_type,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": quantity,
                "pnl": pnl,
                "pnl_percent": pnl_percent_trade,
                "entry_time": entry_time.strftime("%Y-%m-%d %H:%M"),
                "exit_time": exit_time.strftime("%Y-%m-%d %H:%M"),
                "exit_reason": exit_reason
            })
            
            balance += pnl
        
        # Tạo kết quả
        backtest_result = {
            "id": backtest_id,
            "strategy": strategy,
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "profit_pct": pnl_percent,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "profit_factor": random.uniform(1.1, 2.5),
            "sharpe_ratio": random.uniform(0.8, 2.5),
            "max_drawdown": random.uniform(5, 25),
            "max_drawdown_amount": initial_balance * (random.uniform(5, 25)/100),
            "trades": trades,
            "parameters": {
                "risk_per_trade": risk_per_trade,
                "leverage": leverage,
                "optimize_params": optimize_params,
                "strategy_params": {
                    # Thêm các tham số của chiến lược
                }
            }
        }
        
        # Lưu kết quả vào file
        result_file = os.path.join(backtest_results_dir, backtest_id + '.json')
        with open(result_file, 'w') as f:
            json.dump(backtest_result, f, indent=4, default=str)
        
        # Trả về kết quả
        return jsonify({
            "success": True,
            "backtest_id": backtest_id,
            "result": backtest_result
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/language', methods=['POST'])
def change_language():
    """Thay đổi ngôn ngữ"""
    language = request.json.get('language')
    if language in ['en', 'vi']:
        session['language'] = language
        return jsonify({"status": "success", "message": "Language changed successfully"})
    return jsonify({"status": "error", "message": "Invalid language"})

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
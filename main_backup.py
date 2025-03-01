#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot Dashboard
"""

import os
import json
import time
import logging
import threading
import schedule
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import pandas as pd

# Thiết lập logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

# Khởi tạo Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SESSION_SECRET", "secret!12345")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Biến toàn cục để theo dõi trạng thái
background_task_started = False

# Đường dẫn đến file trạng thái giao dịch
trading_state_file = "trading_state.json"
multi_coin_config_file = "multi_coin_config.json"

def load_trading_state():
    """Load trading state from file"""
    try:
        if os.path.exists(trading_state_file):
            with open(trading_state_file, "r") as f:
                return json.load(f)
        else:
            return {
                "balance": 10000.0,
                "positions": [],
                "trade_history": [],
                "bot_status": "stopped",
                "last_update": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error loading trading state: {e}")
        return {
            "balance": 10000.0,
            "positions": [],
            "trade_history": [],
            "bot_status": "stopped",
            "last_update": datetime.now().isoformat()
        }

def load_multi_coin_config():
    """Load multi-coin configuration"""
    try:
        if os.path.exists(multi_coin_config_file):
            with open(multi_coin_config_file, "r") as f:
                return json.load(f)
        else:
            return {
                "enabled_coins": ["BTCUSDT", "ETHUSDT"],
                "timeframes": ["1h"],
                "risk_percentage": 1.0,
                "max_positions": 3,
                "check_interval": 300
            }
    except Exception as e:
        logger.error(f"Error loading multi-coin config: {e}")
        return {
            "enabled_coins": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1h"],
            "risk_percentage": 1.0,
            "max_positions": 3,
            "check_interval": 300
        }

@app.route('/')
def index():
    """Trang chủ Dashboard"""
    state = load_trading_state()
    return render_template('dashboard.html', 
                          bot_status=state.get("bot_status", "stopped"),
                          balance=state.get("balance", 10000.0),
                          positions=state.get("positions", []))

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
    state = load_trading_state()
    return render_template('trades.html', 
                          trade_history=state.get("trade_history", []))

@app.route('/settings')
def settings():
    """Trang cài đặt bot"""
    config = load_multi_coin_config()
    return render_template('settings.html', config=config)

@app.route('/report')
def report():
    """Trang báo cáo giao dịch"""
    return render_template('report.html')

@app.route('/api/bot/control', methods=['POST'])
def bot_control():
    """Điều khiển bot (start/stop/restart)"""
    action = request.json.get('action')
    
    state = load_trading_state()
    
    if action == 'start':
        state["bot_status"] = "running"
    elif action == 'stop':
        state["bot_status"] = "stopped"
    elif action == 'restart':
        state["bot_status"] = "running"
    
    state["last_update"] = datetime.now().isoformat()
    
    try:
        with open(trading_state_file, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving trading state: {e}")
    
    # Emit socket event to update all clients
    socketio.emit('bot_status_changed', {'status': state["bot_status"]})
    
    return jsonify({"status": state["bot_status"]})

@app.route('/api/positions/close', methods=['POST'])
def close_position():
    """Đóng một vị thế"""
    symbol = request.json.get('symbol')
    
    state = load_trading_state()
    positions = state.get("positions", [])
    
    # Find position to close
    position_idx = None
    for idx, pos in enumerate(positions):
        if pos.get("symbol") == symbol:
            position_idx = idx
            break
    
    if position_idx is not None:
        # Get position
        position = positions[position_idx]
        
        # Create closed trade record
        trade = {
            "symbol": position.get("symbol"),
            "type": position.get("type"),
            "entry_price": position.get("entry_price"),
            "exit_price": position.get("current_price"),
            "quantity": position.get("quantity"),
            "pnl": position.get("pnl"),
            "pnl_pct": position.get("pnl_pct"),
            "entry_time": position.get("entry_time"),
            "exit_time": datetime.now().isoformat(),
            "exit_reason": "Manually closed by user"
        }
        
        # Update state
        state["trade_history"].append(trade)
        state["positions"].pop(position_idx)
        state["balance"] += position.get("pnl", 0)
        state["last_update"] = datetime.now().isoformat()
        
        try:
            with open(trading_state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trading state: {e}")
        
        # Emit socket events to update all clients
        socketio.emit('position_closed', {'symbol': symbol})
        socketio.emit('account_update', {'balance': state["balance"]})
        
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Position not found"})

@app.route('/api/bot/status')
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    state = load_trading_state()
    return jsonify({
        "status": state.get("bot_status", "stopped"),
        "last_update": state.get("last_update", "")
    })

@app.route('/api/account')
def get_account():
    """Lấy dữ liệu tài khoản"""
    state = load_trading_state()
    return jsonify({
        "balance": state.get("balance", 10000.0),
        "positions": state.get("positions", []),
        "trade_history": state.get("trade_history", [])
    })

@app.route('/api/signals')
def get_signals():
    """Lấy tín hiệu giao dịch gần đây"""
    # Mô phỏng dữ liệu tín hiệu
    signals = []
    coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT"]
    
    for coin in coins:
        signal_strength = 0  # -1 to 1
        signal_type = "neutral"
        
        # Randomly set signals for demo purpose
        import random
        r = random.random()
        if r > 0.7:
            signal_strength = random.uniform(0.3, 1.0)
            signal_type = "buy"
        elif r < 0.3:
            signal_strength = random.uniform(-1.0, -0.3)
            signal_type = "sell"
        
        signals.append({
            "symbol": coin,
            "signal": signal_type,
            "strength": abs(signal_strength),
            "timestamp": datetime.now().isoformat()
        })
    
    return jsonify(signals)

@app.route('/api/market')
def get_market():
    """Lấy dữ liệu thị trường"""
    # Mô phỏng dữ liệu thị trường
    market_data = []
    coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT"]
    base_prices = {
        "BTCUSDT": 55000,
        "ETHUSDT": 3200,
        "BNBUSDT": 580,
        "SOLUSDT": 120,
        "XRPUSDT": 0.52,
        "AVAXUSDT": 35,
        "DOGEUSDT": 0.12,
        "ADAUSDT": 0.64,
        "DOTUSDT": 7.50
    }
    
    import random
    for coin in coins:
        base_price = base_prices.get(coin, 100)
        # Add small random variation
        price = base_price * (1 + random.uniform(-0.01, 0.01))
        change_24h = random.uniform(-5, 5)
        
        market_data.append({
            "symbol": coin,
            "price": price,
            "volume_24h": base_price * 10000 * random.uniform(0.8, 1.2),
            "change_24h": change_24h,
            "high_24h": price * (1 + abs(change_24h)/100 * random.uniform(1, 1.5)),
            "low_24h": price * (1 - abs(change_24h)/100 * random.uniform(1, 1.5)),
        })
    
    return jsonify(market_data)

@app.route('/api/coins')
def get_coins():
    """Lấy danh sách coin đang giao dịch"""
    config = load_multi_coin_config()
    return jsonify({
        "enabled_coins": config.get("enabled_coins", ["BTCUSDT", "ETHUSDT"]),
        "available_coins": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT"]
    })

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối"""
    logger.info("Client connected")
    global background_task_started
    if not background_task_started:
        background_task_started = True
        socketio.start_background_task(start_background_tasks)

@socketio.on('disconnect')
def handle_disconnect():
    """Xử lý khi client ngắt kết nối"""
    logger.info("Client disconnected")

def simulate_price_updates():
    """Giả lập cập nhật giá thời gian thực"""
    coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT"]
    base_prices = {
        "BTCUSDT": 55000,
        "ETHUSDT": 3200,
        "BNBUSDT": 580,
        "SOLUSDT": 120,
        "XRPUSDT": 0.52,
        "AVAXUSDT": 35,
        "DOGEUSDT": 0.12,
        "ADAUSDT": 0.64,
        "DOTUSDT": 7.50
    }
    
    while True:
        import random
        for coin in coins:
            base_price = base_prices.get(coin, 100)
            # Add small random variation
            price = base_price * (1 + random.uniform(-0.005, 0.005))
            
            # Update base price with small drift
            base_prices[coin] = base_price * (1 + random.uniform(-0.001, 0.001))
            
            socketio.emit('price_update', {
                'symbol': coin,
                'price': price,
                'timestamp': datetime.now().isoformat()
            })
        
        # Wait 2 seconds
        socketio.sleep(2)

def simulate_sentiment_updates():
    """Giả lập cập nhật tâm lý thị trường"""
    while True:
        import random
        sentiment = random.uniform(0, 100)
        sentiment_label = "Extreme Fear"
        
        if sentiment < 25:
            sentiment_label = "Extreme Fear"
        elif sentiment < 45:
            sentiment_label = "Fear"
        elif sentiment < 55:
            sentiment_label = "Neutral"
        elif sentiment < 75:
            sentiment_label = "Greed"
        else:
            sentiment_label = "Extreme Greed"
        
        socketio.emit('sentiment_update', {
            'value': sentiment,
            'label': sentiment_label,
            'timestamp': datetime.now().isoformat()
        })
        
        # Wait 60 seconds
        socketio.sleep(60)

def simulate_account_updates():
    """Giả lập cập nhật tài khoản và vị thế"""
    while True:
        state = load_trading_state()
        
        if state.get("bot_status") == "running":
            # Update positions if any
            positions = state.get("positions", [])
            
            if positions:
                import random
                updated = False
                
                for position in positions:
                    # Add random price movement
                    current_price = position.get("current_price", position.get("entry_price", 0))
                    price_change = random.uniform(-0.5, 0.5) / 100  # +/-0.5%
                    new_price = current_price * (1 + price_change)
                    
                    # Update position
                    position["current_price"] = new_price
                    
                    # Calculate PnL
                    entry_price = position.get("entry_price", 0)
                    quantity = position.get("quantity", 0)
                    
                    if position.get("type") == "LONG":
                        pnl = (new_price - entry_price) * quantity
                        pnl_pct = (new_price / entry_price - 1) * 100
                    else:  # SHORT
                        pnl = (entry_price - new_price) * quantity
                        pnl_pct = (entry_price / new_price - 1) * 100
                    
                    position["pnl"] = pnl
                    position["pnl_pct"] = pnl_pct
                    
                    # Random chance to close position
                    if random.random() < 0.05:  # 5% chance
                        # Create closed trade record
                        trade = {
                            "symbol": position.get("symbol"),
                            "type": position.get("type"),
                            "entry_price": position.get("entry_price"),
                            "exit_price": new_price,
                            "quantity": quantity,
                            "pnl": pnl,
                            "pnl_pct": pnl_pct,
                            "entry_time": position.get("entry_time"),
                            "exit_time": datetime.now().isoformat(),
                            "exit_reason": "Take profit" if pnl > 0 else "Stop loss"
                        }
                        
                        # Update trade history
                        state["trade_history"].append(trade)
                        
                        # Update balance
                        state["balance"] += pnl
                        
                        # Remove position
                        positions.remove(position)
                        
                        # Emit event
                        socketio.emit('position_closed', {'symbol': position.get("symbol")})
                        
                        updated = True
                
                # Random chance to open new position
                if len(positions) < 3 and random.random() < 0.1:  # 10% chance
                    coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT"]
                    existing_symbols = [p.get("symbol") for p in positions]
                    available_coins = [c for c in coins if c not in existing_symbols]
                    
                    if available_coins:
                        symbol = random.choice(available_coins)
                        pos_type = "LONG" if random.random() > 0.5 else "SHORT"
                        
                        # Get base price
                        base_prices = {
                            "BTCUSDT": 55000,
                            "ETHUSDT": 3200,
                            "BNBUSDT": 580,
                            "SOLUSDT": 120,
                            "XRPUSDT": 0.52,
                            "AVAXUSDT": 35,
                            "DOGEUSDT": 0.12,
                            "ADAUSDT": 0.64,
                            "DOTUSDT": 7.50
                        }
                        price = base_prices.get(symbol, 100)
                        
                        # Calculate quantity
                        risk_amount = state.get("balance") * 0.02  # 2% risk
                        quantity = risk_amount / price
                        
                        # Create position
                        new_position = {
                            "symbol": symbol,
                            "type": pos_type,
                            "entry_price": price,
                            "current_price": price,
                            "quantity": quantity,
                            "pnl": 0,
                            "pnl_pct": 0,
                            "entry_time": datetime.now().isoformat()
                        }
                        
                        # Add to positions
                        positions.append(new_position)
                        
                        # Emit event
                        socketio.emit('position_opened', new_position)
                        
                        updated = True
                
                if updated:
                    # Save updated state
                    state["positions"] = positions
                    state["last_update"] = datetime.now().isoformat()
                    
                    try:
                        with open(trading_state_file, "w") as f:
                            json.dump(state, f, indent=2)
                    except Exception as e:
                        logger.error(f"Error saving trading state: {e}")
                    
                    # Emit account update
                    socketio.emit('account_update', {
                        'balance': state.get("balance"),
                        'positions': positions
                    })
        
        # Wait 10 seconds
        socketio.sleep(10)

def check_and_restart_bot():
    """Kiểm tra và khởi động lại bot nếu cần"""
    while True:
        # TODO: Implement real bot monitoring
        socketio.sleep(300)  # Check every 5 minutes

def generate_daily_report():
    """Tạo báo cáo hàng ngày theo lịch"""
    from daily_report import main as generate_report
    generate_report()
    
    # Emit event to notify clients
    socketio.emit('report_generated', {
        'type': 'daily',
        'timestamp': datetime.now().isoformat()
    })

def start_background_tasks():
    """Khởi chạy các tác vụ nền khi có request đầu tiên"""
    logger.info("Background tasks started")
    
    # Lên lịch tác vụ
    schedule.every().day.at("00:00").do(generate_daily_report)
    
    # Khởi chạy các tác vụ giả lập
    socketio.start_background_task(simulate_price_updates)
    socketio.start_background_task(simulate_sentiment_updates)
    socketio.start_background_task(simulate_account_updates)
    socketio.start_background_task(check_and_restart_bot)
    
    # Kiểm tra và chạy các tác vụ theo lịch
    while True:
        schedule.run_pending()
        socketio.sleep(1)

if __name__ == '__main__':
    # Tạo thư mục cần thiết
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    # Khởi động SocketIO
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
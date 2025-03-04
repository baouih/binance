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
import json
import glob
import random
import uuid

# Thêm module Telegram Notifier
from telegram_notifier import TelegramNotifier

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "binance_trader_bot_secret")

# Khởi tạo SocketIO với CORS và async mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=60, ping_interval=25)

# Đường dẫn đến các file cấu hình
ACCOUNT_CONFIG_PATH = 'account_config.json'
BOT_CONFIG_PATH = 'bot_config.json'
TELEGRAM_CONFIG_PATH = 'telegram_config.json'

# Trạng thái bot
bot_status = {
    'running': False,
    'status': 'stopped',
    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'uptime': 0,
    'version': '1.0.0',
    'mode': 'demo',  # demo, testnet, live
    'last_signal': None,
    'balance': 10000.0,
    'account_type': 'futures'
}

# Cấu hình Telegram
telegram_config = {
    'enabled': False,
    'bot_token': '',
    'chat_id': '',
    'min_interval': 5,  # Khoảng thời gian tối thiểu giữa các thông báo (phút)
    'last_notification': None
}

# Khởi tạo Telegram Notifier
telegram_notifier = TelegramNotifier(
    token=telegram_config.get('bot_token', ''),
    chat_id=telegram_config.get('chat_id', '')
)

# Dữ liệu tạm để hiển thị
fake_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT', 'XRPUSDT', 'DOTUSDT']
fake_prices = {
    'BTCUSDT': 36500.0,
    'ETHUSDT': 2400.0,
    'BNBUSDT': 320.0,
    'ADAUSDT': 0.45,
    'DOGEUSDT': 0.12,
    'XRPUSDT': 0.65,
    'DOTUSDT': 17.8
}

# Lưu trữ thông báo hệ thống
system_messages = []

# Dữ liệu hiệu suất
performance_data = {
    'daily': {
        'win_rate': 62.5,
        'profit_loss': 215.75,
        'trades': 8,
        'pnl_percent': 2.15
    },
    'weekly': {
        'win_rate': 58.3,
        'profit_loss': 843.20,
        'trades': 36,
        'pnl_percent': 8.43
    },
    'monthly': {
        'win_rate': 56.8,
        'profit_loss': 2750.50,
        'trades': 125,
        'pnl_percent': 27.51
    },
    'all_time': {
        'win_rate': 54.5,
        'profit_loss': 9876.30,
        'trades': 475,
        'pnl_percent': 98.76
    }
}

# Dữ liệu mẫu vị thế
positions = []

# Dữ liệu mẫu giao dịch
trades = []

# Số dư ban đầu và lịch sử hiệu suất
initial_balances = {
    'daily': 10000.0,
    'weekly': 10000.0,
    'monthly': 10000.0,
    'all_time': 10000.0
}

# Danh sách tín hiệu
signals = []

# Dữ liệu thị trường
market_data = {}

# Hàm cập nhật dữ liệu giả
def update_fake_data():
    global fake_prices, market_data, performance_data, bot_status
    
    # Cập nhật giá
    for symbol in fake_symbols:
        change = random.uniform(-0.5, 0.5)
        fake_prices[symbol] *= (1 + change / 100)
        
        if symbol not in market_data:
            market_data[symbol] = {
                'symbol': symbol,
                'price': fake_prices[symbol],
                'change_24h': 0,
                'volume': 0,
                'high_24h': fake_prices[symbol],
                'low_24h': fake_prices[symbol],
                'indicators': {}
            }
        else:
            market_data[symbol]['price'] = fake_prices[symbol]
            market_data[symbol]['change_24h'] = random.uniform(-5, 5)
            market_data[symbol]['volume'] = random.uniform(100000, 10000000)
            market_data[symbol]['high_24h'] = fake_prices[symbol] * (1 + random.uniform(0.5, 2) / 100)
            market_data[symbol]['low_24h'] = fake_prices[symbol] * (1 - random.uniform(0.5, 2) / 100)
            
            # Thêm các chỉ báo kỹ thuật
            market_data[symbol]['indicators'] = {
                'rsi': random.uniform(30, 70),
                'macd': random.uniform(-10, 10),
                'ema50': fake_prices[symbol] * (1 + random.uniform(-2, 2) / 100),
                'ema200': fake_prices[symbol] * (1 + random.uniform(-4, 4) / 100),
                'bb_upper': fake_prices[symbol] * (1 + random.uniform(1, 3) / 100),
                'bb_lower': fake_prices[symbol] * (1 - random.uniform(1, 3) / 100)
            }
    
    # Cập nhật thời gian chạy của bot nếu đang hoạt động
    if bot_status['running']:
        bot_status['uptime'] += 10  # Tăng 10 giây
    
    # Cập nhật số dư nếu có vị thế đang mở
    if positions and bot_status['running']:
        for pos in positions:
            current_price = fake_prices[pos['symbol']]
            price_diff = current_price - pos['entry_price']
            
            if pos['side'] == 'BUY':
                pos['current_price'] = current_price
                pos['unrealized_pnl'] = price_diff * pos['quantity']
                pos['unrealized_pnl_percent'] = (price_diff / pos['entry_price']) * 100
            else:  # SELL
                pos['current_price'] = current_price
                pos['unrealized_pnl'] = -price_diff * pos['quantity']
                pos['unrealized_pnl_percent'] = (-price_diff / pos['entry_price']) * 100
                
            # Cập nhật lệnh stop loss và take profit
            if pos['side'] == 'BUY':
                if current_price <= pos['stop_loss']:
                    close_position(pos['id'], current_price, 'Stop Loss')
                elif current_price >= pos['take_profit']:
                    close_position(pos['id'], current_price, 'Take Profit')
            else:  # SELL
                if current_price >= pos['stop_loss']:
                    close_position(pos['id'], current_price, 'Stop Loss')
                elif current_price <= pos['take_profit']:
                    close_position(pos['id'], current_price, 'Take Profit')
        
        # Cập nhật số dư
        bot_status['balance'] = get_current_balance()
    
    # Cập nhật hiệu suất
    if bot_status['running'] and random.random() < 0.1:  # 10% cơ hội cập nhật
        performance_data['daily']['profit_loss'] += random.uniform(-5, 15)
        performance_data['daily']['pnl_percent'] = (performance_data['daily']['profit_loss'] / initial_balances['daily']) * 100
        
        performance_data['weekly']['profit_loss'] += random.uniform(-10, 30)
        performance_data['weekly']['pnl_percent'] = (performance_data['weekly']['profit_loss'] / initial_balances['weekly']) * 100
        
        performance_data['monthly']['profit_loss'] += random.uniform(-20, 60)
        performance_data['monthly']['pnl_percent'] = (performance_data['monthly']['profit_loss'] / initial_balances['monthly']) * 100
        
        performance_data['all_time']['profit_loss'] += random.uniform(-50, 150)
        performance_data['all_time']['pnl_percent'] = (performance_data['all_time']['profit_loss'] / initial_balances['all_time']) * 100

# Hàm tạo tín hiệu giả
def generate_fake_signal():
    global signals
    if bot_status['running'] and random.random() < 0.2:  # 20% cơ hội tạo tín hiệu
        symbol = random.choice(fake_symbols)
        signal_type = random.choice(['BUY', 'SELL'])
        signal_strength = random.uniform(0.1, 0.9)
        confidence = random.uniform(60, 95)
        strategy = random.choice(['RSI', 'MACD Cross', 'EMA Cross', 'Bollinger Bands', 'Support/Resistance'])
        
        signal = {
            'id': str(uuid.uuid4())[:8],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'type': signal_type,
            'price': fake_prices[symbol],
            'strength': signal_strength,
            'confidence': confidence,
            'strategy': strategy,
            'executed': False
        }
        
        signals.append(signal)
        if len(signals) > 50:
            signals.pop(0)
        
        # Gửi thông báo tín hiệu qua SocketIO
        socketio.emit('new_signal', signal)
        
        # Thêm thông báo
        add_system_message(f"Đã phát hiện tín hiệu {signal_type} cho {symbol} với độ tin cậy {confidence:.1f}%")
        
        # Mở vị thế tự động nếu tín hiệu đủ mạnh
        if signal_strength > 0.5 and confidence > 75 and bot_status['running']:
            open_position(signal)

import random
import uuid

# Hàm mở vị thế mới
def open_position(signal):
    global positions, trades
    
    # Kiểm tra xem đã có vị thế cho symbol này chưa
    for pos in positions:
        if pos['symbol'] == signal['symbol']:
            # Đã có vị thế, có thể thêm logic để đóng vị thế cũ và mở vị thế mới
            return
    
    # Tính toán size
    risk_per_trade = 0.02  # 2% số dư
    stop_loss_percent = 0.02  # 2% giá
    take_profit_percent = 0.04  # 4% giá
    
    entry_price = signal['price']
    
    if signal['type'] == 'BUY':
        stop_loss = entry_price * (1 - stop_loss_percent)
        take_profit = entry_price * (1 + take_profit_percent)
    else:  # SELL
        stop_loss = entry_price * (1 + stop_loss_percent)
        take_profit = entry_price * (1 - take_profit_percent)
    
    # Tính số lượng dựa trên rủi ro
    risk_amount = bot_status['balance'] * risk_per_trade
    quantity = risk_amount / (entry_price * stop_loss_percent)
    
    # Tạo ID duy nhất cho vị thế
    position_id = str(uuid.uuid4())[:8]
    
    # Tạo vị thế mới
    position = {
        'id': position_id,
        'symbol': signal['symbol'],
        'side': signal['type'],
        'entry_price': entry_price,
        'current_price': entry_price,
        'quantity': quantity,
        'leverage': 1,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'unrealized_pnl': 0,
        'unrealized_pnl_percent': 0,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'age': 0,  # Tuổi vị thế tính bằng giây
        'signal_id': signal['id'],
        'strategy': signal['strategy']
    }
    
    positions.append(position)
    
    # Đánh dấu tín hiệu đã được thực thi
    for s in signals:
        if s['id'] == signal['id']:
            s['executed'] = True
    
    # Thêm thông báo
    add_system_message(f"Đã mở vị thế {signal['type']} cho {signal['symbol']} tại giá {entry_price:.2f}")
    
    # Gửi thông báo qua Telegram
    if telegram_config['enabled']:
        now = datetime.now()
        last_notification = telegram_config.get('last_notification')
        
        # Kiểm tra khoảng thời gian tối thiểu giữa các thông báo
        if not last_notification or (now - last_notification).total_seconds() / 60 >= telegram_config['min_interval']:
            message = f"🔔 *Vị thế mới đã được mở*\n" \
                     f"Symbol: `{signal['symbol']}`\n" \
                     f"Loại: `{signal['type']}`\n" \
                     f"Giá vào: `{entry_price:.2f}`\n" \
                     f"Số lượng: `{quantity:.4f}`\n" \
                     f"Stop Loss: `{stop_loss:.2f}`\n" \
                     f"Take Profit: `{take_profit:.2f}`\n" \
                     f"Thời gian: `{position['timestamp']}`"
            
            telegram_notifier.send_message(message)
            telegram_config['last_notification'] = now
    
    return position_id

# Hàm đóng vị thế
def close_position(position_id, exit_price=None, reason='Manual Close'):
    global positions, trades
    
    # Tìm vị thế cần đóng
    position_index = -1
    for i, pos in enumerate(positions):
        if pos['id'] == position_id:
            position_index = i
            break
    
    if position_index == -1:
        return False
    
    position = positions[position_index]
    
    # Sử dụng giá hiện tại nếu không cung cấp giá thoát
    if exit_price is None:
        exit_price = fake_prices[position['symbol']]
    
    # Tính P/L
    if position['side'] == 'BUY':
        pnl = (exit_price - position['entry_price']) * position['quantity']
        pnl_percent = ((exit_price - position['entry_price']) / position['entry_price']) * 100
    else:  # SELL
        pnl = (position['entry_price'] - exit_price) * position['quantity']
        pnl_percent = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
    
    # Tạo giao dịch đã hoàn thành
    trade = {
        'id': position['id'],
        'symbol': position['symbol'],
        'side': position['side'],
        'entry_price': position['entry_price'],
        'exit_price': exit_price,
        'quantity': position['quantity'],
        'pnl': pnl,
        'pnl_percent': pnl_percent,
        'entry_time': position['timestamp'],
        'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'duration': position['age'],  # Thời gian giữ vị thế
        'strategy': position['strategy'],
        'reason': reason,
        'status': 'profit' if pnl > 0 else 'loss'
    }
    
    trades.append(trade)
    if len(trades) > 100:
        trades.pop(0)
    
    # Xoá vị thế
    positions.pop(position_index)
    
    # Cập nhật số dư
    bot_status['balance'] += pnl
    
    # Thêm thông báo
    result_text = "lãi" if pnl > 0 else "lỗ"
    add_system_message(f"Đã đóng vị thế {trade['side']} cho {trade['symbol']} với {result_text} {pnl:.2f} ({pnl_percent:.2f}%) - Lý do: {reason}")
    
    # Gửi thông báo qua Telegram
    if telegram_config['enabled'] and (pnl_percent > 2 or pnl_percent < -2):  # Chỉ gửi khi P/L > 2% hoặc < -2%
        now = datetime.now()
        last_notification = telegram_config.get('last_notification')
        
        # Kiểm tra khoảng thời gian tối thiểu giữa các thông báo
        if not last_notification or (now - last_notification).total_seconds() / 60 >= telegram_config['min_interval']:
            emoji = "🟢" if pnl > 0 else "🔴"
            message = f"{emoji} *Vị thế đã đóng*\n" \
                     f"Symbol: `{trade['symbol']}`\n" \
                     f"Loại: `{trade['side']}`\n" \
                     f"Giá vào: `{trade['entry_price']:.2f}`\n" \
                     f"Giá ra: `{trade['exit_price']:.2f}`\n" \
                     f"P/L: `{pnl:.2f} ({pnl_percent:.2f}%)`\n" \
                     f"Lý do: `{reason}`\n" \
                     f"Thời gian: `{trade['exit_time']}`"
            
            telegram_notifier.send_message(message)
            telegram_config['last_notification'] = now
    
    return True

# Lấy số dư hiện tại (bao gồm cả unrealized P/L)
def get_current_balance():
    balance = bot_status['balance']
    
    # Cộng thêm unrealized P/L từ các vị thế đang mở
    for pos in positions:
        balance += pos['unrealized_pnl']
    
    return balance

# Thêm thông báo hệ thống
def add_system_message(message):
    global system_messages
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    system_messages.append({
        'id': str(uuid.uuid4())[:8],
        'timestamp': timestamp,
        'message': message
    })
    
    # Giới hạn số lượng thông báo
    if len(system_messages) > 100:
        system_messages.pop(0)
    
    # Gửi thông báo qua SocketIO
    socketio.emit('system_message', {
        'timestamp': timestamp,
        'message': message
    })
    
    # Log thông báo
    logger.debug(f"System message: {message}")

# Tải cấu hình từ file
def load_config():
    global bot_status, telegram_config, telegram_notifier
    
    # Tải cấu hình bot
    try:
        if os.path.exists(BOT_CONFIG_PATH):
            with open(BOT_CONFIG_PATH, 'r') as f:
                bot_config = json.load(f)
                # Cập nhật các giá trị từ cấu hình
                if 'mode' in bot_config:
                    bot_status['mode'] = bot_config['mode']
                if 'account_type' in bot_config:
                    bot_status['account_type'] = bot_config['account_type']
                if 'balance' in bot_config:
                    bot_status['balance'] = bot_config['balance']
                
                logger.info(f"Đã tải cấu hình bot từ {BOT_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình bot: {e}")
    
    # Tải cấu hình Telegram
    try:
        if os.path.exists(TELEGRAM_CONFIG_PATH):
            with open(TELEGRAM_CONFIG_PATH, 'r') as f:
                tg_config = json.load(f)
                # Cập nhật cấu hình Telegram
                if 'enabled' in tg_config:
                    telegram_config['enabled'] = tg_config['enabled']
                if 'bot_token' in tg_config:
                    telegram_config['bot_token'] = tg_config['bot_token']
                if 'chat_id' in tg_config:
                    telegram_config['chat_id'] = tg_config['chat_id']
                if 'min_interval' in tg_config:
                    telegram_config['min_interval'] = tg_config['min_interval']
                
                # Cập nhật notifier
                telegram_notifier.set_token(telegram_config['bot_token'])
                telegram_notifier.set_chat_id(telegram_config['chat_id'])
                
                logger.info(f"Đã tải cấu hình Telegram từ {TELEGRAM_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình Telegram: {e}")

# Lưu cấu hình vào file
def save_config():
    global bot_status, telegram_config
    
    # Lưu cấu hình bot
    try:
        bot_config = {
            'mode': bot_status['mode'],
            'account_type': bot_status['account_type'],
            'balance': bot_status['balance']
        }
        
        with open(BOT_CONFIG_PATH, 'w') as f:
            json.dump(bot_config, f, indent=2)
            
        logger.info(f"Đã lưu cấu hình bot vào {BOT_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình bot: {e}")
    
    # Lưu cấu hình Telegram
    try:
        tg_config = {
            'enabled': telegram_config['enabled'],
            'bot_token': telegram_config['bot_token'],
            'chat_id': telegram_config['chat_id'],
            'min_interval': telegram_config['min_interval']
        }
        
        with open(TELEGRAM_CONFIG_PATH, 'w') as f:
            json.dump(tg_config, f, indent=2)
            
        logger.info(f"Đã lưu cấu hình Telegram vào {TELEGRAM_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình Telegram: {e}")

# Tạo dữ liệu giả ban đầu
import random

def generate_initial_fake_data():
    global positions, trades
    
    # Tạo một số vị thế mẫu
    for i in range(3):
        symbol = random.choice(fake_symbols)
        side = random.choice(['BUY', 'SELL'])
        entry_price = fake_prices[symbol]
        quantity = random.uniform(0.01, 0.5)
        leverage = random.choice([1, 2, 3, 5, 10])
        
        stop_loss_percent = random.uniform(0.01, 0.03)
        take_profit_percent = random.uniform(0.02, 0.06)
        
        if side == 'BUY':
            stop_loss = entry_price * (1 - stop_loss_percent)
            take_profit = entry_price * (1 + take_profit_percent)
        else:  # SELL
            stop_loss = entry_price * (1 + stop_loss_percent)
            take_profit = entry_price * (1 - take_profit_percent)
        
        position = {
            'id': str(uuid.uuid4())[:8],
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'current_price': entry_price,
            'quantity': quantity,
            'leverage': leverage,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'unrealized_pnl': 0,
            'unrealized_pnl_percent': 0,
            'timestamp': (datetime.now() - timedelta(hours=random.randint(1, 24))).strftime('%Y-%m-%d %H:%M:%S'),
            'age': random.randint(3600, 86400),  # 1 giờ đến 1 ngày
            'signal_id': str(uuid.uuid4())[:8],
            'strategy': random.choice(['RSI', 'MACD Cross', 'EMA Cross', 'Bollinger Bands', 'Support/Resistance'])
        }
        
        positions.append(position)
    
    # Tạo một số giao dịch đã hoàn thành
    for i in range(20):
        symbol = random.choice(fake_symbols)
        side = random.choice(['BUY', 'SELL'])
        entry_price = fake_prices[symbol] * (1 + random.uniform(-0.1, 0.1))
        exit_price = entry_price * (1 + random.uniform(-0.05, 0.05))
        quantity = random.uniform(0.01, 0.5)
        
        if side == 'BUY':
            pnl = (exit_price - entry_price) * quantity
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:  # SELL
            pnl = (entry_price - exit_price) * quantity
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        days_ago = random.randint(1, 30)
        hours_ago = random.randint(1, 24)
        
        entry_time = (datetime.now() - timedelta(days=days_ago, hours=hours_ago)).strftime('%Y-%m-%d %H:%M:%S')
        exit_time = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
        
        duration = hours_ago * 3600
        
        trade = {
            'id': str(uuid.uuid4())[:8],
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'duration': duration,
            'strategy': random.choice(['RSI', 'MACD Cross', 'EMA Cross', 'Bollinger Bands', 'Support/Resistance']),
            'reason': random.choice(['Take Profit', 'Stop Loss', 'Manual Close', 'Signal Reversal']),
            'status': 'profit' if pnl > 0 else 'loss'
        }
        
        trades.append(trade)

# Background task để cập nhật dữ liệu
def background_tasks():
    # Tải cấu hình
    load_config()
    
    # Tạo dữ liệu mẫu
    generate_initial_fake_data()
    
    # Thêm thông báo khởi động
    add_system_message("Bot đã khởi động thành công!")
    
    # Cập nhật số dư ban đầu
    update_initial_balances()
    
    # Đặt lịch cho các nhiệm vụ hàng ngày
    schedule_daily_tasks()
    
    # Chạy các tác vụ nền
    while True:
        try:
            update_fake_data()
            generate_fake_signal()
            
            # Cập nhật tuổi của các vị thế
            for pos in positions:
                pos['age'] += 10  # Tăng 10 giây
            
            # Gửi dữ liệu cập nhật qua SocketIO
            socketio.emit('market_update', {
                'prices': fake_prices,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            socketio.emit('bot_status_update', bot_status)
            
            # Cập nhật vị thế
            socketio.emit('positions_update', positions)
            
            # Gửi P/L nếu có vị thế đang mở
            if positions:
                total_pnl = sum(pos['unrealized_pnl'] for pos in positions)
                socketio.emit('pnl_update', {
                    'total_pnl': total_pnl,
                    'total_pnl_percent': (total_pnl / bot_status['balance']) * 100,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # Gửi hiệu suất
            socketio.emit('performance_update', performance_data)
            
        except Exception as e:
            logger.error(f"Lỗi trong tác vụ nền: {e}")
        
        time.sleep(10)  # Cập nhật mỗi 10 giây

# Cập nhật số dư ban đầu
def update_initial_balances():
    global initial_balances
    
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Đặt số dư đầu ngày
    initial_balances['daily'] = bot_status['balance']
    logger.info(f"Cập nhật số dư đầu ngày: {initial_balances['daily']}")
    
    # Đặt số dư đầu tuần (thứ 2)
    if now.weekday() == 0:  # 0 là thứ 2
        initial_balances['weekly'] = bot_status['balance']
        logger.info(f"Cập nhật số dư đầu tuần: {initial_balances['weekly']}")
    
    # Đặt số dư đầu tháng (ngày đầu tiên của tháng)
    if now.day == 1:
        initial_balances['monthly'] = bot_status['balance']
        logger.info(f"Cập nhật số dư đầu tháng: {initial_balances['monthly']}")

# Thiết lập các công việc lịch trình theo thời gian
def schedule_daily_tasks():
    # Cập nhật số dư đầu ngày mỗi ngày
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    time_to_midnight = (midnight - now).total_seconds()
    
    # Đặt lịch cập nhật vào nửa đêm 
    threading.Timer(time_to_midnight, lambda: update_initial_balance('daily')).start()
    
    # Kiểm tra nếu là thứ 2, cập nhật tuần mới
    if now.weekday() == 0 and now.hour == 0:
        update_initial_balance('weekly')
    
    # Kiểm tra nếu là ngày đầu tháng, cập nhật tháng mới
    if now.day == 1 and now.hour == 0:
        update_initial_balance('monthly')

def update_initial_balance(period):
    global initial_balances
    initial_balances[period] = bot_status['balance']
    logger.info(f"Cập nhật số dư đầu {period}: {initial_balances[period]}")

def check_month_start():
    now = datetime.now()
    if now.day == 1:
        update_initial_balance('monthly')

# Các API endpoint
@app.route('/')
def index():
    # Tạo dữ liệu account_data và market_data để truyền vào template
    account_data = {
        'balance': bot_status['balance'],
        'available': bot_status['balance'],
        'positions': positions,
        'change_24h': random.uniform(-5, 5),
        'change_7d': random.uniform(-10, 15),
        'total_profit': random.uniform(-500, 1500),
        'total_profit_percent': random.uniform(-5, 15),
        'unrealized_pnl': sum(p.get('unrealized_pnl', 0) for p in positions) if positions else 0
    }
    
    market_data = {
        'btc_price': fake_prices.get('BTCUSDT', 0),
        'eth_price': fake_prices.get('ETHUSDT', 0),
        'sol_price': fake_prices.get('SOLUSDT', 25.0),
        'bnb_price': fake_prices.get('BNBUSDT', 0),
        'btc_change_24h': random.uniform(-5, 5),
        'eth_change_24h': random.uniform(-5, 5),
        'market_mode': random.choice(['Uptrend', 'Downtrend', 'Sideways']),
        'market_strength': random.uniform(30, 80),
        'volatility_level': random.choice(['Low', 'Medium', 'High']),
        'volatility_value': random.uniform(20, 70)
    }
    
    # Dữ liệu chiến lược
    strategy_stats = {
        'win_rate': random.uniform(50, 70),
        'profit_factor': random.uniform(1.2, 2.5),
        'expectancy': random.uniform(0.1, 0.5),
        'avg_win': random.uniform(50, 150),
        'avg_loss': random.uniform(30, 80),
        'best_pair': random.choice(['BTCUSDT', 'ETHUSDT', 'SOLUSDT']),
        'worst_pair': random.choice(['DOGEUSDT', 'ADAUSDT', 'XRPUSDT'])
    }
    
    # Dữ liệu hiệu suất
    performance_stats = {
        'total_trades': random.randint(20, 100),
        'winning_trades': random.randint(15, 60),
        'losing_trades': random.randint(5, 40),
        'best_trade': random.uniform(100, 500),
        'worst_trade': random.uniform(-300, -50),
        'avg_holding_time': f"{random.randint(1, 12)} giờ",
        'success_rate': random.uniform(50, 75)
    }
    
    # Dữ liệu thống kê giao dịch
    trade_stats = {
        'avg_win': random.uniform(50, 200),
        'avg_loss': random.uniform(30, 100),
        'largest_win': random.uniform(300, 1000),
        'largest_loss': random.uniform(200, 500),
        'win_rate': random.uniform(50, 75),
        'profit_factor': random.uniform(1.2, 3.0),
        'avg_trade_time': f"{random.randint(2, 10)}h {random.randint(10, 59)}m",
        'total_fees': random.uniform(50, 500)
    }
    
    # Dữ liệu theo dõi
    watchlist = {
        'BTCUSDT': {
            'price': fake_prices.get('BTCUSDT', 36500),
            'change_24h': random.uniform(-5, 5),
            'alerts': [
                {'price': 35000, 'condition': 'below', 'active': True},
                {'price': 40000, 'condition': 'above', 'active': True}
            ]
        },
        'ETHUSDT': {
            'price': fake_prices.get('ETHUSDT', 2400),
            'change_24h': random.uniform(-5, 5),
            'alerts': [
                {'price': 2200, 'condition': 'below', 'active': True},
                {'price': 2600, 'condition': 'above', 'active': True}
            ]
        },
        'SOLUSDT': {
            'price': fake_prices.get('SOLUSDT', 115),
            'change_24h': random.uniform(-5, 5),
            'alerts': [
                {'price': 100, 'condition': 'below', 'active': True}
            ]
        }
    }
    
    # Danh sách hoạt động gần đây
    activities = [
        {'type': 'trade', 'time': '14:25', 'description': 'Mở vị thế BUY BTCUSDT tại $71250.50', 'icon': 'bi-arrow-up-circle-fill', 'class': 'text-success'},
        {'type': 'system', 'time': '14:15', 'description': 'Thị trường được phát hiện trong chế độ Uptrend', 'icon': 'bi-graph-up', 'class': 'text-primary'},
        {'type': 'trade', 'time': '13:45', 'description': 'Đóng vị thế SELL ETHUSDT P/L: -$25.50 (-1.2%)', 'icon': 'bi-arrow-down-circle-fill', 'class': 'text-danger'},
        {'type': 'trade', 'time': '13:30', 'description': 'Mở vị thế SELL ETHUSDT tại $3155.75', 'icon': 'bi-arrow-down-circle-fill', 'class': 'text-danger'},
        {'type': 'system', 'time': '13:00', 'description': 'Bot đã bắt đầu theo dõi SOLUSDT', 'icon': 'bi-plus-circle', 'class': 'text-info'},
        {'type': 'trade', 'time': '12:45', 'description': 'Đóng vị thế BUY BTCUSDT P/L: +$350.00 (+1.75%)', 'icon': 'bi-arrow-up-circle-fill', 'class': 'text-success'}
    ]
    
    return render_template('index.html', 
                          bot_status=bot_status, 
                          account_data=account_data,
                          market_data=market_data,
                          fake_prices=fake_prices,
                          signals=signals,
                          strategy_stats=strategy_stats,
                          performance_stats=performance_stats,
                          activities=activities,
                          positions=positions,
                          system_messages=system_messages,
                          watchlist=watchlist,
                          trade_stats=trade_stats)

@app.route('/bot-status', methods=['GET'])
def get_bot_status():
    return jsonify(bot_status)

@app.route('/start-bot', methods=['POST'])
def start_bot():
    bot_status['running'] = True
    bot_status['status'] = 'running'
    bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    add_system_message("Bot đã được khởi động!")
    return jsonify({'success': True, 'status': bot_status['status']})

@app.route('/stop-bot', methods=['POST'])
def stop_bot():
    bot_status['running'] = False
    bot_status['status'] = 'stopped'
    bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    add_system_message("Bot đã được dừng!")
    return jsonify({'success': True, 'status': bot_status['status']})

@app.route('/api/signals')
def get_signals():
    return jsonify({'success': True, 'signals': signals})

@app.route('/api/positions')
def get_positions():
    return jsonify({'success': True, 'positions': positions})

@app.route('/api/trades')
def get_trades():
    return jsonify({'success': True, 'trades': trades})

@app.route('/api/performance')
def get_performance():
    return jsonify({'success': True, 'performance': performance_data})

@app.route('/api/market')
def get_market():
    return jsonify({'success': True, 'market': market_data})

@app.route('/api/close-position/<position_id>', methods=['POST'])
def api_close_position(position_id):
    if close_position(position_id):
        return jsonify({'success': True, 'message': 'Vị thế đã được đóng'})
    else:
        return jsonify({'success': False, 'message': 'Không tìm thấy vị thế'})

@app.route('/api/system-messages')
def get_system_messages():
    return jsonify({'success': True, 'messages': system_messages})

@app.route('/api/balance')
def get_balance():
    return jsonify({
        'success': True,
        'balance': bot_status['balance'],
        'current_balance': get_current_balance(),
        'initial_balances': initial_balances
    })

@app.route('/api/bot/mode', methods=['POST'])
def set_bot_mode():
    data = request.json
    if 'mode' in data:
        bot_status['mode'] = data['mode']
        save_config()
        add_system_message(f"Chế độ bot đã được thay đổi thành: {data['mode']}")
        return jsonify({'success': True, 'mode': bot_status['mode']})
    return jsonify({'success': False, 'message': 'Missing mode parameter'})

@app.route('/api/account/type', methods=['POST'])
def set_account_type():
    data = request.json
    if 'account_type' in data:
        bot_status['account_type'] = data['account_type']
        save_config()
        add_system_message(f"Loại tài khoản đã được thay đổi thành: {data['account_type']}")
        return jsonify({'success': True, 'account_type': bot_status['account_type']})
    return jsonify({'success': False, 'message': 'Missing account_type parameter'})

@app.route('/api/telegram/config', methods=['GET', 'POST'])
def telegram_config_api():
    global telegram_config, telegram_notifier
    
    if request.method == 'GET':
        return jsonify({'success': True, 'data': telegram_config})
    
    data = request.json
    if 'enabled' in data:
        telegram_config['enabled'] = data['enabled']
    
    global telegram_notifier
    
    if 'bot_token' in data:
        telegram_config['bot_token'] = data['bot_token']
    
    if 'chat_id' in data:
        telegram_config['chat_id'] = data['chat_id']
    
    # Cập nhật Telegram notifier với thông tin mới
    telegram_notifier = TelegramNotifier(
        token=telegram_config['bot_token'],
        chat_id=telegram_config['chat_id']
    )
    
    if 'min_interval' in data:
        telegram_config['min_interval'] = data['min_interval']
    
    # Lưu cấu hình
    save_config()
    logger.info("Đã lưu cấu hình Telegram")
    
    # Thử gửi tin nhắn kiểm tra
    if telegram_config['enabled'] and telegram_config['bot_token'] and telegram_config['chat_id']:
        result = telegram_notifier.send_message("✅ Kết nối Telegram thành công! Bot thông báo đã sẵn sàng.")
        if not result:
            add_system_message("Kết nối Telegram thất bại, vui lòng kiểm tra token và chat_id")
            return jsonify({
                'success': True,
                'message': "Kết nối Telegram thất bại, vui lòng kiểm tra token và chat_id",
                'config': {
                    'enabled': telegram_config['enabled'],
                    'has_token': bool(telegram_config['bot_token']),
                    'has_chat_id': bool(telegram_config['chat_id']),
                    'min_interval': telegram_config['min_interval']
                }
            })
    
    return jsonify({
        'success': True,
        'message': "Cấu hình Telegram đã được lưu",
        'config': {
            'enabled': telegram_config['enabled'],
            'has_token': bool(telegram_config['bot_token']),
            'has_chat_id': bool(telegram_config['chat_id']),
            'min_interval': telegram_config['min_interval']
        }
    })

@app.route('/test-telegram', methods=['POST'])
def test_telegram():
    if not telegram_config['enabled'] or not telegram_config['bot_token'] or not telegram_config['chat_id']:
        return jsonify({'success': False, 'message': 'Telegram chưa được cấu hình'})
    
    result = telegram_notifier.send_message("🧪 Đây là tin nhắn kiểm tra từ BinanceTrader Bot")
    
    if result:
        return jsonify({'success': True, 'message': 'Đã gửi tin nhắn kiểm tra thành công'})
    else:
        return jsonify({'success': False, 'message': 'Không thể gửi tin nhắn kiểm tra'})

# Thêm các route điều hướng
@app.route('/strategies')
def strategies():
    return render_template('strategies.html', bot_status=bot_status, fake_prices=fake_prices)

@app.route('/backtest')
def backtest():
    return render_template('backtest.html', bot_status=bot_status, fake_prices=fake_prices)

@app.route('/trades')
def trades_page():
    return render_template('trades.html', bot_status=bot_status, trades=trades, fake_prices=fake_prices)

@app.route('/market')
def market():
    market_data = {
        'btc_price': fake_prices.get('BTCUSDT', 0),
        'eth_price': fake_prices.get('ETHUSDT', 0),
        'sol_price': fake_prices.get('SOLUSDT', 25.0),
        'bnb_price': fake_prices.get('BNBUSDT', 0)
    }
    return render_template('market.html', bot_status=bot_status, fake_prices=fake_prices, market_data=market_data)

@app.route('/position')
def position():
    return render_template('position.html', bot_status=bot_status, positions=positions, fake_prices=fake_prices)

@app.route('/settings')
def settings():
    return render_template('settings.html', bot_status=bot_status, telegram_config=telegram_config)

@app.route('/cli')
def cli():
    return render_template('cli.html', bot_status=bot_status, system_messages=system_messages)

@app.route('/trading-report')
def trading_report():
    return render_template('trading_report.html', bot_status=bot_status, trades=trades, performance_data=performance_data)

# Các kết nối Socket.IO
@socketio.on('connect')
def on_connect():
    logger.info('Client connected')
    socketio.emit('bot_status_update', bot_status)

@socketio.on('disconnect')
def on_disconnect():
    logger.info('Client disconnected')

@socketio.on('start_bot')
def on_start_bot():
    bot_status['running'] = True
    bot_status['status'] = 'running'
    bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    add_system_message("Bot đã được khởi động!")
    socketio.emit('bot_status_update', bot_status)

@socketio.on('stop_bot')
def on_stop_bot():
    bot_status['running'] = False
    bot_status['status'] = 'stopped'
    bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    add_system_message("Bot đã được dừng!")
    socketio.emit('bot_status_update', bot_status)

@socketio.on('close_position')
def on_close_position(data):
    position_id = data.get('position_id')
    if position_id and close_position(position_id):
        socketio.emit('positions_update', positions)
        socketio.emit('bot_status_update', bot_status)
        return {'success': True, 'message': 'Vị thế đã được đóng'}
    return {'success': False, 'message': 'Không tìm thấy vị thế'}

if __name__ == "__main__":
    # Bắt đầu tác vụ nền
    background_thread = threading.Thread(target=background_tasks)
    background_thread.daemon = True
    background_thread.start()
    
    # Khởi chạy ứng dụng
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False, log_output=True)
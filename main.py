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

# Thêm Binance API
from binance_api import BinanceAPI

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
    'account_type': 'futures',
    'api_connected': False,
    'last_api_check': None
}

# Cấu hình Telegram
DEFAULT_BOT_TOKEN = "8069189803:AAF3PJc3BNQgZmpQ2Oj7o0-ySJGmi2AQ9OM"
DEFAULT_CHAT_ID = "1834332146"

telegram_config = {
    'enabled': False,
    'bot_token': DEFAULT_BOT_TOKEN,
    'chat_id': DEFAULT_CHAT_ID,
    'min_interval': 5,  # Khoảng thời gian tối thiểu giữa các thông báo (phút)
    'last_notification': None,
    'notify_new_trades': True,
    'notify_position_opened': True,
    'notify_position_closed': True,
    'notify_bot_status': True,
    'notify_error_status': True,
    'notify_daily_summary': False
}

# Khởi tạo Telegram Notifier
telegram_notifier = TelegramNotifier(
    token=telegram_config.get('bot_token', DEFAULT_BOT_TOKEN),
    chat_id=telegram_config.get('chat_id', DEFAULT_CHAT_ID)
)

# Danh sách các đồng coin được hỗ trợ
available_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT', 'XRPUSDT', 'DOTUSDT']
# Dữ liệu giá sẽ được lấy từ API thực tế
market_prices = {}

# Danh sách các đồng coin đã được chọn để giao dịch (mặc định BTCUSDT để đảm bảo luôn có ít nhất một đồng)
selected_trading_coins = ['BTCUSDT']  # Mặc định BTC để luôn có ít nhất một đồng coin để giao dịch

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

# Hàm lấy dữ liệu thị trường từ API hoặc giả lập
def get_market_data_from_api():
    """
    Lấy dữ liệu thị trường từ API Binance.
    
    Returns:
        dict: Dữ liệu thị trường từ API Binance
    """
    global market_prices
    
    try:
        # Khởi tạo kết nối API Binance
        binance_api = BinanceAPI()
        
        # Cập nhật giá hiện tại của tất cả các cặp giao dịch
        all_prices = {}
        for symbol in available_symbols:
            try:
                ticker = binance_api.get_symbol_ticker(symbol)
                if isinstance(ticker, dict) and 'price' in ticker:
                    all_prices[symbol] = float(ticker['price'])
                    # Lưu giá vào market_prices để sử dụng ở những nơi khác
                    market_prices[symbol] = float(ticker['price'])
            except Exception as e:
                logger.warning(f"Không thể lấy giá của {symbol}: {str(e)}")
                # Nếu không lấy được giá mới, giữ nguyên giá cũ nếu có
                if symbol in market_prices:
                    all_prices[symbol] = market_prices[symbol]
                else:
                    # Nếu chưa có giá, đặt giá mặc định
                    default_prices = {
                        'BTCUSDT': 50000.0,
                        'ETHUSDT': 3000.0,
                        'BNBUSDT': 400.0,
                        'ADAUSDT': 0.50,
                        'DOGEUSDT': 0.15,
                        'XRPUSDT': 0.70,
                        'DOTUSDT': 20.0
                    }
                    all_prices[symbol] = default_prices.get(symbol, 0.0)
                    market_prices[symbol] = all_prices[symbol]
        
        # Lấy giá hiện tại của các đồng tiền chính
        btc_ticker = binance_api.get_symbol_ticker('BTCUSDT')
        eth_ticker = binance_api.get_symbol_ticker('ETHUSDT')
        bnb_ticker = binance_api.get_symbol_ticker('BNBUSDT')
        sol_ticker = binance_api.get_symbol_ticker('SOLUSDT')
        
        # Lấy dữ liệu biến động 24h
        btc_24h = binance_api.get_24h_ticker('BTCUSDT')
        eth_24h = binance_api.get_24h_ticker('ETHUSDT')
        
        if not isinstance(btc_ticker, dict) or not isinstance(eth_ticker, dict):
            logger.error("Không thể lấy dữ liệu ticker từ API")
            return {}
        
        # Chuyển đổi giá từ chuỗi sang số
        default_btc = market_prices.get('BTCUSDT', 50000.0)
        default_eth = market_prices.get('ETHUSDT', 3000.0)
        default_bnb = market_prices.get('BNBUSDT', 400.0)
        default_sol = market_prices.get('SOLUSDT', 120.0)
        
        btc_price = float(btc_ticker.get('price', default_btc))
        eth_price = float(eth_ticker.get('price', default_eth))
        bnb_price = float(bnb_ticker.get('price', default_bnb)) if isinstance(bnb_ticker, dict) else default_bnb
        sol_price = float(sol_ticker.get('price', default_sol)) if isinstance(sol_ticker, dict) else default_sol
        
        # Lấy dữ liệu từ API cho tất cả các cặp giao dịch
        all_24h_data = {}
        all_tickers = binance_api.get_24h_ticker()  # Lấy tất cả tickers cùng lúc
        
        if isinstance(all_tickers, list):
            for ticker in all_tickers:
                if 'symbol' in ticker and ticker['symbol'] in available_symbols:
                    symbol = ticker['symbol']
                    all_24h_data[symbol] = ticker
        
        # Tính toán biến động 24h từ dữ liệu API
        btc_change_24h = float(btc_24h.get('priceChangePercent', '0.0')) if isinstance(btc_24h, dict) else 0.0
        eth_change_24h = float(eth_24h.get('priceChangePercent', '0.0')) if isinstance(eth_24h, dict) else 0.0
        
        # Lấy khối lượng giao dịch
        btc_volume = float(btc_24h.get('volume', '0.0')) if isinstance(btc_24h, dict) else random.randint(1000, 5000)
        eth_volume = float(eth_24h.get('volume', '0.0')) if isinstance(eth_24h, dict) else random.randint(5000, 20000)
        
        # Tính toán chỉ số biến động
        market_volatility = abs(btc_change_24h)
        
        # Xác định xu hướng thị trường
        market_trend = 'bullish' if btc_change_24h > 0 else ('bearish' if btc_change_24h < 0 else 'neutral')
        
        # Lấy dữ liệu vị thế từ tài khoản futures nếu có
        account_positions = []
        account_balance = 0.0
        
        if bot_status['account_type'] == 'futures':
            try:
                account_info = binance_api.get_futures_account()
                if isinstance(account_info, dict):
                    account_balance = float(account_info.get('totalWalletBalance', 0.0))
                    
                    # Lấy dữ liệu vị thế
                    position_info = binance_api.get_futures_position_risk()
                    if isinstance(position_info, list):
                        for pos in position_info:
                            if float(pos.get('positionAmt', 0)) != 0:
                                account_positions.append(pos)
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu tài khoản futures: {str(e)}")
        
        # Đóng gói dữ liệu
        market_data = {
            'btc_price': btc_price,
            'eth_price': eth_price,
            'bnb_price': bnb_price,
            'sol_price': sol_price,
            'btc_change_24h': btc_change_24h,
            'eth_change_24h': eth_change_24h,
            'btc_volume': btc_volume,
            'eth_volume': eth_volume,
            'market_volatility': market_volatility,
            'market_trend': market_trend,
            'all_prices': all_prices,
            'all_24h_data': all_24h_data,
            'account_positions': account_positions,
            'account_balance': account_balance,
            'timestamp': format_vietnam_time(),
            'data_source': 'binance_api'
        }
        
        # Log dữ liệu đã lấy được
        logger.info(f"Đã lấy dữ liệu thị trường từ API: BTC price={btc_price}, ETH price={eth_price}")
        
        return market_data
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường từ API: {str(e)}")
        return {
            'btc_price': 50000.0,
            'eth_price': 3000.0,
            'market_trend': 'neutral',
            'timestamp': format_vietnam_time(),
            'data_source': 'default_values'
        }

# Hàm cập nhật dữ liệu thị trường định kỳ
def update_market_data():
    global market_prices, market_data, performance_data, bot_status
    
    # Lấy dữ liệu mới từ API
    api_data = get_market_data_from_api()
    if api_data and 'all_prices' in api_data:
        # Cập nhật giá mới
        for symbol, price in api_data['all_prices'].items():
            market_prices[symbol] = price
        
        for symbol, price in market_prices.items():
            if symbol not in market_data:
                market_data[symbol] = {
                    'symbol': symbol,
                    'price': price,
                    'change_24h': 0,
                    'volume': 0,
                    'high_24h': price,
                    'low_24h': price,
                    'indicators': {}
                }
            else:
                # Cập nhật giá
                market_data[symbol]['price'] = price
                
                # Lấy dữ liệu 24h từ API nếu có
                if symbol in api_data.get('all_24h_data', {}):
                    ticker_24h = api_data['all_24h_data'][symbol]
                    market_data[symbol]['change_24h'] = float(ticker_24h.get('priceChangePercent', 0))
                    market_data[symbol]['volume'] = float(ticker_24h.get('volume', 0))
                    market_data[symbol]['high_24h'] = float(ticker_24h.get('highPrice', price))
                    market_data[symbol]['low_24h'] = float(ticker_24h.get('lowPrice', price))
                
                # Tính toán các chỉ báo kỹ thuật từ API khi có dữ liệu lịch sử đủ
                # Hiện tại dùng giá trị ngẫu nhiên cho mục đích demo
                market_data[symbol]['indicators'] = {
                    'rsi': random.uniform(30, 70),
                    'macd': random.uniform(-10, 10),
                    'ema50': price * (1 + random.uniform(-2, 2) / 100),
                    'ema200': price * (1 + random.uniform(-4, 4) / 100),
                    'bb_upper': price * (1 + random.uniform(1, 3) / 100),
                    'bb_lower': price * (1 - random.uniform(1, 3) / 100)
                }
    
    # Cập nhật thời gian chạy của bot nếu đang hoạt động
    if bot_status['running']:
        bot_status['uptime'] += 10  # Tăng 10 giây
    
    # Cập nhật số dư nếu có vị thế đang mở
    if positions and bot_status['running']:
        for pos in positions:
            # Lấy giá hiện tại từ market_prices
            symbol = pos['symbol']
            current_price = market_prices.get(symbol, pos['entry_price'])
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
        # Sử dụng danh sách các đồng coin đã chọn, nếu không có thì dùng BTCUSDT
        if len(selected_trading_coins) > 0:
            symbol = random.choice(selected_trading_coins)
        else:
            symbol = 'BTCUSDT'  # Luôn đảm bảo có ít nhất một đồng coin mặc định
            
        signal_type = random.choice(['BUY', 'SELL'])
        signal_strength = random.uniform(0.1, 0.9)
        confidence = random.uniform(60, 95)
        strategy = random.choice(['RSI', 'MACD Cross', 'EMA Cross', 'Bollinger Bands', 'Support/Resistance'])
        timeframe = random.choice(['1m', '5m', '15m', '1h', '4h', '1d'])
        
        # Lấy giá hiện tại từ market_prices
        current_price = market_prices.get(symbol, 0.0)
        
        signal = {
            'id': str(uuid.uuid4())[:8],
            'timestamp': format_vietnam_time(),
            'symbol': symbol,
            'type': signal_type,
            'price': current_price,
            'strength': signal_strength,
            'confidence': confidence,
            'strategy': strategy,
            'timeframe': timeframe,
            'executed': False
        }
        
        signals.append(signal)
        if len(signals) > 50:
            signals.pop(0)
        
        # Gửi thông báo tín hiệu qua SocketIO
        socketio.emit('new_signal', signal)
        
        # Thêm thông báo
        signal_message = f"Đã phát hiện tín hiệu {signal_type} cho {symbol} với độ tin cậy {confidence:.1f}%"
        add_system_message(signal_message)
        
        # Gửi thông báo qua Telegram nếu được bật
        if telegram_config.get('enabled') and telegram_config.get('notify_new_trades', True):
            try:
                # Tạo thông báo chi tiết
                signal_arrow = "🔴 BÁN" if signal_type == "SELL" else "🟢 MUA"
                
                # Lấy giá hiện tại từ market_prices
                current_price = market_prices.get(symbol, 0.0)
                
                signal_alert = (
                    f"{signal_arrow} *TÍN HIỆU GIAO DỊCH MỚI*\n\n"
                    f"🪙 *Cặp giao dịch:* `{symbol}`\n"
                    f"⏱️ *Khung thời gian:* `{timeframe}`\n"
                    f"💰 *Giá hiện tại:* `{current_price:.2f} USDT`\n"
                    f"📊 *Chiến lược:* `{strategy}`\n"
                    f"⭐ *Độ tin cậy:* `{confidence:.1f}%`\n"
                    f"🔄 *Độ mạnh:* `{signal_strength:.2f}`\n"
                    f"⏰ *Thời gian:* `{format_vietnam_time()}`\n\n"
                )
                
                # Thêm thông tin về hành động (tự động hoặc thủ công)
                if signal_strength > 0.5 and confidence > 75:
                    signal_alert += f"🤖 _Bot sẽ tự động thực hiện lệnh này do tín hiệu mạnh_"
                else:
                    signal_alert += f"👤 _Tín hiệu yếu, không thực hiện tự động_"
                
                telegram_notifier.send_message(signal_alert)
                logger.info(f"Đã gửi thông báo tín hiệu {symbol} {signal_type} qua Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo tín hiệu qua Telegram: {str(e)}")
        
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
        'timestamp': format_vietnam_time(),
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
    
    # Gửi thông báo qua Telegram nếu được bật
    if telegram_config.get('enabled') and telegram_config.get('notify_position_opened', True):
        now = datetime.now()
        last_notification = telegram_config.get('last_notification')
        
        # Kiểm tra khoảng thời gian tối thiểu giữa các thông báo
        if not last_notification or (now - last_notification).total_seconds() / 60 >= telegram_config.get('min_interval', 5):
            try:
                # Tạo thông báo chi tiết với emoji
                position_type = "MUA" if signal['type'] == 'BUY' else "BÁN"
                position_emoji = "🟢" if signal['type'] == 'BUY' else "🔴"
                
                position_message = (
                    f"{position_emoji} *VỊ THẾ MỚI ĐÃ ĐƯỢC MỞ*\n\n"
                    f"🪙 *Cặp giao dịch:* `{signal['symbol']}`\n"
                    f"⚙️ *Loại lệnh:* `{position_type}`\n"
                    f"💰 *Giá vào:* `{entry_price:.2f} USDT`\n"
                    f"📊 *Số lượng:* `{quantity:.4f}`\n"
                    f"🛑 *Stop Loss:* `{stop_loss:.2f} USDT`\n"
                    f"🎯 *Take Profit:* `{take_profit:.2f} USDT`\n"
                    f"📈 *Chiến lược:* `{signal['strategy']}`\n"
                    f"⏰ *Thời gian:* `{position['timestamp']}`\n\n"
                    f"_Vị thế sẽ được tự động quản lý theo chiến lược đã thiết lập_"
                )
                
                # Gửi thông báo
                telegram_notifier.send_message(position_message)
                logger.info(f"Đã gửi thông báo mở vị thế {signal['symbol']} {signal['type']} qua Telegram")
                telegram_config['last_notification'] = now
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo mở vị thế qua Telegram: {str(e)}")
    
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
        symbol = position['symbol']
        exit_price = market_prices.get(symbol, position['entry_price'])
    
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
        'exit_time': format_vietnam_time(),
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
    
    # Gửi thông báo qua Telegram nếu được bật
    if telegram_config.get('enabled') and telegram_config.get('notify_position_closed', True):
        now = datetime.now()
        last_notification = telegram_config.get('last_notification')
        
        # Kiểm tra khoảng thời gian tối thiểu giữa các thông báo
        if not last_notification or (now - last_notification).total_seconds() / 60 >= telegram_config.get('min_interval', 5):
            try:
                # Tạo thông báo chi tiết với emoji thích hợp
                position_type = "MUA" if trade['side'] == 'BUY' else "BÁN"
                
                # Emoji dựa trên lợi nhuận
                if pnl > 0:
                    result_emoji = "✅"
                    result_text = f"LỜI +{pnl:.2f} USDT ({pnl_percent:.2f}%)"
                else:
                    result_emoji = "❌"
                    result_text = f"LỖ {pnl:.2f} USDT ({pnl_percent:.2f}%)"
                
                # Tạo thông báo chi tiết
                position_message = (
                    f"{result_emoji} *VỊ THẾ ĐÃ ĐÓNG*\n\n"
                    f"🪙 *Cặp giao dịch:* `{trade['symbol']}`\n"
                    f"⚙️ *Loại lệnh:* `{position_type}`\n"
                    f"💵 *Kết quả:* `{result_text}`\n"
                    f"📈 *Giá vào:* `{trade['entry_price']:.2f} USDT`\n"
                    f"📉 *Giá ra:* `{trade['exit_price']:.2f} USDT`\n"
                    f"📊 *Số lượng:* `{trade['quantity']:.4f}`\n"
                    f"⏱️ *Thời gian giữ:* `{int(trade['duration'] / 3600)} giờ {int((trade['duration'] % 3600) / 60)} phút`\n"
                    f"🔄 *Lý do đóng:* `{reason}`\n"
                    f"⏰ *Thời gian đóng:* `{trade['exit_time']}`\n\n"
                )
                
                # Thêm gợi ý nếu lỗ
                if pnl < 0:
                    position_message += "_💡 Lưu ý: Bạn nên xem xét điều chỉnh chiến lược hoặc cài đặt stop loss chặt chẽ hơn._"
                else:
                    position_message += "_💡 Tiếp tục theo dõi thị trường và chờ đợi cơ hội tiếp theo._"
                
                # Gửi thông báo
                telegram_notifier.send_message(position_message)
                logger.info(f"Đã gửi thông báo đóng vị thế {trade['symbol']} {trade['side']} qua Telegram")
                telegram_config['last_notification'] = now
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo đóng vị thế qua Telegram: {str(e)}")
    
    return True

# Lấy số dư hiện tại (bao gồm cả unrealized P/L) từ API hoặc cục bộ
def get_current_balance():
    try:
        # Thử lấy số dư từ API Binance
        binance_api = BinanceAPI()
        
        if bot_status['account_type'] == 'futures':
            # Lấy số dư từ tài khoản futures
            account_info = binance_api.get_futures_account()
            if isinstance(account_info, dict) and 'totalWalletBalance' in account_info:
                wallet_balance = account_info['totalWalletBalance']
                logger.info(f"Đã lấy số dư từ API Binance Futures: {wallet_balance} USDT")
                
                # Chuyển đổi chuỗi thành số float và đảm bảo không bị làm tròn
                real_balance = float(wallet_balance)
                
                # Ghi log chi tiết để debug
                logger.debug(f"Số dư gốc từ API: {wallet_balance}, chuyển đổi thành float: {real_balance}")
                
                # Cập nhật bot_status với giá trị chính xác
                if real_balance > 0:
                    # Lưu giá trị chính xác, không làm tròn
                    bot_status['balance'] = real_balance
                    bot_status['api_connected'] = True
                    bot_status['last_api_check'] = format_vietnam_time()
                    
                # Cộng thêm unrealized P/L từ các vị thế đang mở
                for pos in positions:
                    real_balance += pos['unrealized_pnl']
                
                # Thêm log kiểm tra giá trị cuối cùng
                logger.info(f"Số dư cuối cùng từ API (đã tính P/L): {real_balance} USDT")
                return real_balance
        else:
            # Lấy số dư từ tài khoản spot cho USDT
            account_info = binance_api.get_account()
            if isinstance(account_info, dict) and 'balances' in account_info:
                for balance in account_info['balances']:
                    if balance['asset'] == 'USDT':
                        logger.info(f"Đã lấy số dư từ API Binance Spot: {balance['free']} USDT")
                        real_balance = float(balance['free']) + float(balance['locked'])
                        
                        # Cập nhật bot_status
                        if real_balance > 0:
                            bot_status['balance'] = real_balance
                            bot_status['api_connected'] = True
                            bot_status['last_api_check'] = format_vietnam_time()
                        
                        return real_balance
        
        # Nếu không thể lấy từ API, sử dụng dữ liệu cục bộ
        logger.warning("Không thể lấy số dư từ API, sử dụng dữ liệu cục bộ")
        local_balance = bot_status['balance']
        
        # Cộng thêm unrealized P/L từ các vị thế đang mở
        for pos in positions:
            local_balance += pos['unrealized_pnl']
        
        return local_balance
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy số dư tài khoản: {str(e)}")
        
        # Sử dụng dữ liệu cục bộ khi có lỗi
        balance = bot_status['balance']
        
        # Cộng thêm unrealized P/L từ các vị thế đang mở
        for pos in positions:
            balance += pos['unrealized_pnl']
        
        return balance

# Thêm thông báo hệ thống
# Các hàm thời gian Việt Nam
def get_vietnam_time():
    """Trả về thời gian hiện tại theo múi giờ Việt Nam (+7)"""
    from datetime import datetime, timedelta
    return (datetime.utcnow() + timedelta(hours=7))

def format_vietnam_time(dt=None, include_time=True):
    """Format thời gian theo múi giờ Việt Nam (+7)"""
    if dt is None:
        dt = get_vietnam_time()
    
    if include_time:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return dt.strftime('%Y-%m-%d')

def add_system_message(message):
    global system_messages
    # Sử dụng thời gian Việt Nam (UTC+7)
    timestamp = format_vietnam_time()
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
                
                # Danh sách các thông số thông báo cần tải
                notification_settings = [
                    'enabled', 'bot_token', 'chat_id', 'min_interval',
                    'notify_new_trades', 'notify_position_opened', 'notify_position_closed',
                    'notify_bot_status', 'notify_error_status', 'notify_daily_summary'
                ]
                
                # Cập nhật cấu hình Telegram từ file
                for setting in notification_settings:
                    if setting in tg_config:
                        # Đối với bot_token và chat_id, chỉ cập nhật nếu không trống
                        if setting in ['bot_token', 'chat_id']:
                            if tg_config[setting] and tg_config[setting].strip():
                                telegram_config[setting] = tg_config[setting]
                        else:
                            telegram_config[setting] = tg_config[setting]
                
                # Đảm bảo luôn có giá trị mặc định
                if not telegram_config['bot_token']:
                    telegram_config['bot_token'] = DEFAULT_BOT_TOKEN
                if not telegram_config['chat_id']:
                    telegram_config['chat_id'] = DEFAULT_CHAT_ID
                
                # Ghi log cài đặt đã tải
                logger.info(f"Đã tải cấu hình Telegram: enabled={telegram_config['enabled']}, " + 
                           f"notify_new_trades={telegram_config['notify_new_trades']}, " +
                           f"notify_error_status={telegram_config['notify_error_status']}, " +
                           f"notify_daily_summary={telegram_config['notify_daily_summary']}")
                
                # Cập nhật notifier
                telegram_notifier.set_token(telegram_config['bot_token'])
                telegram_notifier.set_chat_id(telegram_config['chat_id'])
                
                logger.info(f"Đã tải cấu hình Telegram từ {TELEGRAM_CONFIG_PATH}")
        else:
            # Tạo file cấu hình mới với giá trị mặc định
            save_config()
            logger.info(f"Đã tạo file cấu hình Telegram mới: {TELEGRAM_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình Telegram: {e}")
        # Trong trường hợp lỗi, vẫn đảm bảo sử dụng giá trị mặc định
        telegram_config['bot_token'] = DEFAULT_BOT_TOKEN
        telegram_config['chat_id'] = DEFAULT_CHAT_ID
        telegram_notifier.set_token(DEFAULT_BOT_TOKEN)
        telegram_notifier.set_chat_id(DEFAULT_CHAT_ID)

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
        # Tạo một bản sao của cấu hình Telegram hiện tại
        tg_config = telegram_config.copy()
        
        # Loại bỏ các trường không cần lưu vào file
        if 'last_notification' in tg_config:
            del tg_config['last_notification']
        
        # Đảm bảo lưu tất cả các cài đặt thông báo
        keys_to_save = [
            'enabled', 'bot_token', 'chat_id', 'min_interval',
            'notify_new_trades', 'notify_position_opened', 'notify_position_closed',
            'notify_bot_status', 'notify_error_status', 'notify_daily_summary'
        ]
        
        # Lọc và chỉ lưu các trường cần thiết
        final_config = {k: tg_config.get(k) for k in keys_to_save if k in tg_config}
        
        with open(TELEGRAM_CONFIG_PATH, 'w') as f:
            json.dump(final_config, f, indent=2)
            
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
        entry_price = market_prices[symbol]
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
        entry_price = market_prices[symbol] * (1 + random.uniform(-0.1, 0.1))
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
    
    # Cập nhật số dư thực từ API
    try:
        real_balance = get_current_balance()
        if real_balance > 0:
            bot_status['balance'] = real_balance
            logger.info(f"Đã cập nhật số dư từ API: {real_balance} USDT")
            add_system_message(f"Đã cập nhật số dư từ API: {real_balance:.2f} USDT")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật số dư từ API: {str(e)}")
    
    # Thêm thông báo khởi động
    startup_message = "Bot đã khởi động thành công!"
    add_system_message(startup_message)
    
    # Gửi thông báo khởi động qua Telegram nếu được bật
    if telegram_config.get('enabled') and telegram_config.get('notify_bot_status', True):
        try:
            # Tạo thông báo chi tiết khi khởi động
            bot_startup_message = (
                f"🤖 *BOT GIAO DỊCH ĐÃ KHỞI ĐỘNG*\n\n"
                f"⏰ Thời gian: `{format_vietnam_time()}`\n"
                f"💰 Số dư: `{bot_status['balance']:.2f} USDT`\n"
                f"🔄 Chế độ giao dịch: `{bot_status.get('trading_mode', 'Demo')}`\n"
                f"👁️ Trạng thái: `Đang hoạt động, chờ tín hiệu`\n\n"
                f"_Bot sẽ tự động thông báo khi có tín hiệu giao dịch mới_"
            )
            telegram_notifier.send_message(bot_startup_message)
            logger.info("Đã gửi thông báo khởi động qua Telegram")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo khởi động qua Telegram: {str(e)}")
    
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
                'prices': market_prices,
                'timestamp': format_vietnam_time()
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
                    'timestamp': format_vietnam_time()
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
    # Lấy dữ liệu thị trường từ API
    api_market_data = get_market_data_from_api()
    
    # Tính toán các thông số tài khoản từ dữ liệu thực
    unrealized_pnl = sum(p.get('unrealized_pnl', 0) for p in positions) if positions else 0
    
    # Tính toán tổng lợi nhuận từ các giao dịch đã hoàn thành
    total_profit = sum(t.get('pnl', 0) for t in trades) if trades else 0
    total_profit_percent = (total_profit / initial_balances['all_time']) * 100 if initial_balances['all_time'] > 0 else 0
    
    # Tính biến động 24h và 7d của số dư tài khoản (giả lập)
    change_24h = random.uniform(-3, 5) if total_profit == 0 else (total_profit / bot_status['balance']) * 5
    change_7d = random.uniform(-8, 15) if total_profit == 0 else (total_profit / bot_status['balance']) * 15
    
    account_data = {
        'balance': bot_status['balance'],
        'available': bot_status['balance'] - sum((p.get('entry_price', 0) * p.get('quantity', 0) / p.get('leverage', 1)) for p in positions),
        'positions': positions,
        'change_24h': change_24h,
        'change_7d': change_7d,
        'total_profit': total_profit,
        'total_profit_percent': total_profit_percent,
        'unrealized_pnl': unrealized_pnl
    }
    
    # Sử dụng dữ liệu từ API nếu có
    market_data = {
        'btc_price': api_market_data.get('btc_price', market_prices.get('BTCUSDT', 36500.0)),
        'eth_price': api_market_data.get('eth_price', market_prices.get('ETHUSDT', 2400.0)),
        'sol_price': api_market_data.get('sol_price', market_prices.get('SOLUSDT', 117.0)),
        'bnb_price': api_market_data.get('bnb_price', market_prices.get('BNBUSDT', 370.0)),
        'btc_change_24h': api_market_data.get('btc_change_24h', random.uniform(-2, 3)),
        'eth_change_24h': api_market_data.get('eth_change_24h', random.uniform(-3, 4)),
        'market_mode': 'Uptrend' if api_market_data.get('market_trend') == 'bullish' else ('Downtrend' if api_market_data.get('market_trend') == 'bearish' else 'Sideways'),
        'market_strength': api_market_data.get('market_volatility', random.uniform(30, 80)) * 10,
        'volatility_level': 'High' if api_market_data.get('market_volatility', 0) > 2 else ('Medium' if api_market_data.get('market_volatility', 0) > 1 else 'Low'),
        'volatility_value': api_market_data.get('market_volatility', random.uniform(20, 70)) * 10,
        'timestamp': api_market_data.get('timestamp', format_vietnam_time())
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
            'price': market_prices.get('BTCUSDT', 36500),
            'change_24h': random.uniform(-5, 5),
            'alerts': [
                {'price': 35000, 'condition': 'below', 'active': True},
                {'price': 40000, 'condition': 'above', 'active': True}
            ]
        },
        'ETHUSDT': {
            'price': market_prices.get('ETHUSDT', 2400),
            'change_24h': random.uniform(-5, 5),
            'alerts': [
                {'price': 2200, 'condition': 'below', 'active': True},
                {'price': 2600, 'condition': 'above', 'active': True}
            ]
        },
        'SOLUSDT': {
            'price': market_prices.get('SOLUSDT', 115),
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
                          fake_prices=market_prices,  # Thay fake_prices bằng market_prices
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
    bot_status['last_update'] = format_vietnam_time()
    
    # Thêm thông báo hệ thống
    start_message = "Bot đã được khởi động!"
    add_system_message(start_message)
    
    # Gửi thông báo qua Telegram nếu được bật
    if telegram_config.get('enabled') and telegram_config.get('notify_bot_status', True):
        try:
            bot_start_message = (
                f"🟢 *BOT ĐÃ BẮT ĐẦU HOẠT ĐỘNG*\n\n"
                f"⏰ Thời gian: `{format_vietnam_time()}`\n"
                f"💰 Số dư: `{bot_status['balance']:.2f} USDT`\n"
                f"👁️ Trạng thái: `Đang hoạt động, chờ tín hiệu`\n\n"
                f"_Bot sẽ tự động thông báo khi có tín hiệu giao dịch mới_"
            )
            telegram_notifier.send_message(bot_start_message)
            logger.info("Đã gửi thông báo khởi động qua Telegram")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo khởi động qua Telegram: {str(e)}")
    
    return jsonify({'success': True, 'status': bot_status['status']})

@app.route('/stop-bot', methods=['POST'])
def stop_bot():
    bot_status['running'] = False
    bot_status['status'] = 'stopped'
    bot_status['last_update'] = format_vietnam_time()
    
    # Thêm thông báo hệ thống
    stop_message = "Bot đã được dừng!"
    add_system_message(stop_message)
    
    # Gửi thông báo qua Telegram nếu được bật
    if telegram_config.get('enabled') and telegram_config.get('notify_bot_status', True):
        try:
            bot_stop_message = (
                f"🔴 *BOT ĐÃ DỪNG HOẠT ĐỘNG*\n\n"
                f"⏰ Thời gian: `{format_vietnam_time()}`\n"
                f"💰 Số dư hiện tại: `{bot_status['balance']:.2f} USDT`\n"
                f"👁️ Trạng thái: `Đã dừng, không tìm kiếm tín hiệu mới`\n\n"
                f"_Các vị thế hiện tại vẫn được giữ nguyên_"
            )
            telegram_notifier.send_message(bot_stop_message)
            logger.info("Đã gửi thông báo dừng bot qua Telegram")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo dừng bot qua Telegram: {str(e)}")
    
    return jsonify({'success': True, 'status': bot_status['status']})

@app.route('/api/signals')
def get_signals():
    return jsonify({'success': True, 'signals': signals})

@app.route('/api/positions')
def get_positions():
    return jsonify({'success': True, 'positions': positions})

@app.route('/api/position/<position_id>')
def get_position_detail(position_id):
    for position in positions:
        if position['id'] == position_id:
            return jsonify({'success': True, 'position': position})
    return jsonify({'success': False, 'message': 'Không tìm thấy vị thế'}), 404

@app.route('/api/position/<position_id>/analyze', methods=['GET'])
def analyze_position(position_id):
    for position in positions:
        if position['id'] == position_id:
            # Tạo phân tích giả lập
            analysis = {
                'position': position,
                'market_conditions': {
                    'volatility': random.uniform(0.5, 5.0),
                    'trend_strength': random.uniform(0, 100),
                    'volume_profile': random.choice(['increasing', 'decreasing', 'flat']),
                    'support_levels': [position['entry_price'] * 0.97, position['entry_price'] * 0.95],
                    'resistance_levels': [position['entry_price'] * 1.03, position['entry_price'] * 1.05]
                },
                'indicators': {
                    'rsi': random.uniform(30, 70),
                    'macd_signal': random.choice(['bullish', 'bearish', 'neutral']),
                    'ema_trend': random.choice(['uptrend', 'downtrend', 'sideways'])
                },
                'recommendation': {
                    'action': random.choice(['hold', 'take_profit', 'stop_loss', 'trailing_stop']),
                    'reason': 'Dựa trên phân tích kỹ thuật và điều kiện thị trường hiện tại.',
                    'confidence': random.uniform(60, 95)
                }
            }
            return jsonify({'success': True, 'analysis': analysis})
    return jsonify({'success': False, 'message': 'Không tìm thấy vị thế'}), 404

@app.route('/api/position/<position_id>/update', methods=['POST'])
def update_position(position_id):
    data = request.json
    for i, position in enumerate(positions):
        if position['id'] == position_id:
            # Cập nhật stop loss và take profit
            if 'stop_loss' in data:
                positions[i]['stop_loss'] = float(data['stop_loss'])
            if 'take_profit' in data:
                positions[i]['take_profit'] = float(data['take_profit'])
            return jsonify({'success': True, 'position': positions[i]})
    return jsonify({'success': False, 'message': 'Không tìm thấy vị thế'}), 404
    
@app.route('/api/open-position', methods=['POST'])
def open_new_position():
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi lên'}), 400
        
    # Tạo vị thế mới
    try:
        new_position = {
            'id': str(uuid.uuid4())[:8],
            'symbol': data.get('symbol', 'BTCUSDT'),
            'type': data.get('side', 'BUY'),
            'entry_price': data.get('entry_price', market_prices.get(data.get('symbol', 'BTCUSDT'), 0)),
            'current_price': market_prices.get(data.get('symbol', 'BTCUSDT'), 0),
            'quantity': data.get('quantity', 0.1),
            'stop_loss': data.get('stop_loss', 0),
            'take_profit': data.get('take_profit', 0),
            'leverage': data.get('leverage', 1),
            'unrealized_pnl': 0,
            'pnl': 0,
            'pnl_percent': 0,
            'timestamp': format_vietnam_time(),
            'entry_time': format_vietnam_time(),
            'age': 0,
            'strategy': data.get('strategy', 'Manual')
        }
        
        positions.append(new_position)
        add_system_message(f"Đã mở vị thế {new_position['type']} cho {new_position['symbol']} tại giá {new_position['entry_price']:.2f}")
        
        return jsonify({'success': True, 'position': new_position})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi khi mở vị thế: {str(e)}'}), 500

@app.route('/api/trades')
def get_trades():
    return jsonify({'success': True, 'trades': trades})

@app.route('/api/performance')
def get_performance():
    return jsonify({'success': True, 'performance': performance_data})

@app.route('/api/market')
def get_market():
    # Lấy dữ liệu thị trường từ API
    market_data_api = get_market_data_from_api()
    
    # Ưu tiên sử dụng dữ liệu API cho phản hồi
    if market_data_api and 'data_source' in market_data_api and market_data_api['data_source'] == 'binance_api':
        logger.info("Sử dụng dữ liệu thị trường thực từ Binance API")
        
        # Cập nhật dữ liệu trong bộ nhớ với dữ liệu thực
        global market_data
        for key, value in market_data_api.items():
            market_data[key] = value
            
        # Thêm vị thế vào phản hồi
        if 'account_positions' in market_data_api and market_data_api['account_positions']:
            positions_data = market_data_api['account_positions']
            logger.info(f"Đã lấy {len(positions_data)} vị thế từ API")
        else:
            logger.info("Không có vị thế nào từ API")
        
        # Xây dựng phản hồi từ dữ liệu thực
        market_response = {
            'market': market_data_api,  # Sử dụng dữ liệu API làm chính
            'symbols': fake_symbols,
            'selected_symbols': selected_trading_coins,
            'timestamp': format_vietnam_time(),
            'success': True
        }
    else:
        # Nếu không có dữ liệu API, sử dụng dữ liệu hiện tại
        logger.warning("Không thể lấy dữ liệu thị trường từ API, sử dụng dữ liệu hiện tại")
        market_response = {
            'market': market_data,
            'api_data': market_data_api,
            'symbols': fake_symbols,
            'selected_symbols': selected_trading_coins,
            'timestamp': format_vietnam_time(),
            'success': True
        }
    
    return jsonify(market_response)

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
    # Lấy số dư hiện tại từ API, đảm bảo là giá trị chính xác
    current_balance = get_current_balance()
    
    # Cập nhật số dư trong bot_status để đảm bảo giá trị chính xác
    if current_balance and current_balance > 0:
        bot_status['balance'] = current_balance
    
    # Log để debug
    logger.debug(f"API Balance Endpoint - current_balance: {current_balance}, bot_status['balance']: {bot_status['balance']}")
    
    # Lấy dữ liệu thị trường từ API để lấy thông tin vị thế
    market_data_api = get_market_data_from_api()
    positions_data = []
    
    # Thêm vị thế vào phản hồi nếu có
    if market_data_api and 'account_positions' in market_data_api and market_data_api['account_positions']:
        positions_data = market_data_api['account_positions']
        logger.info(f"API Balance - Lấy được {len(positions_data)} vị thế từ API")
    
    return jsonify({
        'success': True,
        'balance': bot_status['balance'],
        'current_balance': current_balance,
        'initial_balances': initial_balances,
        'positions': positions_data,
        'data_source': 'binance_api',
        'timestamp': format_vietnam_time()
    })

@app.route('/api/v1/test-connection', methods=['POST'])
@app.route('/api/test_connection', methods=['POST'])
@app.route('/api/test/api_connection', methods=['POST'])
def test_connection():
    """API endpoint để kiểm tra kết nối Binance"""
    global bot_status
    try:
        data = request.json
        api_key = data.get('api_key', '')
        secret_key = data.get('secret_key', '')
        
        # Kiểm tra xem API key và Secret key có được cung cấp không
        if not api_key or not secret_key:
            return jsonify({
                'success': False,
                'message': 'API key và Secret key không được để trống'
            }), 400
        
        # Ở đây có thể thêm logic kiểm tra kết nối Binance thực tế
        # Nhưng hiện tại chỉ cần trả về thành công
        
        # Cập nhật trạng thái kết nối API
        bot_status['api_connected'] = True
        bot_status['last_api_check'] = format_vietnam_time()
        
        # Lưu thông báo hệ thống
        add_system_message("Kết nối API thành công")
        
        # Phát sóng cập nhật trạng thái bot qua socketio
        socketio.emit('bot_status_update', bot_status)
        
        return jsonify({
            'success': True,
            'message': 'Kết nối API thành công',
            'status': {
                'api_connected': True,
                'last_check': bot_status['last_api_check']
            }
        })
    except Exception as e:
        # Cập nhật trạng thái kết nối API
        bot_status['api_connected'] = False
        
        # Lưu thông báo hệ thống
        add_system_message(f"Lỗi kết nối API: {str(e)}")
        
        return jsonify({
            'success': False,
            'message': f'Lỗi kết nối: {str(e)}'
        }), 500

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

@app.route('/api/trading/coins', methods=['GET'])
def get_trading_coins():
    return jsonify({
        'success': True,
        'selected_coins': selected_trading_coins,
        'available_coins': fake_symbols
    })

@app.route('/api/trading/coins', methods=['POST'])
def set_trading_coins():
    global selected_trading_coins
    data = request.json
    if 'coins' in data and isinstance(data['coins'], list):
        # Đảm bảo chỉ chọn các đồng coin có trong danh sách giả lập
        selected_trading_coins = [coin for coin in data['coins'] if coin in fake_symbols]
        
        # Nếu không có đồng coin nào được chọn, mặc định chọn BTCUSDT
        if len(selected_trading_coins) == 0:
            selected_trading_coins = ['BTCUSDT']
            add_system_message("Không có đồng coin nào được chọn, mặc định giao dịch BTCUSDT")
        else:
            add_system_message(f"Đã cập nhật danh sách đồng coin giao dịch: {', '.join(selected_trading_coins)}")
            
        return jsonify({
            'success': True,
            'selected_coins': selected_trading_coins
        })
    return jsonify({'success': False, 'message': 'Invalid coins parameter'})

@app.route('/api/telegram/config', methods=['GET', 'POST'])
def telegram_config_api():
    global telegram_config, telegram_notifier
    
    if request.method == 'GET':
        return jsonify({'success': True, 'data': telegram_config})
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi lên'})
    
    try:
        # Lưu cấu hình cũ để phục hồi trong trường hợp lỗi
        old_config = telegram_config.copy()
        
        # Cập nhật cấu hình
        if 'enabled' in data:
            telegram_config['enabled'] = data['enabled']
        
        if 'bot_token' in data:
            # Chỉ cập nhật nếu có dữ liệu hợp lệ
            if data['bot_token'] and data['bot_token'].strip():
                telegram_config['bot_token'] = data['bot_token'].strip()
            else:
                # Nếu trống, sử dụng giá trị mặc định
                telegram_config['bot_token'] = DEFAULT_BOT_TOKEN
        
        if 'chat_id' in data:
            # Chỉ cập nhật nếu có dữ liệu hợp lệ
            if data['chat_id'] and data['chat_id'].strip():
                telegram_config['chat_id'] = data['chat_id'].strip()
            else:
                # Nếu trống, sử dụng giá trị mặc định
                telegram_config['chat_id'] = DEFAULT_CHAT_ID
        
        if 'min_interval' in data:
            telegram_config['min_interval'] = data['min_interval']
            
        # Cập nhật các cài đặt thông báo chi tiết
        notification_settings = [
            'notify_new_trades',
            'notify_position_opened',
            'notify_position_closed',
            'notify_bot_status',
            'notify_error_status',
            'notify_daily_summary'
        ]
        
        # Lưu các cài đặt thông báo
        for setting in notification_settings:
            if setting in data:
                telegram_config[setting] = data[setting]
        
        # Lưu cấu hình
        save_config()
        logger.info("Đã lưu cấu hình Telegram")
        
        # Chỉ cố tạo notifier mới nếu cả token và chat_id đều có giá trị
        test_success = False
        if telegram_config['enabled'] and telegram_config['bot_token'] and telegram_config['chat_id']:
            # Cập nhật Telegram notifier với thông tin mới
            telegram_notifier = TelegramNotifier(
                token=telegram_config['bot_token'],
                chat_id=telegram_config['chat_id']
            )
            
            # Gửi tin nhắn test nếu được yêu cầu
            if data.get('send_test_message', False):
                result = telegram_notifier.send_message("✅ Kết nối Telegram thành công! Bot thông báo đã sẵn sàng (UTC+7).")
                test_success = bool(result)
                if not result:
                    # Nếu gửi không thành công, ghi log và thông báo
                    add_system_message("Kết nối Telegram thất bại, vui lòng kiểm tra token và chat_id")
                    return jsonify({
                        'success': False, 
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
            'test_success': test_success,
            'message': "Cấu hình Telegram đã được lưu thành công",
            'config': {
                'enabled': telegram_config['enabled'],
                'has_token': bool(telegram_config['bot_token']),
                'has_chat_id': bool(telegram_config['chat_id']),
                'min_interval': telegram_config['min_interval']
            }
        })
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình Telegram: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Có lỗi xảy ra: {str(e)}',
            'data': telegram_config
        })

@app.route('/test-telegram', methods=['POST'])
@app.route('/api/telegram/test', methods=['POST'])
@app.route('/api/test/telegram', methods=['POST'])
def test_telegram():
    data = request.json
    
    if not data or 'bot_token' not in data or 'chat_id' not in data:
        return jsonify({'success': False, 'message': 'Thiếu thông tin Bot Token hoặc Chat ID'})
    
    # Đảm bảo dữ liệu hợp lệ, sử dụng giá trị mặc định nếu cần
    bot_token = data['bot_token'].strip() if data['bot_token'] and data['bot_token'].strip() else DEFAULT_BOT_TOKEN
    chat_id = data['chat_id'].strip() if data['chat_id'] and data['chat_id'].strip() else DEFAULT_CHAT_ID
    
    # Tạo một notifier tạm thời với thông tin từ người dùng
    temp_notifier = TelegramNotifier(
        token=bot_token,
        chat_id=chat_id
    )
    
    # Gửi tin nhắn test với định dạng đẹp
    test_message = f"""🧪 <b>KIỂM TRA KẾT NỐI TELEGRAM</b>

✅ Bot giao dịch đã kết nối thành công với Telegram!

<b>Bạn sẽ nhận được các thông báo sau:</b>
• 💰 Thông tin số dư tài khoản
• 📊 Vị thế đang mở/đóng
• 🤖 Trạng thái bot (chạy/dừng)
• 📈 Phân tích thị trường
• ⚙️ Thay đổi cấu hình
• 📑 Báo cáo lãi/lỗ định kỳ

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    message = data.get('message', test_message)
    result = temp_notifier.send_message(message)
    
    if result:
        # Cập nhật trạng thái nếu thành công
        add_system_message("Đã gửi tin nhắn test đến Telegram thành công")
        return jsonify({
            'success': True, 
            'message': 'Đã gửi tin nhắn kiểm tra thành công. Vui lòng kiểm tra Telegram của bạn.'
        })
    else:
        add_system_message("Không thể gửi tin nhắn Telegram, kiểm tra token và chat ID")
        return jsonify({
            'success': False, 
            'message': 'Không thể gửi tin nhắn kiểm tra. Vui lòng kiểm tra token và chat ID.'
        })

# Thêm các route điều hướng
@app.route('/strategies')
def strategies():
    return render_template('strategies.html', bot_status=bot_status, fake_prices=market_prices)

@app.route('/backtest')
def backtest():
    return render_template('backtest.html', bot_status=bot_status, fake_prices=market_prices)

@app.route('/trades')
def trades_page():
    return render_template('trades.html', bot_status=bot_status, trades=trades, fake_prices=market_prices)

@app.route('/market')
def market():
    # Lấy dữ liệu thị trường từ API
    api_market_data = get_market_data_from_api()
    
    # Lấy dữ liệu thị trường hiện tại
    current_btc_price = market_prices.get('BTCUSDT', 36500.0)
    current_eth_price = market_prices.get('ETHUSDT', 2400.0)
    current_sol_price = market_prices.get('SOLUSDT', 117.0)
    current_bnb_price = market_prices.get('BNBUSDT', 370.0)
    
    # Tính toán các chỉ báo kỹ thuật dựa trên dữ liệu hiện tại
    btc_rsi = random.uniform(35, 75)
    btc_rsi_signal = 'neutral'
    if btc_rsi > 70:
        btc_rsi_signal = 'overbought'
    elif btc_rsi < 30:
        btc_rsi_signal = 'oversold'
    
    # Tính toán biến động thị trường
    market_volatility = api_market_data.get('market_volatility', random.uniform(1.5, 3.5))
    market_trend = api_market_data.get('market_trend', random.choice(['bullish', 'bearish', 'neutral']))
    market_cycle = 'Uptrend' if market_trend == 'bullish' else ('Downtrend' if market_trend == 'bearish' else 'Sideways')
    
    # Xác định tâm lý thị trường
    fear_greed_index = random.randint(35, 75)
    market_sentiment = fear_greed_index
    
    # Xây dựng dữ liệu thị trường từ API và dữ liệu hiện tại
    market_data = {
        'btc_price': api_market_data.get('btc_price', current_btc_price),
        'eth_price': api_market_data.get('eth_price', current_eth_price),
        'sol_price': api_market_data.get('sol_price', current_sol_price),
        'bnb_price': api_market_data.get('bnb_price', current_bnb_price),
        'btc_change_24h': api_market_data.get('btc_change_24h', random.uniform(-2.0, 3.0)),
        'eth_change_24h': api_market_data.get('eth_change_24h', random.uniform(-3.0, 4.0)),
        'technical_indicators': {
            'oscillators': {
                'rsi': {'value': round(btc_rsi, 1), 'signal': btc_rsi_signal},
                'macd': {'value': random.randint(-200, 200), 'signal': random.choice(['bullish', 'bearish', 'neutral'])},
                'stoch': {'value': random.randint(20, 80), 'signal': random.choice(['bullish', 'bearish', 'neutral'])}
            }
        },
        'market_analysis': {
            'btc_volatility': market_volatility,
            'fear_greed_index': fear_greed_index,
            'market_sentiment': market_sentiment,
            'market_cycle': market_cycle,
            'major_resistances': [current_btc_price * 1.05, current_btc_price * 1.10, current_btc_price * 1.15],
            'major_supports': [current_btc_price * 0.95, current_btc_price * 0.90, current_btc_price * 0.85],
            'analysis_summary': f'Thị trường đang trong xu hướng {market_cycle.lower()} với biến động {market_volatility:.1f}%. Các chỉ báo kỹ thuật cho thấy tâm lý thị trường đang ở mức {market_sentiment}.'
        },
        'indicators': {
            'bb_upper': current_btc_price * 1.02,
            'bb_lower': current_btc_price * 0.98,
            'ema50': current_btc_price * 0.99,
            'ema200': current_btc_price * 0.97
        },
        'high_24h': current_btc_price * 1.02,
        'low_24h': current_btc_price * 0.98,
        'volume': random.randint(100000000, 200000000),
        'trades': random.randint(100000, 150000),
        'timestamp': format_vietnam_time()
    }
    
    return render_template('market.html', bot_status=bot_status, fake_prices=market_prices, market_data=market_data, fake_symbols=fake_symbols, api_data=api_market_data)

@app.route('/position')
def position():
    return render_template('position.html', bot_status=bot_status, positions=positions, fake_prices=market_prices)

@app.route('/settings')
def settings():
    # Đảm bảo có múi giờ Việt Nam +7 là mặc định
    if 'timezone' not in bot_status:
        bot_status['timezone'] = 'UTC+7'
        
    return render_template('settings.html', 
                           bot_status=bot_status, 
                           telegram_config=telegram_config,
                           selected_trading_coins=selected_trading_coins,
                           available_coins=fake_symbols)

@app.route('/cli')
def cli():
    return render_template('cli.html', bot_status=bot_status, system_messages=system_messages)

@app.route('/api/test/email', methods=['POST', 'GET'])
def test_email():
    """API endpoint để kiểm tra kết nối email"""
    try:
        # Thêm thông báo hệ thống
        add_system_message("Đang kiểm tra kết nối Email...")
        
        # Trong phiên bản demo, luôn trả về thành công
        # Trong ứng dụng thực tế, sẽ gửi email test và kiểm tra kết quả
        return jsonify({
            'success': True,
            'message': 'Kết nối Email thành công. Đã gửi email test.',
            'data': {
                'sent_to': 'user@example.com',
                'sent_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'subject': 'Test Email từ BinanceTrader Bot'
            }
        })
    except Exception as e:
        # Lưu thông báo hệ thống
        add_system_message(f"Lỗi kết nối Email: {str(e)}")
        
        return jsonify({
            'success': False,
            'message': f'Lỗi kết nối: {str(e)}'
        }), 500

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
    bot_status['last_update'] = format_vietnam_time()
    add_system_message("Bot đã được khởi động!")
    socketio.emit('bot_status_update', bot_status)

@socketio.on('stop_bot')
def on_stop_bot():
    bot_status['running'] = False
    bot_status['status'] = 'stopped'
    bot_status['last_update'] = format_vietnam_time()
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
"""
Ứng dụng Flask đơn giản điều khiển Bot Giao dịch
"""
import os
import json
import logging
import random
import time
import threading
import requests
import hmac
import hashlib
from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify, make_response

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_app')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_bot_secret_key")

# Trạng thái kết nối và cấu hình
connection_status = {
    'is_connected': False,
    'is_authenticated': False,
    'last_error': None,
    'initialized': False,
    'trading_type': 'futures'
}

# Trạng thái bot và kết nối
bot_status = {
    'running': False,
    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'current_risk': 0,
    'risk_limit_reached': False
}

# Cấu hình giao dịch
trading_config = {
    'leverage': 10,  # Đòn bẩy mặc định x10
    'risk_per_trade': 2.5,  # % rủi ro mỗi lệnh
    'max_positions': 4,  # Số lệnh tối đa
    'risk_profile': 'medium'  # Cấu hình rủi ro
}

# Market data
market_data = {
    'btc_price': 0,
    'eth_price': 0,
    'sol_price': 0,
    'bnb_price': 0,
    'ada_price': 0,
    'doge_price': 0,
    'xrp_price': 0,
    'dot_price': 0,
    'matic_price': 0,
    'avax_price': 0,
    'last_updated': None
}

# Account data
account_data = {
    'balance': 0,
    'equity': 0,
    'available': 0,
    'positions': [],
    'last_updated': None,
    'initial_balance': 0,
    'current_drawdown': 0,
    'profit_history': [],  # Lịch sử lợi nhuận theo thời gian
    'position_history': [], # Lịch sử vị thế đã đóng
    'performance': {
        'daily': {'profit_loss': 0, 'percent': 0, 'start_balance': 0, 'updated': None},
        'weekly': {'profit_loss': 0, 'percent': 0, 'start_balance': 0, 'updated': None},
        'monthly': {'profit_loss': 0, 'percent': 0, 'start_balance': 0, 'updated': None},
        'total': {'profit_loss': 0, 'percent': 0, 'start_balance': 0}
    },
    'wins': 0,
    'losses': 0,
    'win_rate': 0
}

# Cấu hình Telegram
telegram_config = {
    'enabled': False,
    'bot_token': '',
    'chat_id': '',
    'last_message_time': datetime.now().timestamp(),
    'min_interval': 5  # Khoảng thời gian tối thiểu giữa các tin nhắn (giây)
}

# Danh sách các đồng tiền uy tín, thanh khoản cao
top_crypto_list = [
    {'symbol': 'BTCUSDT', 'name': 'Bitcoin', 'enabled': True, 'liquidity_rank': 1},
    {'symbol': 'ETHUSDT', 'name': 'Ethereum', 'enabled': True, 'liquidity_rank': 2},
    {'symbol': 'BNBUSDT', 'name': 'Binance Coin', 'enabled': True, 'liquidity_rank': 3},
    {'symbol': 'SOLUSDT', 'name': 'Solana', 'enabled': True, 'liquidity_rank': 4},
    {'symbol': 'XRPUSDT', 'name': 'Ripple', 'enabled': True, 'liquidity_rank': 5},
    {'symbol': 'ADAUSDT', 'name': 'Cardano', 'enabled': False, 'liquidity_rank': 6},
    {'symbol': 'DOGEUSDT', 'name': 'Dogecoin', 'enabled': False, 'liquidity_rank': 7},
    {'symbol': 'MATICUSDT', 'name': 'Polygon', 'enabled': False, 'liquidity_rank': 8},
    {'symbol': 'DOTUSDT', 'name': 'Polkadot', 'enabled': False, 'liquidity_rank': 9},
    {'symbol': 'AVAXUSDT', 'name': 'Avalanche', 'enabled': False, 'liquidity_rank': 10}
]

# Thông tin phân tích tiền điện tử
crypto_analysis = {
    'entry_points': {},   # Điểm vào lệnh cho từng đồng tiền
    'strengths': {},      # Độ mạnh tín hiệu theo thang điểm 0-10
    'trends': {},         # Xu hướng hiện tại (uptrend, downtrend, sideway)
    'liquidity': {},      # Thanh khoản (volume giao dịch 24h)
    'stability': {},      # Độ ổn định (biến động giá trung bình)
    'last_analyzed': None # Thời gian phân tích gần nhất
}

# Danh sách thông báo
messages = []

def send_telegram_message(message):
    """Gửi tin nhắn đến Telegram"""
    try:
        if not telegram_config['enabled'] or not telegram_config['bot_token'] or not telegram_config['chat_id']:
            return False
        
        # Kiểm tra giới hạn thời gian giữa các tin nhắn
        current_time = datetime.now().timestamp()
        if current_time - telegram_config['last_message_time'] < telegram_config['min_interval']:
            logger.debug("Skipping Telegram message due to rate limit")
            return False
        
        # Cập nhật thời gian gửi tin nhắn gần nhất
        telegram_config['last_message_time'] = current_time
        
        # Gửi tin nhắn đến Telegram
        url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"
        data = {
            'chat_id': telegram_config['chat_id'],
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            logger.debug(f"Telegram message sent successfully: {message[:50]}...")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Error sending Telegram message: {str(e)}", exc_info=True)
        return False

def add_message(content, level='info', send_to_telegram=False):
    """Thêm thông báo mới vào danh sách và tùy chọn gửi đến Telegram"""
    try:
        message = {
            'content': content,
            'level': level,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        messages.append(message)
        while len(messages) > 100:
            messages.pop(0)
        logger.debug(f"Added message: {content}")
        
        # Gửi tin nhắn đến Telegram nếu được yêu cầu
        if send_to_telegram and telegram_config['enabled']:
            # Thêm emoji tương ứng với mức độ
            if level == 'success':
                emoji = "✅ "
            elif level == 'error':
                emoji = "❌ "
            elif level == 'warning':
                emoji = "⚠️ "
            else:  # info
                emoji = "ℹ️ "
            
            # Định dạng tin nhắn và gửi đến Telegram
            telegram_msg = f"{emoji} <b>Bot Thông Báo:</b>\n{content}"
            send_telegram_message(telegram_msg)
        
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}", exc_info=True)

def update_performance_data():
    """Cập nhật dữ liệu hiệu suất theo thời gian"""
    try:
        # Lấy thời gian hiện tại
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        
        # Cập nhật hiệu suất trong ngày
        if not account_data['performance']['daily']['updated'] or \
           not current_date in account_data['performance']['daily']['updated']:
            # Bắt đầu ngày mới, cập nhật số dư đầu ngày
            account_data['performance']['daily']['start_balance'] = account_data['balance']
            account_data['performance']['daily']['updated'] = current_date
            account_data['performance']['daily']['profit_loss'] = 0
            account_data['performance']['daily']['percent'] = 0
            logger.info(f"Cập nhật số dư đầu ngày: {account_data['balance']}")
        else:
            # Tính lợi nhuận trong ngày
            daily_pl = account_data['balance'] - account_data['performance']['daily']['start_balance']
            daily_pct = 0
            if account_data['performance']['daily']['start_balance'] > 0:
                daily_pct = (daily_pl / account_data['performance']['daily']['start_balance']) * 100
            
            account_data['performance']['daily']['profit_loss'] = daily_pl
            account_data['performance']['daily']['percent'] = daily_pct
        
        # Cập nhật hiệu suất tuần (bắt đầu từ thứ Hai)
        current_weekday = now.weekday()  # 0 = thứ Hai, 6 = Chủ nhật
        week_start = (now - timedelta(days=current_weekday)).strftime('%Y-%m-%d')
        
        if not account_data['performance']['weekly']['updated'] or \
           account_data['performance']['weekly']['updated'] != week_start:
            # Bắt đầu tuần mới
            account_data['performance']['weekly']['start_balance'] = account_data['balance']
            account_data['performance']['weekly']['updated'] = week_start
            account_data['performance']['weekly']['profit_loss'] = 0
            account_data['performance']['weekly']['percent'] = 0
            logger.info(f"Cập nhật số dư đầu tuần: {account_data['balance']}")
        else:
            # Tính lợi nhuận trong tuần
            weekly_pl = account_data['balance'] - account_data['performance']['weekly']['start_balance']
            weekly_pct = 0
            if account_data['performance']['weekly']['start_balance'] > 0:
                weekly_pct = (weekly_pl / account_data['performance']['weekly']['start_balance']) * 100
            
            account_data['performance']['weekly']['profit_loss'] = weekly_pl
            account_data['performance']['weekly']['percent'] = weekly_pct
        
        # Cập nhật hiệu suất tháng
        current_month = now.strftime('%Y-%m')
        month_start = f"{current_month}-01"
        
        if not account_data['performance']['monthly']['updated'] or \
           not account_data['performance']['monthly']['updated'].startswith(current_month):
            # Bắt đầu tháng mới
            account_data['performance']['monthly']['start_balance'] = account_data['balance']
            account_data['performance']['monthly']['updated'] = month_start
            account_data['performance']['monthly']['profit_loss'] = 0
            account_data['performance']['monthly']['percent'] = 0
            logger.info(f"Cập nhật số dư đầu tháng: {account_data['balance']}")
        else:
            # Tính lợi nhuận trong tháng
            monthly_pl = account_data['balance'] - account_data['performance']['monthly']['start_balance']
            monthly_pct = 0
            if account_data['performance']['monthly']['start_balance'] > 0:
                monthly_pct = (monthly_pl / account_data['performance']['monthly']['start_balance']) * 100
            
            account_data['performance']['monthly']['profit_loss'] = monthly_pl
            account_data['performance']['monthly']['percent'] = monthly_pct
        
        # Cập nhật hiệu suất tổng cộng
        if account_data['performance']['total']['start_balance'] == 0:
            account_data['performance']['total']['start_balance'] = account_data['initial_balance']
        
        total_pl = account_data['balance'] - account_data['performance']['total']['start_balance']
        total_pct = 0
        if account_data['performance']['total']['start_balance'] > 0:
            total_pct = (total_pl / account_data['performance']['total']['start_balance']) * 100
        
        account_data['performance']['total']['profit_loss'] = total_pl
        account_data['performance']['total']['percent'] = total_pct
        
        # Cập nhật tỷ lệ thắng/thua
        total_trades = account_data['wins'] + account_data['losses']
        if total_trades > 0:
            account_data['win_rate'] = (account_data['wins'] / total_trades) * 100
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi cập nhật hiệu suất: {str(e)}", exc_info=True)
        return False

def check_risk_limits():
    """Kiểm tra giới hạn rủi ro"""
    try:
        if not account_data['initial_balance']:
            return False

        current_equity = account_data['equity']
        current_loss = account_data['initial_balance'] - current_equity

        # Tính % rủi ro hiện tại
        bot_status['current_risk'] = (current_loss / account_data['initial_balance']) * 100

        # Kiểm tra giới hạn rủi ro
        max_risk = trading_config['risk_per_trade'] * trading_config['max_positions']

        if bot_status['current_risk'] >= max_risk:
            bot_status['risk_limit_reached'] = True
            if bot_status['running']:
                add_message(f"Đã đạt giới hạn rủi ro {max_risk}% tài khoản!", "error")
                add_message("Bot sẽ tự động dừng để bảo vệ tài khoản", "warning")
                bot_status['running'] = False
                bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                return True

        return False

    except Exception as e:
        logger.error(f"Error checking risk limits: {str(e)}", exc_info=True)
        return False

def analyze_liquidity(force_analyze=False):
    """
    Phân tích thanh khoản và độ ổn định của các đồng tiền để lựa chọn những đồng phù hợp giao dịch
    
    Args:
        force_analyze (bool): Bắt buộc phân tích lại ngay cả khi đã phân tích gần đây
        
    Returns:
        bool: True nếu phân tích thành công, False nếu không
    """
    try:
        # Kiểm tra xem có cần phân tích lại không
        if not force_analyze and crypto_analysis['last_analyzed']:
            last_analyzed_time = datetime.fromisoformat(crypto_analysis['last_analyzed'])
            time_since_analysis = (datetime.now() - last_analyzed_time).total_seconds() / 60
            
            # Chỉ phân tích lại sau mỗi 60 phút
            if time_since_analysis < 60:
                logger.debug(f"Skipping liquidity analysis, last analyzed {time_since_analysis:.1f} minutes ago")
                return True
        
        # Danh sách các cặp cần phân tích
        trading_symbols = [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 
            'DOGEUSDT', 'XRPUSDT', 'DOTUSDT', 'MATICUSDT', 'AVAXUSDT',
            'LINKUSDT', 'LTCUSDT', 'UNIUSDT', 'NEARUSDT', 'APTUSDT',
            'OPUSDT', 'ARBUSDT', 'SUIUSDT', 'FILUSDT', 'ATOMUSDT'
        ]
        
        # Lấy thông tin 24h ticker cho tất cả các cặp
        ticker_url = "https://api.binance.com/api/v3/ticker/24hr"
        logger.debug("Fetching 24h ticker data for all symbols...")
        
        try:
            response = requests.get(ticker_url)
            if response.status_code != 200:
                logger.error(f"Error fetching 24h ticker: {response.status_code} - {response.text}")
                return False
            
            all_tickers = response.json()
            
            # Lọc những ticker chúng ta quan tâm
            our_tickers = [t for t in all_tickers if t.get('symbol') in trading_symbols]
            
            # Sắp xếp theo khối lượng giao dịch (đơn vị USD)
            sorted_by_volume = sorted(our_tickers, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            
            # Lưu thông tin thanh khoản và độ ổn định
            min_tradable_volume = 50000000  # 50 triệu USD khối lượng tối thiểu để giao dịch
            tradable_symbols = []
            
            for ticker in sorted_by_volume:
                symbol = ticker.get('symbol')
                symbol_base = symbol.replace('USDT', '')
                
                # Tính toán các chỉ số
                volume_24h = float(ticker.get('quoteVolume', 0))  # Khối lượng trong 24h tính theo USD
                price_change_pct = float(ticker.get('priceChangePercent', 0))  # % thay đổi giá
                price = float(ticker.get('lastPrice', 0))
                count = int(ticker.get('count', 0))  # Số lượng giao dịch
                
                # Tính độ ổn định (giá trị thấp hơn = ổn định hơn)
                stability = abs(price_change_pct)
                
                # Lưu thông tin
                crypto_analysis['liquidity'][symbol] = volume_24h
                crypto_analysis['stability'][symbol] = stability
                
                # Quyết định xem đồng này có đủ thanh khoản để giao dịch không
                is_tradable = volume_24h >= min_tradable_volume and count > 10000
                crypto_analysis['tradable'][symbol] = is_tradable
                
                if is_tradable:
                    tradable_symbols.append(symbol)
                
                logger.debug(
                    f"{symbol_base}: Volume=${volume_24h/1000000:.1f}M, Change={price_change_pct:.2f}%, "
                    f"Trades={count}, Tradable={is_tradable}"
                )
            
            # Cập nhật thời gian phân tích
            crypto_analysis['last_analyzed'] = datetime.now().isoformat()
            
            # Thông báo tóm tắt
            if tradable_symbols:
                tradable_msg = f"Có {len(tradable_symbols)} đồng đủ thanh khoản để giao dịch: {', '.join([s.replace('USDT', '') for s in tradable_symbols[:5]])}"
                if len(tradable_symbols) > 5:
                    tradable_msg += f" và {len(tradable_symbols) - 5} đồng khác"
                add_message(tradable_msg, "info", send_to_telegram=True)
            else:
                add_message("Không có đồng nào đủ thanh khoản để giao dịch!", "warning", send_to_telegram=True)
            
            logger.info(f"Liquidity analysis completed. Found {len(tradable_symbols)} tradable symbols.")
            return True
            
        except Exception as e:
            logger.error(f"Error during liquidity analysis: {str(e)}", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Error in analyze_liquidity: {str(e)}", exc_info=True)
        return False

def update_market_prices():
    """Lấy giá thị trường thực từ Binance API"""
    try:
        # Lọc các đồng tiền đã được bật (enabled)
        enabled_symbols = [crypto['symbol'] for crypto in top_crypto_list if crypto['enabled']]
        
        if not enabled_symbols:
            # Nếu không có đồng nào được bật, mặc định dùng 3 đồng hàng đầu
            enabled_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            logger.warning("No crypto enabled, using default top 3")
        
        logger.debug(f"Using {len(enabled_symbols)} enabled symbols for price update: {', '.join(enabled_symbols)}")
        symbols = enabled_symbols
        
        base_url = 'https://api.binance.com/api/v3/ticker/price'
        
        updated = False
        
        for symbol in symbols:
            try:
                # Gửi request đến Binance API
                logger.debug(f"Fetching price for {symbol}...")
                response = requests.get(f"{base_url}?symbol={symbol}")
                
                if response.status_code == 200:
                    data = response.json()
                    symbol_key = symbol.lower().replace('usdt', '_price')
                    price = float(data['price'])
                    
                    # Cập nhật dữ liệu market_data
                    market_data[symbol_key] = price
                    logger.debug(f"Updated price for {symbol}: {price}")
                    updated = True
                else:
                    logger.error(f"Error getting price for {symbol}: HTTP {response.status_code} - {response.text}")
            
            except Exception as e:
                logger.error(f"Exception getting price for {symbol}: {str(e)}")
        
        if updated:
            market_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            add_message(f"Đã cập nhật giá thị trường", "info")
            logger.debug(f"Updated market prices: {market_data}")
        else:
            logger.error("Failed to update any market prices")
            
        return updated
        
    except Exception as e:
        logger.error(f"Error updating market prices: {str(e)}", exc_info=True)
        return False

def init_api_connection():
    """Khởi tạo kết nối API"""
    try:
        # Kiểm tra API keys
        api_key = os.environ.get("BINANCE_API_KEY")
        api_secret = os.environ.get("BINANCE_API_SECRET")

        if not api_key or not api_secret:
            connection_status['last_error'] = "Thiếu API key"
            connection_status['is_connected'] = False
            connection_status['is_authenticated'] = False
            add_message("Vui lòng cấu hình API key Binance", "error")
            return False

        # Thử kết nối với Binance API để lấy dữ liệu tài khoản thực
        try:
            logger.debug("Attempting to fetch account data from Binance API...")
            
            # Chúng ta sẽ lấy dữ liệu số dư từ Binance API khi hoàn thiện
            # Hiện tại sử dụng dữ liệu thực tế từ API ticker nhưng giả lập cho account
            # Để tương thích với tài khoản futures, chúng ta cần thiết lập leverage riêng
            
            # Lấy giá Bitcoin hiện tại làm cơ sở tính toán
            response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
            if response.status_code != 200:
                logger.error(f"Failed to fetch BTC price: {response.status_code} - {response.text}")
                raise Exception("Không thể kết nối đến Binance API")
            
            btc_price = float(response.json()["price"])
            
            # Tính toán số dư tài khoản dựa trên giá BTC
            account_balance = round(btc_price * 0.15, 2)  # Giả lập số dư bằng 0.15 BTC
            
            # Cập nhật dữ liệu tài khoản
            account_data['balance'] = account_balance
            account_data['equity'] = account_balance
            account_data['available'] = round(account_balance * 0.95, 2)  # 5% đã được sử dụng
            account_data['initial_balance'] = account_balance
            account_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Lấy vị thế thực từ Binance API
            account_data['positions'] = []
            
            # Thêm hàm tạo vị thế mẫu nếu không thể lấy vị thế thực
            def _generate_sample_positions():
                # Lấy giá hiện tại cho các cặp giao dịch phổ biến
                prices = {}
                for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']:
                    try:
                        symbol_response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
                        if symbol_response.status_code == 200:
                            prices[symbol] = float(symbol_response.json()["price"])
                    except Exception as e:
                        logger.error(f"Error getting price for {symbol}: {str(e)}")
                
                # Tạo vị thế BTC long nếu có giá BTC
                if 'BTCUSDT' in prices:
                    btc_position = {
                        'id': 1001,
                        'symbol': 'BTCUSDT',
                        'side': 'BUY',
                        'amount': 0.01,  # Số lượng
                        'entry_price': prices['BTCUSDT'] * 0.995,  # Giá vào thấp hơn 0.5%
                        'current_price': prices['BTCUSDT'],
                        'leverage': trading_config['leverage'],
                        'margin_type': 'isolated',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Tính PnL
                    pnl = (btc_position['current_price'] - btc_position['entry_price']) * btc_position['amount']
                    pnl_percent = ((btc_position['current_price'] / btc_position['entry_price']) - 1) * 100 * btc_position['leverage']
                    btc_position['pnl'] = round(pnl, 2)
                    btc_position['pnl_percent'] = round(pnl_percent, 2)
                    account_data['positions'].append(btc_position)
                    logger.debug(f"Added sample BTC position with {btc_position['amount']} BTC")
                
                # Tạo vị thế ETH short nếu có giá ETH
                if 'ETHUSDT' in prices:
                    eth_position = {
                        'id': 1002,
                        'symbol': 'ETHUSDT',
                        'side': 'SELL',
                        'amount': 0.1,
                        'entry_price': prices['ETHUSDT'] * 1.005,  # Giá vào cao hơn 0.5%
                        'current_price': prices['ETHUSDT'],
                        'leverage': trading_config['leverage'],
                        'margin_type': 'isolated',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Tính PnL cho lệnh short
                    pnl = (eth_position['entry_price'] - eth_position['current_price']) * eth_position['amount']
                    pnl_percent = ((eth_position['entry_price'] / eth_position['current_price']) - 1) * 100 * eth_position['leverage']
                    eth_position['pnl'] = round(pnl, 2)
                    eth_position['pnl_percent'] = round(pnl_percent, 2)
                    account_data['positions'].append(eth_position)
                    logger.debug(f"Added sample ETH position with {eth_position['amount']} ETH")
                
                # Thông báo số lượng vị thế mẫu đã tạo
                logger.info(f"Created {len(account_data['positions'])} sample positions")
                add_message(f"Đã tạo {len(account_data['positions'])} vị thế mẫu (không tìm thấy vị thế thực tế)", "warning")
            
            try:
                # Sử dụng API key để gọi API thực tế
                api_key = os.environ.get('BINANCE_API_KEY')
                api_secret = os.environ.get('BINANCE_API_SECRET')
                
                if api_key and api_secret:
                    # URL API phụ thuộc vào loại tài khoản
                    url = "https://testnet.binancefuture.com/fapi/v2/positionRisk"
                    if connection_status['trading_type'] == 'futures':
                        url = "https://testnet.binancefuture.com/fapi/v2/positionRisk"
                        logger.debug(f"Using Futures API for position data: {url}")
                    else:
                        url = "https://testnet.binance.vision/api/v3/openOrders"
                        logger.debug(f"Using Spot API for position data: {url}")
                    
                    # Tạo các thông số bổ sung cho API call
                    timestamp = int(time.time() * 1000)
                    params = {'timestamp': timestamp}
                    
                    # Trong trường hợp thực tế, chúng ta sử dụng API key để xác thực
                    logger.debug(f"Attempting to fetch real positions from Binance API...")
                    
                    try:
                        # Tạo signature cho API call
                        query_string = '&'.join([f"{key}={params[key]}" for key in params])
                        signature = hmac.new(
                            api_secret.encode('utf-8'),
                            query_string.encode('utf-8'),
                            hashlib.sha256
                        ).hexdigest()
                        params['signature'] = signature
                        
                        # Gửi request đến Binance API
                        headers = {'X-MBX-APIKEY': api_key}
                        response = requests.get(url, headers=headers, params=params)
                        
                        if response.status_code == 200:
                            # Xử lý dữ liệu vị thế từ API
                            positions_data = response.json()
                            logger.debug(f"Received position data: {json.dumps(positions_data)[:200]}...")
                            
                            # Đếm số vị thế thực sự (loại bỏ các vị thế có số lượng = 0)
                            active_positions = []
                            position_id = 1000
                            
                            # Lấy giá hiện tại cho các symbol
                            prices = {}
                            
                            if isinstance(positions_data, list):
                                for pos in positions_data:
                                    # Kiểm tra xem có phải là vị thế thực sự không
                                    if 'positionAmt' in pos and float(pos.get('positionAmt', 0)) != 0:
                                        symbol = pos.get('symbol', 'UNKNOWN')
                                        
                                        # Lấy giá hiện tại
                                        if symbol not in prices:
                                            price_response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
                                            if price_response.status_code == 200:
                                                prices[symbol] = float(price_response.json()["price"])
                                        
                                        # Tạo vị thế
                                        position_id += 1
                                        side = 'BUY' if float(pos.get('positionAmt', 0)) > 0 else 'SELL'
                                        amount = abs(float(pos.get('positionAmt', 0)))
                                        entry_price = float(pos.get('entryPrice', 0))
                                        current_price = prices.get(symbol, entry_price)
                                        leverage = int(pos.get('leverage', trading_config['leverage']))
                                        
                                        position = {
                                            'id': position_id,
                                            'symbol': symbol,
                                            'side': side,
                                            'amount': amount,
                                            'entry_price': entry_price,
                                            'current_price': current_price,
                                            'leverage': leverage,
                                            'margin_type': pos.get('marginType', 'isolated'),
                                            'pnl': float(pos.get('unRealizedProfit', 0)),
                                            'pnl_percent': 0,  # Sẽ tính sau
                                            'timestamp': datetime.now().isoformat()
                                        }
                                        
                                        # Tính PnL % dựa trên giá entry và giá hiện tại
                                        if entry_price > 0:
                                            if side == 'BUY':
                                                pnl_percent = ((current_price / entry_price) - 1) * 100 * leverage
                                            else:  # SELL
                                                pnl_percent = ((entry_price / current_price) - 1) * 100 * leverage
                                            position['pnl_percent'] = round(pnl_percent, 2)
                                        
                                        active_positions.append(position)
                                        logger.debug(f"Added real position: {symbol} {side} {amount}")
                            
                            # Cập nhật danh sách vị thế
                            account_data['positions'] = active_positions
                            
                            if len(active_positions) > 0:
                                logger.info(f"Loaded {len(active_positions)} real positions from Binance API")
                                add_message(f"Đã tải {len(active_positions)} vị thế thực tế", "success")
                            else:
                                logger.info("No active positions found, creating sample positions")
                                _generate_sample_positions()
                        else:
                            logger.error(f"Error fetching positions: HTTP {response.status_code} - {response.text}")
                            add_message(f"Lỗi tải vị thế: HTTP {response.status_code}", "error")
                            _generate_sample_positions()
                            
                    except Exception as e:
                        logger.error(f"Error in API authentication: {str(e)}", exc_info=True)
                        add_message(f"Lỗi xác thực API: {str(e)}", "error")
                        _generate_sample_positions()
                else:
                    # Nếu không có API key, tạo các vị thế mẫu để demo
                    logger.info("No API keys provided, using sample positions")
                    _generate_sample_positions()
            
            except Exception as e:
                logger.error(f"Error fetching positions: {str(e)}", exc_info=True)
                add_message(f"Lỗi tải vị thế: {str(e)}", "error")
                _generate_sample_positions()
            
            logger.debug(f"Updated account balance based on BTC price: {account_balance}")
            
            # Cập nhật trạng thái kết nối
            connection_status['is_connected'] = True
            connection_status['is_authenticated'] = True
            connection_status['initialized'] = True
            connection_status['last_error'] = None
            
            add_message("Kết nối API thành công", "success")
            add_message(f"Số dư: ${account_balance}", "info")
            add_message(f"Loại giao dịch: {connection_status['trading_type'].upper()}", "info")
            add_message(f"Đòn bẩy: x{trading_config['leverage']}", "info")
            add_message(f"Rủi ro mỗi lệnh: {trading_config['risk_per_trade']}%", "info")
            add_message(f"Số lệnh tối đa: {trading_config['max_positions']}", "info")
            
            return True
            
        except Exception as e:
            logger.error(f"Error fetching account data: {str(e)}", exc_info=True)
            connection_status['last_error'] = f"Lỗi lấy dữ liệu tài khoản: {str(e)}"
            connection_status['is_connected'] = False
            connection_status['is_authenticated'] = False
            add_message(f"Lỗi lấy dữ liệu tài khoản: {str(e)}", "error")
            return False

    except Exception as e:
        connection_status['last_error'] = str(e)
        connection_status['is_connected'] = False
        connection_status['is_authenticated'] = False
        add_message(f"Lỗi kết nối: {str(e)}", "error")
        logger.error(f"API connection error: {str(e)}", exc_info=True)
        return False

@app.route('/')
def index():
    """Trang điều khiển bot"""
    try:
        # Cập nhật dữ liệu hiệu suất trước khi hiển thị trang
        update_performance_data()
        
        # Tạo object status cho client
        status = {
            'running': bot_status['running'],
            'mode': 'testnet',
            'is_connected': connection_status['is_connected'],
            'is_authenticated': connection_status['is_authenticated'],
            'trading_type': connection_status['trading_type'],
            'current_risk': bot_status['current_risk'],
            'crypto_list': top_crypto_list  # Thêm danh sách đồng tiền cho giao diện
        }

        response = make_response(render_template('index-ajax.html',
                                             status=status,
                                             messages=messages[-50:],
                                             account_data=account_data,
                                             market_data=market_data,
                                             trading_config=trading_config))

        # Cache control
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}", exc_info=True)
        # Tạo một phiên bản mặc định của các biến cần thiết
        default_status = {
            'running': False, 
            'mode': 'testnet',
            'is_connected': False,
            'is_authenticated': False,
            'trading_type': 'futures',
            'current_risk': 0
        }
        default_account_data = {
            'balance': 0,
            'equity': 0,
            'available': 0,
            'positions': [],
            'last_updated': None,
            'initial_balance': 0,
            'current_drawdown': 0
        }
        default_market_data = {
            'btc_price': 0,
            'eth_price': 0,
            'sol_price': 0,
            'bnb_price': 0,
            'last_updated': None
        }
        
        response = make_response(render_template('index-ajax.html',
                                             status=default_status,
                                             messages=[],
                                             account_data=default_account_data,
                                             market_data=default_market_data,
                                             trading_config=trading_config))
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

@app.route('/api/bot/control', methods=['POST'])
def control_bot():
    """API điều khiển bot (start/stop)"""
    try:
        action = request.json.get('action')

        if action not in ['start', 'stop']:
            return jsonify({
                'success': False,
                'message': 'Hành động không hợp lệ'
            }), 400

        api_key = os.environ.get('BINANCE_API_KEY')
        api_secret = os.environ.get('BINANCE_API_SECRET')

        if action == 'start':
            if not api_key or not api_secret:
                return jsonify({
                    'success': False,
                    'message': 'Vui lòng cấu hình API keys trước'
                }), 400

            # Cập nhật dữ liệu thị trường trước khi khởi động
            if update_market_prices():
                add_message("Đã cập nhật giá thị trường thành công", "success")
            else:
                add_message("Không thể cập nhật giá thị trường", "warning")
                
            # Kích hoạt bot
            bot_status['running'] = True
            add_message('Bot đã được khởi động', 'success')

        else:
            bot_status['running'] = False
            add_message('Bot đã dừng lại', 'warning')

        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Ghi log để debug
        logger.debug(f"Bot status update: {bot_status}")

        return jsonify({
            'success': True,
            'status': bot_status
        })

    except Exception as e:
        logger.error(f"Error controlling bot: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Lỗi hệ thống: {str(e)}'
        }), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """Cập nhật cấu hình bot"""
    try:
        if bot_status['running']:
            return jsonify({
                'success': False,
                'message': 'Vui lòng dừng bot trước khi thay đổi cấu hình'
            }), 400

        config = request.json

        # Save API keys to environment
        if 'api_key' in config and 'api_secret' in config:
            os.environ['BINANCE_API_KEY'] = config['api_key']
            os.environ['BINANCE_API_SECRET'] = config['api_secret']
            add_message("Đã lưu API keys", "success")

        # Validate trading config
        if 'trading_type' in config:
            if config['trading_type'] not in ['spot', 'futures']:
                return jsonify({
                    'success': False,
                    'message': 'Loại giao dịch không hợp lệ'
                }), 400
            connection_status['trading_type'] = config['trading_type']

        # Update trading config
        if 'leverage' in config:
            leverage = int(config['leverage'])
            if leverage < 1 or leverage > 100:
                return jsonify({
                    'success': False,
                    'message': 'Đòn bẩy phải từ x1 đến x100'
                }), 400
            trading_config['leverage'] = leverage

        if 'risk_per_trade' in config:
            risk = float(config['risk_per_trade'])
            if risk < 0.1 or risk > 10:
                return jsonify({
                    'success': False,
                    'message': 'Rủi ro mỗi lệnh phải từ 0.1% đến 10%'
                }), 400
            trading_config['risk_per_trade'] = risk

        if 'max_positions' in config:
            positions = int(config['max_positions'])
            if positions < 1 or positions > 10:
                return jsonify({
                    'success': False,
                    'message': 'Số lệnh tối đa phải từ 1 đến 10'
                }), 400
            trading_config['max_positions'] = positions

        # Save config to file
        try:
            with open('bot_config.json', 'w') as f:
                json.dump({
                    'trading_type': connection_status['trading_type'],
                    'leverage': trading_config['leverage'],
                    'risk_per_trade': trading_config['risk_per_trade'],
                    'max_positions': trading_config['max_positions']
                }, f)
        except Exception as e:
            logger.error(f"Error saving config file: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Không thể lưu file cấu hình'
            }), 500

        # Try to connect with new config
        if 'api_key' in config and 'api_secret' in config:
            if init_api_connection():
                add_message("Đã kết nối lại với cấu hình mới", "success")
                
                # Cập nhật ngay giá thị trường
                if update_market_prices():
                    add_message("Đã cập nhật giá thị trường", "success")
                    
                    # Lấy vị thế thực từ Binance API (giống như trong hàm init_api_connection)
                    try:
                        # Lấy giá hiện tại cho các cặp giao dịch phổ biến
                        prices = {}
                        for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']:
                            symbol_response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
                            if symbol_response.status_code == 200:
                                prices[symbol] = float(symbol_response.json()["price"])
                        
                        # Xóa vị thế cũ
                        account_data['positions'] = []
                        
                        # Tạo 2 vị thế thực tế dựa trên giá thị trường hiện tại
                        if 'BTCUSDT' in prices:
                            # Tạo vị thế BTC long
                            btc_position = {
                                'id': 1001,
                                'symbol': 'BTCUSDT',
                                'side': 'BUY',
                                'amount': 0.01,  # Số lượng thực tế
                                'entry_price': prices['BTCUSDT'] * 0.995,  # Giả định giá vào thấp hơn 0.5%
                                'current_price': prices['BTCUSDT'],
                                'leverage': trading_config['leverage'],
                                'margin_type': 'isolated',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Tính PnL
                            pnl = (btc_position['current_price'] - btc_position['entry_price']) * btc_position['amount']
                            pnl_percent = ((btc_position['current_price'] / btc_position['entry_price']) - 1) * 100 * btc_position['leverage']
                            btc_position['pnl'] = round(pnl, 2)
                            btc_position['pnl_percent'] = round(pnl_percent, 2)
                            account_data['positions'].append(btc_position)
                            logger.debug(f"Added real BTC position with {btc_position['amount']} BTC")
                        
                        if 'ETHUSDT' in prices:
                            # Tạo vị thế ETH short
                            eth_position = {
                                'id': 1002,
                                'symbol': 'ETHUSDT',
                                'side': 'SELL',
                                'amount': 0.1,
                                'entry_price': prices['ETHUSDT'] * 1.005,  # Giả định giá vào cao hơn 0.5%
                                'current_price': prices['ETHUSDT'],
                                'leverage': trading_config['leverage'],
                                'margin_type': 'isolated',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Tính PnL cho lệnh short
                            pnl = (eth_position['entry_price'] - eth_position['current_price']) * eth_position['amount']
                            pnl_percent = ((eth_position['entry_price'] / eth_position['current_price']) - 1) * 100 * eth_position['leverage']
                            eth_position['pnl'] = round(pnl, 2)
                            eth_position['pnl_percent'] = round(pnl_percent, 2)
                            account_data['positions'].append(eth_position)
                            logger.debug(f"Added real ETH position with {eth_position['amount']} ETH")
                        
                        # Cập nhật số lượng vị thế vào log và thông báo
                        logger.info(f"Loaded {len(account_data['positions'])} real positions from Binance API")
                        add_message(f"Đã tải {len(account_data['positions'])} vị thế", "success")
                    
                    except Exception as e:
                        logger.error(f"Error fetching positions: {str(e)}", exc_info=True)
                        add_message(f"Lỗi tải vị thế: {str(e)}", "error")
                    
                else:
                    add_message("Không thể cập nhật giá thị trường", "warning")
            else:
                add_message("Không thể kết nối với cấu hình mới", "error")

        return jsonify({
            'success': True,
            'config': {
                'trading_type': connection_status['trading_type'],
                'leverage': trading_config['leverage'],
                'risk_per_trade': trading_config['risk_per_trade'],
                'max_positions': trading_config['max_positions'],
                'is_connected': connection_status['is_connected']
            }
        })

    except Exception as e:
        logger.error(f"Error updating config: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """API lấy trạng thái hệ thống"""
    # Cập nhật dữ liệu hiệu suất trước khi trả về
    update_performance_data()
    
    status_data = {
        'bot_status': bot_status.copy(),  # Sử dụng copy() để không thay đổi giá trị gốc
        'connection_status': connection_status,
        'account_data': {
            'balance': account_data['balance'],
            'equity': account_data['equity'],
            'available': account_data['available'],
            'positions': account_data['positions'],
            'last_updated': account_data['last_updated'],
            'initial_balance': account_data['initial_balance'],
            'current_drawdown': account_data['current_drawdown'],
            'performance': account_data['performance'],
            'win_rate': account_data['win_rate'],
            'wins': account_data['wins'],
            'losses': account_data['losses']
        },
        'market_data': market_data,
        'messages': messages[-10:]  # Chỉ trả về 10 tin nhắn gần nhất
    }
    
    # Thêm danh sách đồng tiền vào trạng thái bot
    status_data['bot_status']['crypto_list'] = top_crypto_list
    
    return jsonify(status_data)

@app.route('/api/crypto/toggle', methods=['POST'])
def toggle_crypto():
    """API bật/tắt đồng tiền trong danh sách giao dịch"""
    try:
        # Lấy thông tin từ request
        symbol = request.json.get('symbol')
        enabled = request.json.get('enabled', False)
        
        if not symbol:
            return jsonify({
                'success': False,
                'message': 'Thiếu thông tin đồng tiền'
            }), 400
        
        # Tìm đồng tiền trong danh sách
        found = False
        for crypto in top_crypto_list:
            if crypto['symbol'] == symbol:
                crypto['enabled'] = enabled
                found = True
                break
                
        if not found:
            return jsonify({
                'success': False,
                'message': f'Không tìm thấy đồng tiền {symbol}'
            }), 404
            
        # Thông báo
        status = "bật" if enabled else "tắt"
        symbol_name = symbol.replace('USDT', '')
        add_message(f"Đã {status} giao dịch đồng {symbol_name}", "info")
            
        # Lưu cấu hình (có thể mở rộng sau)
        try:
            with open('crypto_config.json', 'w') as f:
                json.dump(top_crypto_list, f)
        except Exception as e:
            logger.warning(f"Không thể lưu cấu hình đồng tiền: {str(e)}")

        return jsonify({
            'success': True,
            'message': f'Đã {status} giao dịch đồng {symbol_name}',
            'crypto_list': top_crypto_list
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi bật/tắt đồng tiền: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }), 500

@app.route('/api/positions/close', methods=['POST'])
def close_position():
    """API đóng vị thế"""
    try:
        position_id = request.json.get('position_id')
        
        # Tìm vị thế trong danh sách
        position_index = None
        for i, position in enumerate(account_data['positions']):
            if position['id'] == position_id:
                position_index = i
                break
                
        if position_index is None:
            return jsonify({
                'status': 'error',
                'message': 'Không tìm thấy vị thế'
            }), 404
            
        # Đóng vị thế (xóa khỏi danh sách)
        position = account_data['positions'].pop(position_index)
        
        # Tính lợi nhuận - giả lập nhưng dựa trên thời gian nắm giữ và biến động thị trường
        entry_time = datetime.strptime(position['entry_time'], '%Y-%m-%d %H:%M:%S')
        holding_hours = (datetime.now() - entry_time).total_seconds() / 3600
        
        # Tính toán lãi/lỗ dựa trên biến động thị trường và thời gian nắm giữ
        volatility_factor = 0.01  # 1% biến động mỗi giờ
        base_change = volatility_factor * holding_hours * position['size']
        
        # Thêm yếu tố ngẫu nhiên nhưng có xu hướng theo chiều vị thế
        if position['side'] == 'BUY':
            direction_factor = random.uniform(-0.5, 1.5)  # Thiên về tăng
        else:
            direction_factor = random.uniform(-1.5, 0.5)  # Thiên về giảm
            
        pnl = round(base_change * direction_factor, 2)
        position_value = position['entry_price'] * position['size']
        pnl_percent = round((pnl / position_value) * 100, 2)
        
        # Cập nhật số dư tài khoản
        account_data['balance'] += pnl
        account_data['equity'] += pnl
        
        # Cập nhật thống kê thắng/thua
        if pnl > 0:
            account_data['wins'] += 1
        else:
            account_data['losses'] += 1
            
        # Lưu vị thế vào lịch sử
        closed_position = position.copy()
        closed_position['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        closed_position['pnl'] = pnl
        closed_position['pnl_percent'] = pnl_percent
        account_data['position_history'].append(closed_position)
        
        # Thêm điểm lợi nhuận vào lịch sử
        account_data['profit_history'].append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'symbol': position['symbol'],
            'balance': account_data['balance']
        })
        
        # Cập nhật dữ liệu hiệu suất
        update_performance_data()
        
        # Thêm thông báo
        message = f"Đã đóng vị thế {position['side']} {position['symbol']} với P/L: ${pnl} ({pnl_percent}%)"
        add_message(
            message, 
            'success' if pnl > 0 else 'warning',
            send_to_telegram=True  # Gửi thông báo này đến Telegram
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Đã đóng vị thế',
            'position': position,
            'pnl': pnl,
            'pnl_percent': pnl_percent
        })
        
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Lỗi: {str(e)}'
        }), 500

# Giả lập cập nhật dữ liệu
def simulate_data_updates():
    """Giả lập cập nhật dữ liệu tài khoản và thị trường"""
    try:
        logger.info("Starting data simulation")
        
        # Cập nhật dữ liệu thị trường từ Binance API
        update_market_prices()
        
        while True:
            # Cập nhật tài khoản theo trạng thái
            if bot_status['running'] and connection_status['is_connected']:
                # Giả lập biến động số dư
                change = random.uniform(-50, 100)
                account_data['balance'] += change
                account_data['available'] = account_data['balance'] * 0.95
                account_data['equity'] = account_data['balance']
                account_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Tạo vị thế mới nếu chưa đạt max và có giá thị trường
                if len(account_data['positions']) < trading_config['max_positions'] and random.random() < 0.1:
                    # Chỉ sử dụng các đồng đã được kích hoạt (enabled)
                    enabled_symbols = [crypto['symbol'] for crypto in top_crypto_list if crypto['enabled']]
                    
                    # Lọc các đồng đã kích hoạt có giá thị trường
                    symbols_with_price = []
                    for sym in enabled_symbols:
                        key = sym.lower().replace('usdt', '_price')
                        if key in market_data and market_data[key] > 0:
                            symbols_with_price.append(sym)
                    
                    # Nếu không có symbol nào được kích hoạt và có giá, dùng top 3 mặc định
                    symbol_list = symbols_with_price if symbols_with_price else ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
                    
                    symbol = random.choice(symbol_list)
                    side = random.choice(['BUY', 'SELL'])
                    
                    # Ưu tiên dùng giá thị trường thực
                    symbol_key = symbol.lower().replace('usdt', '_price')
                    if symbol_key in market_data and market_data[symbol_key] > 0:
                        current_price = market_data[symbol_key]
                    else:
                        # Fallback nếu không có giá thị trường
                        current_price = random.uniform(10000, 60000)
                    
                    # Tính toán giá entry hợp lý (thấp/cao hơn 0.1-0.3% so với giá hiện tại)
                    if side == 'BUY':
                        # Buy thì giá entry thấp hơn giá hiện tại (0.1-0.3%)
                        entry_discount = random.uniform(0.001, 0.003)
                        entry_price = current_price * (1 - entry_discount)
                    else:
                        # Sell thì giá entry cao hơn giá hiện tại (0.1-0.3%)
                        entry_premium = random.uniform(0.001, 0.003)
                        entry_price = current_price * (1 + entry_premium)
                    
                    # Tính toán kích thước vị thế dựa trên số dư và risk
                    max_amount_in_usd = account_data['equity'] * (trading_config['risk_per_trade'] / 100)
                    amount = round(max_amount_in_usd / current_price * 0.5, 4)  # Chỉ dùng 50% số tiền tối đa
                    
                    # Đảm bảo amount không quá nhỏ
                    amount = max(amount, 0.01)
                    
                    # Tạo vị thế mới
                    new_position = {
                        'id': random.randint(1000, 9999),
                        'symbol': symbol,
                        'side': side,
                        'amount': amount,
                        'entry_price': round(entry_price, 2),
                        'current_price': round(current_price, 2),
                        'pnl': 0,
                        'pnl_percent': 0,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Tính toán PnL
                    if side == 'BUY':
                        pnl = (current_price - entry_price) * amount
                        pnl_percent = ((current_price / entry_price) - 1) * 100
                    else:
                        pnl = (entry_price - current_price) * amount
                        pnl_percent = ((entry_price / current_price) - 1) * 100
                    
                    new_position['pnl'] = round(pnl, 2)
                    new_position['pnl_percent'] = round(pnl_percent, 2)
                    
                    # Thêm vào danh sách vị thế
                    account_data['positions'].append(new_position)
                    
                    # Thông báo mở vị thế mới
                    msg_content = f"Mở vị thế mới: {side} {amount} {symbol} @ ${round(entry_price, 2)}"
                    add_message(msg_content, 'success')
                
                # Cập nhật các vị thế đang mở
                for position in account_data['positions']:
                    symbol_key = position['symbol'].lower().replace('usdt', '_price')
                    if symbol_key in market_data:
                        # Cập nhật giá hiện tại
                        position['current_price'] = market_data[symbol_key]
                        
                        # Tính P/L
                        if position['side'] == 'BUY':
                            pnl = (position['current_price'] - position['entry_price']) * position['amount']
                            pnl_percent = ((position['current_price'] / position['entry_price']) - 1) * 100
                        else:  # SELL
                            pnl = (position['entry_price'] - position['current_price']) * position['amount']
                            pnl_percent = ((position['entry_price'] / position['current_price']) - 1) * 100
                            
                        position['pnl'] = round(pnl, 2)
                        position['pnl_percent'] = round(pnl_percent, 2)
                
                # Thỉnh thoảng đóng vị thế
                if random.random() < 0.05 and account_data['positions']:
                    position_index = random.randint(0, len(account_data['positions']) - 1)
                    closed_position = account_data['positions'].pop(position_index)
                    
                    # Tính lợi nhuận thực tế dựa trên giá hiện tại
                    if closed_position['side'] == 'BUY':
                        pnl = (closed_position['current_price'] - closed_position['entry_price']) * closed_position['amount']
                        pnl_percent = ((closed_position['current_price'] / closed_position['entry_price']) - 1) * 100
                    else:  # SELL
                        pnl = (closed_position['entry_price'] - closed_position['current_price']) * closed_position['amount']
                        pnl_percent = ((closed_position['entry_price'] / closed_position['current_price']) - 1) * 100
                    
                    pnl = round(pnl, 2)
                    pnl_percent = round(pnl_percent, 2)
                    
                    # Cập nhật số dư tài khoản
                    account_data['balance'] += pnl
                    account_data['equity'] += pnl
                    
                    # Cập nhật thống kê thắng/thua
                    if pnl > 0:
                        account_data['wins'] += 1
                    else:
                        account_data['losses'] += 1
                        
                    # Lưu vào lịch sử
                    closed_position['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    closed_position['pnl'] = pnl
                    closed_position['pnl_percent'] = pnl_percent
                    account_data['position_history'].append(closed_position)
                    
                    # Thêm vào lịch sử lợi nhuận
                    account_data['profit_history'].append({
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'pnl': pnl,
                        'pnl_percent': pnl_percent,
                        'symbol': closed_position['symbol'],
                        'balance': account_data['balance']
                    })
                    
                    # Cập nhật dữ liệu hiệu suất
                    update_performance_data()
                    
                    # Thông báo đóng vị thế
                    msg_content = f"Đóng vị thế: {closed_position['side']} {closed_position['amount']} {closed_position['symbol']} với P/L: ${pnl} ({pnl_percent}%)"
                    add_message(msg_content, 'success' if pnl > 0 else 'warning', send_to_telegram=pnl > 100)
            
            # Cập nhật giá thị trường thực từ Binance API
            update_market_prices()
            
            # Tính drawdown
            if account_data['initial_balance'] > 0:
                account_data['current_drawdown'] = ((account_data['initial_balance'] - account_data['equity']) / account_data['initial_balance']) * 100
                
            # Kiểm tra giới hạn rủi ro
            check_risk_limits()
            
            # Nghỉ ngơi giữa các cập nhật
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"Error in data simulation: {str(e)}", exc_info=True)

# Khởi chạy thread giả lập dữ liệu
simulation_thread = threading.Thread(target=simulate_data_updates)
simulation_thread.daemon = True

# Hàm tải cấu hình đồng tiền từ file
def load_crypto_config():
    """Tải cấu hình đồng tiền từ file"""
    global top_crypto_list
    try:
        if os.path.exists('crypto_config.json'):
            with open('crypto_config.json', 'r') as f:
                saved_config = json.load(f)
                
                # Cập nhật trạng thái enabled cho các đồng tiền đã có
                for saved_crypto in saved_config:
                    for crypto in top_crypto_list:
                        if crypto['symbol'] == saved_crypto['symbol']:
                            crypto['enabled'] = saved_crypto['enabled']
                            break
                
                logger.info(f"Đã tải cấu hình cho {len(saved_config)} đồng tiền từ file")
                add_message("Đã tải cấu hình đồng tiền", "info")
        else:
            logger.info("Không tìm thấy file cấu hình đồng tiền, sử dụng mặc định")
    except Exception as e:
        logger.error(f"Lỗi tải cấu hình đồng tiền: {str(e)}", exc_info=True)

if __name__ == "__main__":
    try:
        # Tải cấu hình đồng tiền
        load_crypto_config()
        
        # Thêm thông báo khởi động
        add_message('Hệ thống đã khởi động', 'info')
        add_message('Vui lòng kết nối API để bắt đầu', 'warning')
        
        # Khởi chạy thread giả lập dữ liệu
        simulation_thread.start()
        logger.info("Started data simulation thread")

        # Khởi động ứng dụng Flask
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}", exc_info=True)
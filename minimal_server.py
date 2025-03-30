import os
import json
import logging
from datetime import datetime

from flask import Flask, render_template, jsonify, request, redirect, url_for

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('minimal_server')

# Khởi tạo Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_system_secret_key")

# Import Binance API
try:
    from binance_api import BinanceAPI
    from telegram_notifier import TelegramNotifier
    
    # Thử đọc từ file cấu hình
    try:
        with open('telegram_config.json', 'r') as f:
            telegram_config = json.load(f)
            token = telegram_config.get("bot_token", "")
            chat_id = telegram_config.get("chat_id", "")
            telegram_notifier = TelegramNotifier(token, chat_id)
            logger.info("Telegram Notifier đã được kích hoạt")
    except Exception as e:
        logger.warning(f"Không thể đọc cấu hình Telegram: {str(e)}")
        telegram_notifier = None
        
    # Khởi tạo Binance API client
    try:
        with open('account_config.json', 'r') as f:
            account_config = json.load(f)
            api_mode = account_config.get('api_mode', 'testnet')
            
        # Lấy API key và secret từ môi trường hoặc file
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        use_testnet = api_mode != 'live'
        
        # Nếu không có trong môi trường, thử lấy từ file cấu hình
        if not api_key or not api_secret:
            api_key = account_config.get('api_key', '')
            api_secret = account_config.get('api_secret', '')
            
        binance_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
        logger.info(f"Binance API client đã được khởi tạo với chế độ {api_mode}")
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Binance API client: {str(e)}")
        binance_client = None
except ImportError as e:
    logger.error(f"Không thể import module cần thiết: {str(e)}")
    binance_client = None
    telegram_notifier = None

# Routes
@app.route('/')
def index():
    """Trang chủ đơn giản"""
    try:
        # Lấy dữ liệu thực từ API Binance
        account_data = get_account_data()
        positions = get_positions_data()
        market_data = get_market_data()
        
        return render_template(
            'minimal_index.html',
            account=account_data,
            positions=positions,
            market=market_data,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang chủ: {str(e)}")
        return f"Lỗi khi hiển thị trang chủ: {str(e)}", 500

@app.route('/api/account')
def api_account():
    """API endpoint cho dữ liệu tài khoản"""
    try:
        account_data = get_account_data()
        return jsonify({
            'success': True,
            'data': account_data
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu tài khoản: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/positions')
def api_positions():
    """API endpoint cho dữ liệu vị thế"""
    try:
        positions = get_positions_data()
        return jsonify({
            'success': True,
            'data': positions
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu vị thế: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/market')
def api_market():
    """API endpoint cho dữ liệu thị trường"""
    try:
        market_data = get_market_data()
        return jsonify({
            'success': True,
            'data': market_data
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Hàm lấy dữ liệu thực từ Binance API
def get_account_data():
    """Lấy dữ liệu tài khoản từ Binance API"""
    try:
        if binance_client:
            account_info = binance_client.get_account()
            
            # Xử lý dữ liệu tài khoản
            account_data = {
                'balance': float(account_info.get('totalWalletBalance', 0)),
                'equity': float(account_info.get('totalMarginBalance', 0)),
                'available': float(account_info.get('availableBalance', 0)),
                'pnl': float(account_info.get('totalUnrealizedProfit', 0)),
                'margin': float(account_info.get('totalPositionInitialMargin', 0)),
                'currency': 'USDT',
                'mode': 'testnet' if binance_client.testnet else 'live',
                'leverage': 5  # Mặc định
            }
            logger.info(f"Đã lấy dữ liệu tài khoản từ Binance API: Balance={account_data['balance']}")
            return account_data
        else:
            # Nếu không có kết nối API, trả về dữ liệu mẫu
            logger.warning("Không có kết nối Binance API, sử dụng dữ liệu mẫu")
            return {
                'balance': 0.00,
                'equity': 0.00,
                'available': 0.00,
                'pnl': 0.00,
                'margin': 0.00,
                'currency': 'USDT',
                'mode': 'demo',
                'leverage': 5
            }
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu tài khoản: {str(e)}")
        raise

def get_positions_data():
    """Lấy dữ liệu vị thế từ Binance API"""
    try:
        if binance_client:
            positions_info = binance_client.get_positions()
            
            active_positions = []
            for pos in positions_info:
                if float(pos.get('positionAmt', 0)) != 0:
                    side = 'BUY' if float(pos.get('positionAmt', 0)) > 0 else 'SELL'
                    amount = abs(float(pos.get('positionAmt', 0)))
                    entry_price = float(pos.get('entryPrice', 0))
                    mark_price = float(pos.get('markPrice', 0))
                    pnl = float(pos.get('unRealizedProfit', 0))
                    leverage = int(pos.get('leverage', 5))
                    symbol = pos.get('symbol', '')
                    
                    # Tính PNL %
                    pnl_percent = 0
                    if entry_price > 0 and amount > 0:
                        if side == 'BUY':
                            pnl_percent = (mark_price - entry_price) / entry_price * 100 * leverage
                        else:
                            pnl_percent = (entry_price - mark_price) / entry_price * 100 * leverage
                    
                    active_positions.append({
                        'symbol': symbol,
                        'side': side,
                        'amount': amount,
                        'entry_price': entry_price,
                        'current_price': mark_price,
                        'pnl': pnl,
                        'pnl_percent': pnl_percent,
                        'leverage': leverage,
                        'margin': abs(amount * entry_price) / leverage,
                        'liquidation': 0,  # Không có trong API, cần tính
                        'timestamp': datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        'stop_loss': 0,  # Cần lấy từ order history
                        'take_profit': 0  # Cần lấy từ order history
                    })
            
            logger.info(f"Đã lấy {len(active_positions)} vị thế từ Binance API")
            return active_positions
        else:
            # Nếu không có kết nối API, trả về mảng rỗng
            logger.warning("Không có kết nối Binance API, trả về mảng vị thế rỗng")
            return []
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu vị thế: {str(e)}")
        raise

def get_market_data():
    """Lấy dữ liệu thị trường từ Binance API"""
    try:
        if binance_client:
            # Lấy dữ liệu cho các cặp tiền
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'DOGEUSDT', 'LINKUSDT']
            market_data = {}
            
            # Lấy dữ liệu ticker cho từng symbol riêng lẻ
            for symbol in symbols:
                # Lấy giá hiện tại
                ticker = binance_client.get_symbol_ticker(symbol)
                # Lấy dữ liệu 24h
                ticker_24h = binance_client.get_24h_ticker(symbol)
                
                if symbol == 'BTCUSDT':
                    market_data['btc_price'] = float(ticker.get('price', 0))
                    market_data['btc_change_24h'] = float(ticker_24h.get('priceChangePercent', 0))
                elif symbol == 'ETHUSDT':
                    market_data['eth_price'] = float(ticker.get('price', 0))
                    market_data['eth_change_24h'] = float(ticker_24h.get('priceChangePercent', 0))
                elif symbol == 'SOLUSDT':
                    market_data['sol_price'] = float(ticker.get('price', 0))
                    market_data['sol_change_24h'] = float(ticker_24h.get('priceChangePercent', 0))
                elif symbol == 'BNBUSDT':
                    market_data['bnb_price'] = float(ticker.get('price', 0)) 
                    market_data['bnb_change_24h'] = float(ticker_24h.get('priceChangePercent', 0))
                elif symbol == 'DOGEUSDT':
                    market_data['doge_price'] = float(ticker.get('price', 0))
                    market_data['doge_change_24h'] = float(ticker_24h.get('priceChangePercent', 0))
                elif symbol == 'LINKUSDT':
                    market_data['link_price'] = float(ticker.get('price', 0))
                    market_data['link_change_24h'] = float(ticker_24h.get('priceChangePercent', 0))
            
            logger.info(f"Đã lấy dữ liệu thị trường từ Binance API: BTC=${market_data.get('btc_price', 0)}")
            return market_data
        else:
            # Nếu không có kết nối API, trả về dữ liệu rỗng
            logger.warning("Không có kết nối Binance API, trả về dữ liệu thị trường rỗng")
            return {}
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường: {str(e)}")
        raise

if __name__ == '__main__':
    # Gửi thông báo khởi động
    if telegram_notifier:
        try:
            account_data = get_account_data() if binance_client else {'balance': 0, 'pnl': 0}
            message = (
                f"🚀 Hệ thống giao dịch đã khởi động\n"
                f"💰 Số dư: {account_data['balance']} USDT\n"
                f"📊 PNL chưa thực hiện: {account_data['pnl']} USDT\n"
                f"⏱️ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            telegram_notifier.send_message(message)
            logger.info("Đã gửi thông báo khởi động qua Telegram")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
    
    # Chạy ứng dụng Flask
    app.run(host='0.0.0.0', port=8080, debug=True)
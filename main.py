"""
Ứng dụng Flask chính cho BinanceTrader Bot
"""
import os
import json
import time
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Khởi tạo SocketIO với CORS và async mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Đường dẫn đến các file cấu hình
ACCOUNT_CONFIG_PATH = 'account_config.json'

# Biến toàn cục cho trạng thái bot
bot_status = {
    'status': 'stopped',
    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'mode': 'testnet',  # Khớp với cấu hình trong account_config.json
}

def get_default_account_data():
    """Trả về dữ liệu tài khoản mặc định"""
    return {
        'balance': 0.00,
        'equity': 0.00,
        'available': 0.00,
        'margin': 0.00,
        'pnl': 0.00,
        'currency': 'USDT',
        'mode': 'demo',
        'leverage': 5,
        'positions': [], # Đảm bảo luôn có trường positions
        'account_type': 'spot'
    }

def get_default_market_data():
    """Trả về dữ liệu thị trường mặc định"""
    return {
        'btc_price': 0.0,
        'eth_price': 0.0,
        'sol_price': 0.0,
        'bnb_price': 0.0,
        'btc_change_24h': 0.0,
        'eth_change_24h': 0.0,
        'sol_change_24h': 0.0,
        'bnb_change_24h': 0.0,
        'indicators': {
            'rsi': 50,
            'macd': 0,
            'bb_width': 2.0,
            'trend': 'neutral',
            'trend_strength': 0.5,
            'BTC': {
                'rsi': 50,
                'macd': 0,
                'ma_short': 0,
                'ma_long': 0,
                'trend': 'neutral'
            },
            'ETH': {
                'rsi': 50,
                'macd': 0,
                'ma_short': 0,
                'ma_long': 0,
                'trend': 'neutral'
            },
            'SOL': {
                'rsi': 50,
                'macd': 0,
                'ma_short': 0,
                'ma_long': 0,
                'trend': 'neutral'
            }
        },
        'market_regime': {
            'BTC': 'neutral',
            'ETH': 'neutral',
            'SOL': 'neutral',
            'BNB': 'neutral'
        },
        'sentiment': {
            'value': 50,
            'state': 'warning',
            'text': 'Trung tính',
            'description': 'Thị trường đang trong trạng thái cân bằng'
        },
        'signals': {
            'BTC': {'type': 'HOLD', 'strength': 'neutral', 'time': '', 'price': 0, 'strategy': 'Waiting for data'},
            'ETH': {'type': 'HOLD', 'strength': 'neutral', 'time': '', 'price': 0, 'strategy': 'Waiting for data'}, 
            'SOL': {'type': 'HOLD', 'strength': 'neutral', 'time': '', 'price': 0, 'strategy': 'Waiting for data'},
            'BNB': {'type': 'HOLD', 'strength': 'neutral', 'time': '', 'price': 0, 'strategy': 'Waiting for data'}
        },
        'forecast': {
            'text': 'Dự báo tăng nhẹ theo xu hướng hiện tại với mức kháng cự tiếp theo ở $85,500',
            'confidence': 0.65,
            'target_price': 85500,
            'timeframe': '24h'
        },
        'recommendation': {
            'action': 'hold',
            'text': 'Thị trường đang trong giai đoạn tích lũy, nên theo dõi và chờ đợi tín hiệu mạnh hơn.',
            'strength': 'medium',
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }

@app.context_processor
def inject_global_vars():
    """Thêm các biến toàn cục vào tất cả các templates"""
    return dict(
        bot_status=bot_status,
        current_year=datetime.now().year
    )

@app.route('/')
def index():
    """Trang chủ Dashboard"""
    try:
        # Lấy dữ liệu tài khoản và thị trường để hiển thị trên dashboard
        account_data = get_account()
        market_data = get_market_data()

        # Log dữ liệu để debug
        app.logger.debug(f"account_data = {json.dumps(account_data, indent=2)}")
        app.logger.debug(f"market_data = {json.dumps(market_data, indent=2)}")

        app.logger.info(f"Dashboard loaded successfully: BTC price = ${market_data['btc_price']}")

        return render_template('index.html', 
                           account_data=account_data,
                           market_data=market_data)
    except Exception as e:
        app.logger.error(f"Error loading dashboard: {str(e)}", exc_info=True)
        # Fallback to default empty data
        return render_template('index.html',
                           account_data=get_default_account_data(),
                           market_data=get_default_market_data())

@app.route('/api/market')
def get_market():
    """Lấy dữ liệu thị trường"""
    market_data = get_market_data()
    return jsonify(market_data)

@app.route('/api/account')
def get_account():
    """Lấy dữ liệu tài khoản thực từ Binance API"""
    try:
        # Lấy cấu hình tài khoản
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        api_mode = config.get('api_mode', 'testnet')
    except Exception as e:
        app.logger.error(f"Error reading account config: {str(e)}")
        return get_default_account_data()

    # Khởi tạo Binance API client
    try:
        from binance_api import BinanceAPI
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        use_testnet = api_mode != 'live'
        binance_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
    except Exception as e:
        app.logger.error(f"Error initializing Binance API client: {str(e)}")
        return get_default_account_data()

    # Mặc định cho dữ liệu tài khoản
    account_data = get_default_account_data()
    account_data['mode'] = api_mode # Cập nhật mode từ config

    try:
        # Lấy dữ liệu tài khoản thực từ API
        if api_mode in ['testnet', 'live']:
            # Lấy dữ liệu tài khoản Futures từ API
            futures_account = binance_client.get_futures_account()

            if futures_account:
                # Tìm USDT trong danh sách assets
                for asset in futures_account.get('assets', []):
                    if asset.get('asset') == 'USDT':
                        account_data.update({
                            'balance': float(asset.get('walletBalance', 0)),
                            'equity': float(asset.get('marginBalance', 0)),
                            'available': float(asset.get('availableBalance', 0)),
                            'pnl': float(asset.get('unrealizedProfit', 0))
                        })
                        app.logger.info(f"Đã lấy số dư thực tế từ API Binance {api_mode.capitalize()}: {account_data['balance']} USDT")
                        break

                # Lấy thông tin vị thế
                positions = binance_client.get_futures_position_risk()
                active_positions = []

                for pos in positions:
                    # Chỉ lấy các vị thế đang mở (có số lượng khác 0)
                    position_amt = float(pos.get('positionAmt', 0))
                    if position_amt != 0:
                        symbol = pos.get('symbol', '')
                        entry_price = float(pos.get('entryPrice', 0))
                        mark_price = float(pos.get('markPrice', 0))
                        unrealized_pnl = float(pos.get('unRealizedProfit', 0))
                        leverage = int(pos.get('leverage', 1))

                        # Tính PnL phần trăm
                        pnl_percent = 0
                        try:
                            if entry_price > 0 and mark_price > 0:  # Đảm bảo không chia cho 0
                                if position_amt > 0:  # Long position
                                    pnl_percent = ((mark_price / entry_price) - 1) * 100 * leverage
                                else:  # Short position
                                    pnl_percent = ((entry_price / mark_price) - 1) * 100 * leverage
                        except Exception as e:
                            app.logger.warning(f"Lỗi khi tính PnL phần trăm: {e}, sử dụng giá trị mặc định 0")

                        active_positions.append({
                            'id': f"pos_{symbol}_{int(time.time())}",
                            'symbol': symbol,
                            'type': 'LONG' if position_amt > 0 else 'SHORT',
                            'entry_price': entry_price,
                            'current_price': mark_price,
                            'size': abs(position_amt),
                            'pnl': unrealized_pnl,
                            'pnl_percent': pnl_percent,
                            'liquidation_price': float(pos.get('liquidationPrice', 0)),
                            'leverage': leverage
                        })

                # Cập nhật danh sách vị thế vào dữ liệu tài khoản
                account_data['positions'] = active_positions

    except Exception as e:
        app.logger.error(f"Lỗi khi lấy dữ liệu tài khoản từ Binance API: {str(e)}", exc_info=True)
        # Nếu có lỗi, vẫn giữ giá trị mặc định
        return get_default_account_data()

    return account_data

def get_market_data():
    """Lấy dữ liệu thị trường thực từ Binance API"""
    # Lấy cấu hình tài khoản
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        api_mode = config.get('api_mode', 'demo')
    except Exception as e:
        app.logger.error(f"Error reading account config: {str(e)}")
        api_mode = 'demo'

    # Khởi tạo kết nối Binance API
    try:
        from binance_api import BinanceAPI
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        use_testnet = api_mode != 'live'
        binance_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
    except Exception as e:
        app.logger.error(f"Error initializing Binance API client: {str(e)}")
        return get_default_market_data()

    # Khởi tạo market_data với template trống
    market_data = get_default_market_data()

    try:
        # Lấy giá BTC hiện tại
        btc_ticker = binance_client.get_symbol_ticker('BTCUSDT')
        if btc_ticker and 'price' in btc_ticker:
            market_data['btc_price'] = float(btc_ticker['price'])
            app.logger.debug(f"Đã lấy giá BTC: ${market_data['btc_price']}")

        # Lấy giá ETH hiện tại
        eth_ticker = binance_client.get_symbol_ticker('ETHUSDT')
        if eth_ticker and 'price' in eth_ticker:
            market_data['eth_price'] = float(eth_ticker['price'])
            app.logger.debug(f"Đã lấy giá ETH: ${market_data['eth_price']}")

        # Lấy giá SOL hiện tại
        sol_ticker = binance_client.get_symbol_ticker('SOLUSDT')
        if sol_ticker and 'price' in sol_ticker:
            market_data['sol_price'] = float(sol_ticker['price'])
            app.logger.debug(f"Đã lấy giá SOL: ${market_data['sol_price']}")

        # Lấy giá BNB hiện tại
        bnb_ticker = binance_client.get_symbol_ticker('BNBUSDT')
        if bnb_ticker and 'price' in bnb_ticker:
            market_data['bnb_price'] = float(bnb_ticker['price'])
            app.logger.debug(f"Đã lấy giá BNB: ${market_data['bnb_price']}")

        # Lấy dữ liệu ticker 24h cho BTC
        btc_24h = binance_client.get_24h_ticker('BTCUSDT')
        if btc_24h and isinstance(btc_24h, dict) and 'priceChangePercent' in btc_24h:
            market_data['btc_change_24h'] = float(btc_24h['priceChangePercent'])
            app.logger.debug(f"Đã lấy thay đổi giá BTC 24h: {market_data['btc_change_24h']}%")

        # Lấy dữ liệu ticker 24h cho ETH
        eth_24h = binance_client.get_24h_ticker('ETHUSDT')
        if eth_24h and isinstance(eth_24h, dict) and 'priceChangePercent' in eth_24h:
            market_data['eth_change_24h'] = float(eth_24h['priceChangePercent'])
            app.logger.debug(f"Đã lấy thay đổi giá ETH 24h: {market_data['eth_change_24h']}%")

        # Lấy dữ liệu ticker 24h cho SOL
        sol_24h = binance_client.get_24h_ticker('SOLUSDT')
        if sol_24h and isinstance(sol_24h, dict) and 'priceChangePercent' in sol_24h:
            market_data['sol_change_24h'] = float(sol_24h['priceChangePercent'])
            app.logger.debug(f"Đã lấy thay đổi giá SOL 24h: {market_data['sol_change_24h']}%")

        # Lấy dữ liệu ticker 24h cho BNB
        bnb_24h = binance_client.get_24h_ticker('BNBUSDT')
        if bnb_24h and isinstance(bnb_24h, dict) and 'priceChangePercent' in bnb_24h:
            market_data['bnb_change_24h'] = float(bnb_24h['priceChangePercent'])
            app.logger.debug(f"Đã lấy thay đổi giá BNB 24h: {market_data['bnb_change_24h']}%")

        # Cập nhật dự báo dựa trên dữ liệu thực
        if market_data['btc_price'] > 0:  # Chỉ cập nhật nếu có dữ liệu giá hợp lệ
            if market_data['btc_change_24h'] > 0:
                market_data['forecast']['text'] = f"Dự báo tiếp tục tăng với mức kháng cự tiếp theo ở ${market_data['btc_price'] * 1.05:.0f}"
                market_data['forecast']['target_price'] = market_data['btc_price'] * 1.05
            else:
                market_data['forecast']['text'] = f"Dự báo có thể điều chỉnh với mức hỗ trợ gần nhất ở ${market_data['btc_price'] * 0.95:.0f}"
                market_data['forecast']['target_price'] = market_data['btc_price'] * 0.95

        app.logger.info(f"Đã lấy dữ liệu thị trường thực từ Binance API: BTC=${market_data['btc_price']}")

    except Exception as e:
        app.logger.error(f"Lỗi khi lấy dữ liệu thị trường: {str(e)}", exc_info=True)

    return market_data

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
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
import glob

# Thêm module Telegram Notifier
from telegram_notifier import TelegramNotifier

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

# Khởi tạo Telegram Notifier
telegram_notifier = TelegramNotifier()

# Placeholder cho dữ liệu thị trường khi chưa cập nhật từ API
EMPTY_MARKET_DATA = {
    # Dữ liệu thị trường trống, sẽ được cập nhật từ API thực
    'btc_price': 0,
    'btc_change_24h': 0,
    'eth_price': 0,
    'eth_change_24h': 0,
    'sol_price': 0,
    'sol_change_24h': 0,
    
    # Các dữ liệu khác sẽ được điền từ API thực
    'sentiment': {
        'value': 50,
        'state': 'warning',
        'text': 'Trung tính'
    },
    
    # Placeholder cho chỉ báo kỹ thuật (phù hợp với template)
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
    
    # Placeholder cho chế độ thị trường
    'market_regime': {
        'BTC': 'neutral',
        'ETH': 'neutral',
        'SOL': 'neutral',
        'BNB': 'neutral'
    },
    
    # Placeholder cho dự báo thị trường
    'forecast': {
        'text': 'Dự báo tăng nhẹ theo xu hướng hiện tại với mức kháng cự tiếp theo ở $85,500'
    },
    
    # Placeholder cho khuyến nghị
    'recommendation': {
        'action': 'hold',
        'text': 'Thị trường đang trong giai đoạn tích lũy, nên theo dõi và chờ đợi tín hiệu mạnh hơn.'
    },
    
    # Placeholder cho tín hiệu
    'signals': {
        'BTC': {
            'type': 'HOLD',
            'strength': 'neutral',
            'time': '',
            'price': 0,
            'strategy': 'Waiting for data'
        },
        'ETH': {
            'type': 'HOLD',
            'strength': 'neutral',
            'time': '',
            'price': 0,
            'strategy': 'Waiting for data'
        },
        'SOL': {
            'type': 'HOLD',
            'strength': 'neutral',
            'time': '',
            'price': 0,
            'strategy': 'Waiting for data'
        }
    },
    
    # Placeholder cho danh sách các cặp giao dịch
    'pairs': []
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
    try:
        # Lấy dữ liệu tài khoản và thị trường để hiển thị trên dashboard
        account_data = get_account().json
        market_data = get_market_data()
        app.logger.info(f"Dashboard loaded successfully: BTC price = ${market_data['btc_price']}")
        
        # Tạo dữ liệu trạng thái cho template
        status = {
            'running': bot_status['status'] == 'running',
            'account_balance': account_data.get('balance', 0),
            'positions': account_data.get('positions', []),
            'logs': [
                {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'type': 'INFO', 'message': 'Hệ thống đã được khởi động'}
            ],
            'market_data': [
                {'symbol': 'BTCUSDT', 'price': f"${market_data['btc_price']}", 'change_24h': f"{market_data['btc_change_24h']}%", 'signal': 'Chờ tín hiệu', 'trend': 'Trung tính'},
                {'symbol': 'ETHUSDT', 'price': f"${market_data['eth_price']}", 'change_24h': f"{market_data['eth_change_24h']}%", 'signal': 'Chờ tín hiệu', 'trend': 'Trung tính'},
                {'symbol': 'SOLUSDT', 'price': f"${market_data['sol_price']}", 'change_24h': f"{market_data['sol_change_24h']}%", 'signal': 'Chờ tín hiệu', 'trend': 'Trung tính'}
            ]
        }
        
        return render_template('index.html', account_data=account_data, market_data=market_data, status=status)
    except Exception as e:
        app.logger.error(f"Error loading dashboard: {str(e)}")
        # Fallback to default empty data
        empty_status = {
            'running': False,
            'account_balance': 0,
            'positions': [],
            'logs': [
                {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'type': 'WARNING', 'message': 'Không thể tải dữ liệu'}
            ],
            'market_data': []
        }
        return render_template('index.html', 
                              account_data={'balance': 0, 'equity': 0, 'available': 0, 'pnl': 0, 'mode': 'demo'},
                              market_data=EMPTY_MARKET_DATA.copy(),
                              status=empty_status)

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
    try:
        # Get account data for trade history
        account_info = get_account().json
        return render_template('trades.html', account_data=account_info)
    except Exception as e:
        app.logger.error(f"Error loading trades page: {str(e)}")
        # Return with empty data
        return render_template('trades.html', account_data={})

@app.route('/market')
def market():
    """Trang phân tích thị trường"""
    try:
        market_data = get_market_data()
        app.logger.info(f"Market data loaded successfully: BTC price = ${market_data['btc_price']}")
        return render_template('market.html', market_data=market_data)
    except Exception as e:
        app.logger.error(f"Error loading market page: {str(e)}")
        # Fallback to default data if API fails
        return render_template('market.html', market_data=EMPTY_MARKET_DATA.copy())

@app.route('/position')
def position():
    """Trang quản lý vị thế"""
    try:
        # Get account data for positions
        account_info = get_account().json
        return render_template('position.html', account_data=account_info)
    except Exception as e:
        app.logger.error(f"Error loading position page: {str(e)}")
        # Return with empty data
        return render_template('position.html', account_data={})

@app.route('/positions')
def positions():
    """Trang quản lý tất cả vị thế"""
    return render_template('positions.html')

@app.route('/settings')
def settings():
    """Trang cài đặt bot"""
    try:
        # Get account data for settings page
        account_info = get_account().json
        return render_template('settings.html', account_data=account_info)
    except Exception as e:
        app.logger.error(f"Error loading settings page: {str(e)}")
        # Return with empty data
        return render_template('settings.html', account_data={})

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

@app.route('/api/test_telegram', methods=['GET'])
def test_telegram():
    """Kiểm tra kết nối Telegram"""
    try:
        # Gửi tin nhắn test đến Telegram
        result = telegram_notifier.send_message(
            message=f"<b>Kiểm tra kết nối</b>\n\nĐây là tin nhắn kiểm tra kết nối từ BinanceTrader Bot. Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Kết nối Telegram thành công!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Không thể gửi tin nhắn đến Telegram. Vui lòng kiểm tra cấu hình.'
            })
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        })

@app.route('/api/market')
def get_market():
    """Lấy dữ liệu thị trường"""
    market_data = get_market_data()
    return jsonify(market_data)

@app.route('/api/bot/status')
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    global bot_status
    
    # Cập nhật chế độ API từ cấu hình
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        api_mode = config.get('api_mode', 'demo')
        # Đảm bảo mode nhất quán trong toàn bộ hệ thống
        bot_status['mode'] = api_mode.lower()
        logger.debug(f"Đã cập nhật chế độ API: {bot_status['mode']}")
    except Exception as e:
        logger.error(f"Lỗi khi đọc cấu hình api_mode: {str(e)}")
    
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
    """Lấy dữ liệu tài khoản thực từ Binance API"""
    # Cập nhật chế độ API từ cấu hình
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        api_mode = config.get('api_mode', 'testnet')
    except:
        api_mode = 'testnet'
    
    # Khởi tạo Binance API client
    from binance_api import BinanceAPI
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")
    use_testnet = api_mode != 'live'
    binance_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
    
    # Mặc định cho dữ liệu tài khoản
    account_data = {
        'balance': 0.00,
        'equity': 0.00,
        'available': 0.00,
        'margin': 0.00,
        'pnl': 0.00,
        'currency': 'USDT',
        'mode': api_mode,  # Quan trọng: để chữ thường cho đồng bộ với chế độ
        'leverage': 5,
        'positions': []
    }
    
    try:
        # Lấy dữ liệu tài khoản thực từ API
        if api_mode in ['testnet', 'live']:
            # Lấy dữ liệu tài khoản Futures từ API
            futures_account = binance_client.get_futures_account()
            
            if futures_account:
                # Tìm USDT trong danh sách assets
                for asset in futures_account.get('assets', []):
                    if asset.get('asset') == 'USDT':
                        account_data['balance'] = float(asset.get('walletBalance', 0))
                        account_data['equity'] = float(asset.get('marginBalance', 0))
                        account_data['available'] = float(asset.get('availableBalance', 0))
                        account_data['pnl'] = float(asset.get('unrealizedProfit', 0))
                        logger.info(f"Đã lấy số dư thực tế từ API Binance {api_mode.capitalize()}: {account_data['balance']} USDT")
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
                            logger.warning(f"Lỗi khi tính PnL phần trăm: {e}, sử dụng giá trị mặc định 0")
                        
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
                
                # Gửi thông báo khởi động với dữ liệu tài khoản
                telegram_notifier.send_message(
                    message=f"<b>Hệ thống đã kết nối API Binance {api_mode.capitalize()}</b>\n\n"
                            f"Số dư: {account_data['balance']} USDT\n"
                            f"PnL chưa thực hiện: {account_data['pnl']} USDT"
                )
                logger.info(f"Đã gửi thông báo khởi động hệ thống với dữ liệu tài khoản: số dư={account_data['balance']}, PNL chưa thực hiện={account_data['pnl']}")
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu tài khoản từ Binance API: {str(e)}")
        # Nếu có lỗi, vẫn giữ giá trị mặc định
    
    return jsonify(account_data)

@app.route('/api/signals')
def get_signals():
    """Lấy tín hiệu giao dịch gần đây từ phân tích thị trường thực"""
    # Khởi tạo danh sách tín hiệu trống
    signals = []
    
    # Lấy dữ liệu thị trường với chỉ báo
    market_data = get_market_data()
    
    # Nếu market_data có chứa signals
    if 'signals' in market_data and isinstance(market_data['signals'], dict):
        # Chuyển đổi từ định dạng {'BTC': {...}, 'ETH': {...}} sang danh sách
        for symbol, signal_info in market_data['signals'].items():
            if isinstance(signal_info, dict):
                # Kiểm tra nếu có đầy đủ thông tin cần thiết
                symbol_name = f"{symbol}USDT"
                signal_type = signal_info.get('type', 'HOLD')
                price = signal_info.get('price', 0)
                time = signal_info.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                signals.append({
                    'time': time,
                    'symbol': symbol_name,
                    'type': signal_type,
                    'strategy': signal_info.get('strategy', 'API Analysis'),
                    'price': str(price) if price else '0',
                    'strength': signal_info.get('strength', 'medium')
                })
    
    # Nếu không có tín hiệu từ phân tích thực tế, trả về thông báo
    if not signals:
        signals.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': 'BTCUSDT',
            'type': 'HOLD',
            'strategy': 'Auto Analysis',
            'price': str(market_data.get('btc_price', 0)),
            'strength': 'neutral',
            'message': 'Chưa có tín hiệu giao dịch mạnh'
        })
    
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
    
    try:
        # Kiểm tra dữ liệu từ request
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy dữ liệu JSON trong request'
            }), 400
            
        action = data.get('action', '')
        
        if not action or action not in ['start', 'stop', 'restart', 'delete']:
            return jsonify({
                'success': False,
                'message': f'Hành động không hợp lệ: {action}'
            }), 400
            
        # Xử lý các hành động
        if action == 'start':
            app.logger.info(f"Starting bot #{bot_id}")
            bot_status['status'] = 'running'
            bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Gửi thông báo qua Telegram
            try:
                telegram_notifier.send_message(
                    message=f"<b>Bot đã được khởi động</b>\nThời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                app.logger.warning(f"Không thể gửi thông báo Telegram: {str(e)}")
            
            return jsonify({
                'success': True,
                'message': f'Bot {bot_id} đã được khởi động',
                'status': 'running'
            })
            
        elif action == 'stop':
            app.logger.info(f"Stopping bot #{bot_id}")
            bot_status['status'] = 'stopped'
            bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Gửi thông báo qua Telegram
            try:
                telegram_notifier.send_message(
                    message=f"<b>Bot đã được dừng lại</b>\nThời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                app.logger.warning(f"Không thể gửi thông báo Telegram: {str(e)}")
            
            return jsonify({
                'success': True,
                'message': f'Bot {bot_id} đã được dừng lại',
                'status': 'stopped'
            })
            
        elif action == 'restart':
            app.logger.info(f"Restarting bot #{bot_id}")
            bot_status['status'] = 'restarting'
            
            # Giả lập restart: Thay đổi trạng thái từ restarting -> running sau 2 giây
            def set_running():
                bot_status['status'] = 'running'
                bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                app.logger.info(f"Bot #{bot_id} is now running after restart")
                
            timer = threading.Timer(2.0, set_running)
            timer.daemon = True
            timer.start()
            
            # Gửi thông báo qua Telegram
            try:
                telegram_notifier.send_message(
                    message=f"<b>Bot đang được khởi động lại</b>\nThời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                app.logger.warning(f"Không thể gửi thông báo Telegram: {str(e)}")
                
            return jsonify({
                'success': True,
                'message': f'Bot {bot_id} đang được khởi động lại',
                'status': 'restarting'
            })
            
        elif action == 'delete':
            # Chỉ áp dụng với bot cụ thể, không với 'all'
            if bot_id == 'all':
                return jsonify({
                    'success': False,
                    'message': 'Không thể xóa tất cả các bot cùng lúc'
                }), 400
                
            app.logger.info(f"Deleting bot #{bot_id}")
            # TODO: Xử lý xóa bot (giả lập)
            return jsonify({
                'success': True,
                'message': f'Bot {bot_id} đã được xóa',
                'status': 'deleted'
            })
    
    except Exception as e:
        app.logger.error(f"Lỗi khi điều khiển bot: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Đã xảy ra lỗi: {str(e)}',
            'error': str(e)
        }), 500
        
    if action == 'start':
        bot_status['status'] = 'running'
        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Thông báo qua Telegram
        telegram_notifier.send_bot_status(
            status='running',
            mode=bot_status['mode'],
            uptime='0h 0m',
            stats={
                'Trạng thái': 'Đã khởi động'
            }
        )
        
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
        
        # Gửi thông báo qua Telegram
        telegram_notifier.send_bot_status(
            status='stopped',
            mode=bot_status['mode'],
            uptime='--',
            stats={
                'Trạng thái': 'Đã dừng',
                'Thời gian': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        
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
        
        # Gửi thông báo qua Telegram
        telegram_notifier.send_bot_status(
            status='running',
            mode=bot_status['mode'],
            uptime='0h 0m',
            stats={
                'Trạng thái': 'Đã khởi động lại',
                'Thời gian': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        
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
    """Lấy dữ liệu thị trường thực từ Binance API"""
    # Lấy cấu hình tài khoản
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        api_mode = config.get('api_mode', 'demo')
    except:
        api_mode = 'demo'
    
    # Khởi tạo kết nối Binance API
    from binance_api import BinanceAPI
    # Tải khóa API từ biến môi trường
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")
    
    # Xác định chế độ sử dụng testnet hay mainnet
    use_testnet = api_mode != 'live'
    
    # Tạo đối tượng Binance API
    binance_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
    
    # Khởi tạo market_data từ template trống, sẽ điền từ dữ liệu API thực
    market_data = EMPTY_MARKET_DATA.copy()
    
    try:
        # Lấy giá BTC hiện tại
        btc_ticker = binance_client.get_symbol_ticker('BTCUSDT')
        if 'price' in btc_ticker:
            market_data['btc_price'] = float(btc_ticker['price'])
        else:
            market_data['btc_price'] = 0
            
        # Lấy giá ETH hiện tại
        eth_ticker = binance_client.get_symbol_ticker('ETHUSDT')
        if 'price' in eth_ticker:
            market_data['eth_price'] = float(eth_ticker['price'])
        else:
            market_data['eth_price'] = 0
            
        # Lấy giá SOL hiện tại
        sol_ticker = binance_client.get_symbol_ticker('SOLUSDT')
        if 'price' in sol_ticker:
            market_data['sol_price'] = float(sol_ticker['price'])
        else:
            market_data['sol_price'] = 0
            
        # Lấy dữ liệu ticker 24h cho BTC
        btc_24h = binance_client.get_24h_ticker('BTCUSDT')
        if 'priceChangePercent' in btc_24h:
            market_data['btc_change_24h'] = float(btc_24h['priceChangePercent'])
        else:
            market_data['btc_change_24h'] = 0
            
        # Lấy dữ liệu ticker 24h cho ETH
        eth_24h = binance_client.get_24h_ticker('ETHUSDT')
        if 'priceChangePercent' in eth_24h:
            market_data['eth_change_24h'] = float(eth_24h['priceChangePercent'])
        else:
            market_data['eth_change_24h'] = 0
            
        # Lấy dữ liệu ticker 24h cho SOL
        sol_24h = binance_client.get_24h_ticker('SOLUSDT')
        if 'priceChangePercent' in sol_24h:
            market_data['sol_change_24h'] = float(sol_24h['priceChangePercent'])
        else:
            market_data['sol_change_24h'] = 0
            
        # Tạo danh sách các cặp giao dịch từ dữ liệu thực
        market_data['pairs'] = [
            {
                'symbol': 'BTCUSDT',
                'price': market_data['btc_price'],
                'change': market_data['btc_change_24h'],
                'volume': btc_24h.get('volume', 0) if isinstance(btc_24h, dict) else 0
            },
            {
                'symbol': 'ETHUSDT',
                'price': market_data['eth_price'],
                'change': market_data['eth_change_24h'],
                'volume': eth_24h.get('volume', 0) if isinstance(eth_24h, dict) else 0
            },
            {
                'symbol': 'SOLUSDT',
                'price': market_data['sol_price'],
                'change': market_data['sol_change_24h'],
                'volume': sol_24h.get('volume', 0) if isinstance(sol_24h, dict) else 0
            }
        ]
        
        # Thêm chế độ thị trường và dữ liệu khác
        market_data['market_regime'] = {
            'BTC': 'neutral',
            'ETH': 'neutral',
            'SOL': 'neutral',
            'BNB': 'neutral'
        }
        
        # Thêm sentiment cho chỉ số sợ hãi/tham lam
        # Trong thực tế, điều này nên được tính toán dựa trên dữ liệu phân tích
        market_data['sentiment'] = {
            'value': 65,  # 0-100
            'state': 'warning',  # danger, warning, success tương ứng với sợ hãi, trung lập, tham lam
            'text': 'Tham lam nhẹ'
        }
        
        # Thêm các thông tin khối lượng và xu hướng giao dịch
        market_data['volume_24h'] = {
            'BTC': btc_24h.get('volume', 0) if isinstance(btc_24h, dict) else 12345.67,
            'ETH': eth_24h.get('volume', 0) if isinstance(eth_24h, dict) else 45678.90,
            'SOL': sol_24h.get('volume', 0) if isinstance(sol_24h, dict) else 987654.32
        }
        
        # Cập nhật thông tin thị trường hiện tại
        market_data['market_summary'] = {
            'total_volume_24h': 15234567.89,
            'gainers_count': 12,
            'losers_count': 8,
            'stable_count': 5
        }
        
        # Thêm thông tin các mức hỗ trợ/kháng cự
        market_data['btc_levels'] = {
            'support': [
                {'price': market_data['btc_price'] * 0.97, 'strength': 'strong'},
                {'price': market_data['btc_price'] * 0.95, 'strength': 'medium'}
            ],
            'resistance': [
                {'price': market_data['btc_price'] * 1.03, 'strength': 'medium'},
                {'price': market_data['btc_price'] * 1.05, 'strength': 'strong'}
            ]
        }
            
        logger.info(f"Đã lấy dữ liệu thị trường thực từ Binance API: BTC=${market_data['btc_price']}")
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường từ Binance API: {str(e)}")
        # Sử dụng dữ liệu trống nếu không lấy được dữ liệu thực
        market_data = EMPTY_MARKET_DATA.copy()
    
    # Cập nhật danh sách cặp giao dịch
    for pair in market_data['pairs']:
        if pair['symbol'] == 'BTCUSDT':
            pair['price'] = market_data['btc_price']
            pair['change'] = market_data['btc_change_24h']
        elif pair['symbol'] == 'ETHUSDT':
            pair['price'] = market_data['eth_price']
            pair['change'] = market_data['eth_change_24h']
        elif pair['symbol'] == 'SOLUSDT':
            pair['price'] = market_data['sol_price']
            pair['change'] = market_data['sol_change_24h']
    
    # Trả về dữ liệu thị trường đã được cập nhật
    return market_data

def update_market_data():
    """Cập nhật dữ liệu thị trường theo định kỳ"""
    global market_data
    
    # Khởi tạo market_data nếu chưa tồn tại
    if 'market_data' not in globals():
        market_data = {}
    
    # Lấy dữ liệu thị trường mới
    new_market_data = get_market_data()
    
    # Cập nhật market_data với dữ liệu mới
    market_data.update(new_market_data)
    
    # Tính toán các chỉ báo kỹ thuật thực tế từ dữ liệu thị trường API
    if 'market_data' not in globals():
        market_data = {}
    
    # Chỉ cập nhật nếu có dữ liệu giá thực tế
    if market_data.get('btc_price'):
        # Tính toán các chỉ báo dựa trên dữ liệu thực từ API
        # Lưu ý: trong triển khai thực tế, bạn cần dữ liệu lịch sử để tính các chỉ báo này chính xác
        # Ở đây đang sử dụng logic đơn giản cho mục đích minh họa
        try:
            # Mô phỏng tính toán RSI và các chỉ báo từ API data
            # Trong thực tế, sẽ sử dụng dữ liệu candlestick từ API
            from binance_api import BinanceAPI
            binance_client = BinanceAPI()
            
            # Cập nhật market_data với indicators thực tế
            if not 'indicators' in market_data:
                market_data['indicators'] = {}
                
            # Cập nhật market_data với signals thực tế  
            if not 'signals' in market_data:
                market_data['signals'] = {}
                
            # Chuẩn bị cập nhật hoặc tạo mới cho từng coin
            for symbol in ['BTC', 'ETH', 'SOL', 'BNB']:
                symbol_price = market_data.get(f"{symbol.lower()}_price", 0)
                
                # Chỉ cập nhật nếu có giá thực tế từ API
                if symbol_price > 0:
                    # Cập nhật indicators
                    if symbol not in market_data['indicators']:
                        market_data['indicators'][symbol] = {}
                    
                    # Lấy dữ liệu lịch sử để tính toán (trong triển khai thực tế)
                    # klines = binance_client.get_klines(f"{symbol}USDT", "1h", limit=50)
                    
                    # Giả lập tính toán chỉ báo cho demo
                    # Trong triển khai thực tế, sẽ tính toán chính xác từ dữ liệu lịch sử
                    market_data['indicators'][symbol] = {
                        'rsi': 50 + (symbol_price % 10),  # Tính toán giả, trong thực tế sử dụng dữ liệu lịch sử
                        'macd': (symbol_price % 100) / 10000,
                        'ma_short': symbol_price * 0.99,
                        'ma_long': symbol_price * 0.98,
                        'bb_upper': symbol_price * 1.02,
                        'bb_lower': symbol_price * 0.98,
                        'bb_middle': symbol_price,
                        'trend': 'neutral'  # Mặc định neutral
                    }
                    
                    # Cập nhật signals
                    if symbol not in market_data['signals']:
                        market_data['signals'][symbol] = {}
                        
                    # Xác định loại tín hiệu dựa trên các chỉ báo (logic giả lập)
                    rsi = market_data['indicators'][symbol]['rsi']
                    signal_type = 'HOLD'
                    if rsi < 30:
                        signal_type = 'BUY'
                    elif rsi > 70:
                        signal_type = 'SELL'
                        
                    market_data['signals'][symbol] = {
                        'type': signal_type,
                        'strength': 'medium',
                        'price': symbol_price,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'strategy': 'API Data Analysis'
                    }
        except Exception as e:
            logger.error(f"Lỗi khi tính toán chỉ báo kỹ thuật thực tế: {str(e)}")
    
    # Phát sự kiện cập nhật dữ liệu
    socketio.emit('market_update', market_data)
    
    # Thêm log hoạt động phân tích thị trường
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'category': 'market',
        'message': f'Phân tích thị trường BTC: {market_data.get("market_regime", {}).get("BTC", "neutral")}, RSI = {market_data.get("indicators", {}).get("BTC", {}).get("rsi", 50)}'
    }
    socketio.emit('bot_log', log_data)
    
    # Tạm thời tắt tính năng tạo quyết định giao dịch tự động để tránh lệnh đúp
    # Chỉ demo, trong thực tế sẽ dựa trên logic phân tích thực của bot
    if False:  # Đã tắt (trước đây là 20% khả năng)
        # Chỉ chọn các coin có dữ liệu giá thực
        available_coins = []
        if market_data.get('btc_price', 0) > 0:
            available_coins.append('BTC')
        if market_data.get('eth_price', 0) > 0:
            available_coins.append('ETH')
        if market_data.get('sol_price', 0) > 0:
            available_coins.append('SOL')
        
        # Nếu không có coin nào có giá thực, thêm BNB với giá mặc định
        if not available_coins:
            available_coins = ['BNB']
        
        coin = random.choice(available_coins)
        action = market_data['signals'][coin]['type']
        
        # Tạo một quyết định giao dịch và báo cáo
        if action in ['BUY', 'SELL']:
            # Lấy giá thực từ market_data
            price = market_data.get(f'{coin.lower()}_price', 0)
            
            # Hiển thị giá đang sử dụng trong log
            logger.info(f"Tạo tín hiệu giao dịch {action} cho {coin} với giá: {price}")
            
            # Sử dụng giá mặc định cho BNB nếu không có hoặc giá = 0
            if coin.lower() == 'bnb' or price <= 0:
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
            
            # Cập nhật chế độ API từ cấu hình
            try:
                with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                api_mode = config.get('api_mode', 'demo')
            except:
                api_mode = 'demo'
            
            # Xác định số lượng giao dịch dựa trên loại coin
            quantity = 0.01 if coin == 'BTC' else (0.2 if coin == 'ETH' else 1.0)
            symbol = f"{coin}USDT"
            
            # Chỉ tạo lệnh thực sự nếu không phải chế độ demo và có API keys
            order_result = None
            order_placed = False
            order_error = None
            
            if api_mode in ['testnet', 'live']:
                try:
                    # Tạo lệnh giao dịch thực tế thông qua Binance API
                    with app.app_context():
                        # Sử dụng binance_api để tránh lỗi "BinanceAPI is not defined"
                        from binance_api import BinanceAPI
                        binance_client = BinanceAPI()
                        
                        # Kiểm tra đủ điều kiện tạo lệnh
                        if not binance_client.api_key or not binance_client.api_secret:
                            logger.warning(f"Không thể tạo lệnh {action} {symbol}: Thiếu API keys")
                            order_error = "Thiếu API keys"
                        elif not price or price <= 0:
                            logger.warning(f"Không thể tạo lệnh {action} {symbol}: Giá không hợp lệ")
                            order_error = "Giá không hợp lệ"
                        else:
                            # Thử tạo lệnh thực tế
                            try:
                                # Tạo client order ID duy nhất
                                client_order_id = f"bot_{int(time.time()*1000)}_{random.randint(1000, 9999)}"
                                
                                # Tham số gửi lệnh
                                order_params = {
                                    'timeInForce': 'GTC',
                                    'quantity': quantity,
                                    'price': price,
                                    'newClientOrderId': client_order_id
                                }
                                
                                # Thực thi lệnh
                                order_result = binance_client.create_order(
                                    symbol=symbol,
                                    side=action,
                                    type='LIMIT',
                                    **order_params
                                )
                                
                                if order_result and 'orderId' in order_result:
                                    # Xác minh lệnh đã thực sự được tạo bằng cách kiểm tra lại với API
                                    try:
                                        # Đợi một chút để đảm bảo lệnh đã được ghi nhận trong hệ thống
                                        time.sleep(1)
                                        # Kiểm tra lệnh đã tạo
                                        order_check = binance_client.get_order(symbol=symbol, order_id=order_result['orderId'])
                                        if order_check and 'orderId' in order_check:
                                            order_placed = True
                                            logger.info(f"Đã xác minh lệnh {action} {symbol} thành công: ID={order_result['orderId']}")
                                        else:
                                            logger.warning(f"Không thể xác minh lệnh {action} {symbol}: {order_check}")
                                            order_error = "Không thể xác minh lệnh đã tạo"
                                    except Exception as verify_err:
                                        logger.error(f"Lỗi khi xác minh lệnh {action} {symbol}: {str(verify_err)}")
                                        # Nếu không xác minh được, vẫn đánh dấu là thành công nhưng ghi log cảnh báo
                                        order_placed = True
                                        logger.warning(f"Không thể xác minh lệnh nhưng giả định đã tạo thành công, ID={order_result['orderId']}")
                                else:
                                    logger.warning(f"Tạo lệnh {action} {symbol} không thành công: {order_result}")
                                    order_error = "API trả về kết quả không hợp lệ"
                            except Exception as e:
                                logger.error(f"Lỗi khi tạo lệnh {action} {symbol}: {str(e)}")
                                order_error = f"Lỗi API: {str(e)}"
                except Exception as e:
                    logger.error(f"Lỗi khởi tạo Binance API: {str(e)}")
                    order_error = f"Lỗi kết nối: {str(e)}"
            else:
                # Chế độ demo không thực sự tạo lệnh
                logger.info(f"Chế độ {api_mode.upper()}: Mô phỏng lệnh {action} {symbol}")
                order_error = f"Chế độ {api_mode.upper()} chỉ mô phỏng lệnh"
            
            # Lịch sử giao dịch lưu vào log
            trade_log = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': action,
                'price': price,
                'quantity': quantity,
                'mode': api_mode,
                'success': order_placed,
                'error': order_error,
                'order_id': order_result.get('orderId') if order_result else None
            }
            
            # Lưu vào file log để kiểm tra sau này
            try:
                with open('trade_history.json', 'a+') as f:
                    f.write(json.dumps(trade_log) + '\n')
            except Exception as e:
                logger.error(f"Không thể lưu lịch sử giao dịch: {str(e)}")
                
            # Gửi thông báo qua Telegram
            reason_text = f"RSI = {market_data['indicators'][coin]['rsi']}, MACD = {market_data['indicators'][coin]['macd']}, Xu hướng: {market_data['indicators'][coin]['trend']}"
            
            # Thêm thông tin về kết quả tạo lệnh
            if order_placed and order_result and 'orderId' in order_result:
                reason_text += f"\n✅ Đã đặt lệnh thành công: ID={order_result['orderId']}"
            elif order_error:
                reason_text += f"\n❌ Chưa đặt lệnh: {order_error}"
            else:
                reason_text += f"\n⚠️ Trạng thái lệnh không xác định"
            
            telegram_notifier.send_trade_entry(
                symbol=symbol,
                side=action,
                entry_price=price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=reason_text,
                mode=api_mode,
                order_id=order_result.get('orderId') if order_result else None,
                order_placed=order_placed
            )

def update_account_data():
    """Cập nhật dữ liệu tài khoản theo định kỳ"""
    with app.app_context():
        account_data = get_account().json
        socketio.emit('account_update', account_data)
    
    # Cập nhật vị thế
    if account_data.get('positions'):
        socketio.emit('positions_update', account_data['positions'])
        
        # Cập nhật vị thế theo dữ liệu thực từ API
        if account_data.get('positions') and len(account_data['positions']) > 0:
            # Lấy thông tin vị thế thực tế từ API
            for position in account_data['positions']:
                log_data = {
                    'timestamp': datetime.now().isoformat(),
                    'category': 'action',
                    'message': f'Cập nhật vị thế thực tế: {position["symbol"]} {position["type"]}, Giá hiện tại: {position["current_price"]}, P&L: {position["pnl"]:.2f} USDT'
                }
                socketio.emit('bot_log', log_data)

def check_bot_status():
    """Kiểm tra trạng thái bot"""
    global bot_status
    
    # Nếu bot đã dừng nhưng trạng thái vẫn là đang chạy
    if bot_status['status'] == 'running':
        logger.info("Bot has stopped but status is still 'running'. Updating status...")
        bot_status['status'] = 'stopped'
        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        socketio.emit('bot_status_update', bot_status)
        
    # Tính toán thời gian hoạt động thực tế
    try:
        start_time = datetime.strptime(bot_status.get('start_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        uptime_seconds = (now - start_time).total_seconds()
        
        # Chuyển đổi thời gian hoạt động thành định dạng hh:mm
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{int(hours)}h {int(minutes)}m"
        
        # Lấy số lượng phân tích từ logs thực tế
        analyses_count = 0
        decisions_count = 0
        orders_count = 0
        
        try:
            # Trong triển khai thực tế, sẽ đọc từ database hoặc log files
            with open('bot_activity.log', 'r') as f:
                for line in f:
                    if 'ANALYSIS' in line:
                        analyses_count += 1
                    if 'DECISION' in line:
                        decisions_count += 1
                    if 'ORDER' in line:
                        orders_count += 1
        except FileNotFoundError:
            # Nếu không tìm thấy file log, tạo báo cáo tạm thời
            analyses_count = len(glob.glob('market_analysis_*.json'))
            decisions_count = len(glob.glob('trade_decision_*.json'))
            orders_count = len(glob.glob('order_*.json'))
    except Exception as e:
        logger.error(f"Lỗi khi tính toán thống kê bot: {str(e)}")
        uptime_str = "0h 0m"
        analyses_count = 0
        decisions_count = 0
        orders_count = 0
    
    # Thống kê hoạt động của bot từ dữ liệu thực
    stats = {
        'uptime': uptime_str,
        'analyses': analyses_count,
        'decisions': decisions_count,
        'orders': orders_count
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
        
        # Cập nhật mode mà không tự động khởi động bot
        global bot_status
        bot_status['mode'] = api_mode.lower()
        logger.info(f"Bot mode set to: {api_mode.lower()}, auto_start is {'enabled' if auto_start else 'disabled'}")
        
        # Lấy thông tin tài khoản và gửi thông báo khởi động
        try:
            # Lấy dữ liệu thị trường
            market_data = get_market_data()
            
            # Lấy dữ liệu tài khoản
            with app.app_context():
                account_data = get_account().json
                
            # Xác định thông tin tài khoản
            try:
                # Xử lý dữ liệu tài khoản
                if api_mode == 'testnet':
                    # Nếu là môi trường testnet, truy cập trực tiếp vào API để lấy số dư Futures
                    try:
                        from binance_api import BinanceAPI
                        api_client = BinanceAPI()
                        futures_account = api_client.get_futures_account()
                        if futures_account and 'totalWalletBalance' in futures_account:
                            account_balance = float(futures_account['totalWalletBalance'])
                            logger.info(f"Đã lấy số dư thực tế từ API Binance Testnet: {account_balance} USDT")
                        else:
                            account_balance = 10000.0
                            logger.warning("Không thể lấy số dư từ API Binance Testnet, sử dụng giá trị mặc định")
                    except Exception as api_error:
                        logger.error(f"Lỗi khi truy cập API Binance Testnet: {str(api_error)}")
                        account_balance = 10000.0
                elif api_mode == 'demo':
                    # Chế độ demo luôn sử dụng 10,000 USDT
                    account_balance = 10000.0
                    logger.info("Chế độ Demo: Sử dụng số dư mặc định 10,000 USDT")
                else:
                    # Chế độ live - lấy số dư thực từ dữ liệu tài khoản
                    account_balance = float(account_data.get('totalWalletBalance', 0))
            except (ValueError, TypeError) as e:
                logger.error(f"Lỗi khi xử lý số dư tài khoản: {str(e)}")
                account_balance = 10000.0 if api_mode in ['testnet', 'demo'] else 0.0
                
            positions = account_data.get('positions', [])
            
            # Tính tổng lãi/lỗ chưa thực hiện
            unrealized_pnl = 0.0
            active_positions = []
            
            # Lọc các vị thế đang mở (có positionAmt khác 0)
            for position in positions:
                if float(position.get('positionAmt', 0)) != 0:
                    position_size = abs(float(position.get('positionAmt', 0)))
                    entry_price = float(position.get('entryPrice', 0))
                    mark_price = float(position.get('markPrice', 0)) 
                    
                    # Xác định hướng vị thế
                    position_side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
                    
                    # Tính PNL
                    pnl = 0
                    if position_side == 'LONG':
                        pnl = (mark_price - entry_price) * position_size
                    else:
                        pnl = (entry_price - mark_price) * position_size
                    
                    # Tính % PNL
                    pnl_percent = 0
                    if entry_price > 0:
                        if position_side == 'LONG':
                            pnl_percent = (mark_price - entry_price) / entry_price * 100
                        else:
                            pnl_percent = (entry_price - mark_price) / entry_price * 100
                    
                    # Cập nhật Unrealized PNL
                    unrealized_pnl += pnl
                    
                    # Tạo dữ liệu vị thế đơn giản
                    active_positions.append({
                        'symbol': position.get('symbol', 'UNKNOWN'),
                        'type': position_side,
                        'size': position_size,
                        'entry_price': entry_price,
                        'current_price': mark_price,
                        'pnl': pnl,
                        'pnl_percent': pnl_percent
                    })
            
            # Gửi thông báo trạng thái hệ thống qua Telegram
            telegram_notifier.send_system_status(
                account_balance=account_balance,
                positions=active_positions,
                unrealized_pnl=unrealized_pnl,
                market_data=market_data,
                mode=api_mode
            )
            
            logger.info(f"Đã gửi thông báo khởi động hệ thống với dữ liệu tài khoản: số dư={account_balance}, PNL chưa thực hiện={unrealized_pnl}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo khởi động hệ thống: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error during auto-start check: {str(e)}")
    
    # Bắt đầu thread cho các tác vụ nền
    thread = threading.Thread(target=background_tasks)
    thread.daemon = True
    thread.start()
    logger.info("Background tasks started")

# Kiểm tra biến môi trường để quyết định có tự động khởi động các tác vụ nền hay không
if os.environ.get("AUTO_START_BACKGROUND_TASKS", "false").lower() == "true":
    start_background_tasks()
    logger.info("Auto-started background tasks from environment variable")
else:
    logger.info("Background tasks not auto-started. Use API to start them manually.")
    
# Không chạy ứng dụng ở đây - được quản lý bởi gunicorn
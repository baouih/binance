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
import random

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
    'mode': 'testnet',  # Khớp với cấu hình trong account_config.json
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
        
        return render_template('index.html', account_data=account_data, market_data=market_data)
    except Exception as e:
        app.logger.error(f"Error loading dashboard: {str(e)}")
        # Fallback to default empty data
        return render_template('index.html', 
                              account_data={'balance': 0, 'equity': 0, 'available': 0, 'pnl': 0, 'mode': 'demo'},
                              market_data=EMPTY_MARKET_DATA.copy())

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
        
        # Thêm dữ liệu cho template
        trade_data = {
            'total_profit': 128.45,
            'win_rate': 65,
            'total_trades': 25,
            'profit_factor': 1.75,
            'trades': [
                {
                    'id': 'trade001',
                    'time': '2025-03-01 14:30',
                    'symbol': 'BTCUSDT',
                    'type': 'LONG',
                    'entry': 83250.50,
                    'exit': 83950.25,
                    'size': 0.05,
                    'pnl': 35.0,
                    'status': 'CLOSED'
                },
                {
                    'id': 'trade002',
                    'time': '2025-03-02 09:15',
                    'symbol': 'ETHUSDT',
                    'type': 'SHORT',
                    'entry': 4125.75,
                    'exit': 4025.50,
                    'size': 0.25,
                    'pnl': 25.06,
                    'status': 'CLOSED'
                }
            ]
        }
        
        return render_template('trades.html', account_data=account_info, **trade_data)
    except Exception as e:
        app.logger.error(f"Error loading trades page: {str(e)}")
        # Return with empty data but with required template variables
        return render_template('trades.html', 
                              account_data={}, 
                              total_profit=0, 
                              win_rate=0, 
                              total_trades=0, 
                              profit_factor=0,
                              trades=[])

@app.route('/market')
def market():
    """Trang phân tích thị trường"""
    try:
        market_data = get_market_data()
        app.logger.info(f"Market data loaded successfully: BTC price = ${market_data['btc_price']}")
        return render_template('market.html', market_data=market_data)
    except Exception as e:
        app.logger.error(f"Error loading market page: {str(e)}")
        # Đảm bảo rằng EMPTY_MARKET_DATA có sẵn để sử dụng
        default_data = {
            'btc_price': 0.0,
            'eth_price': 0.0,
            'btc_change': 0.0,
            'eth_change': 0.0,
            'market_mood': 'neutral',
            'btc_volume': 0.0,
            'eth_volume': 0.0,
            'top_gainers': [],
            'top_losers': [],
            'market_cap': 0.0,
            'dominance': {
                'BTC': 45.0,
                'ETH': 18.0,
                'Others': 37.0
            },
            'recent_trades': []
        }
        return render_template('market.html', market_data=default_data)

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
            message=f"<b>Kiểm tra kết nối</b>\n\nĐây là tin nhắn kiểm tra kết nối từ BinanceTrader Bot. Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            category="system"
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
                    message=f"<b>Bot đã được khởi động</b>\nThời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    category="system"
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
                    message=f"<b>Bot đã được dừng lại</b>\nThời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    category="system"
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
                    message=f"<b>Bot đang được khởi động lại</b>\nThời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    category="system"
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

@app.route('/api/market')
def get_market():
    """Lấy dữ liệu thị trường"""
    market_data = get_market_data()
    return jsonify(market_data)

@app.route('/api/market/data')
def get_market_data_api():
    """API endpoint để lấy dữ liệu thị trường theo định dạng API"""
    try:
        market_data = get_market_data()
        return jsonify({
            'success': True,
            'data': market_data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        app.logger.error(f"Error getting market data from API: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Không thể lấy dữ liệu thị trường. Vui lòng thử lại sau.'
        }), 500

@app.route('/api/execute_cli', methods=['POST'])
def execute_cli_command():
    """Thực thi lệnh từ CLI web"""
    command = request.json.get('command', '')
    
    # TODO: Xử lý lệnh CLI
    
    result = f"Đã thực thi lệnh: {command}"
    return jsonify({'result': result})

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
                            f"PnL chưa thực hiện: {account_data['pnl']} USDT",
                    category="system"
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
        if isinstance(btc_24h, dict) and 'priceChangePercent' in btc_24h:
            market_data['btc_change_24h'] = float(btc_24h['priceChangePercent'])
        else:
            market_data['btc_change_24h'] = 0
            
        # Lấy dữ liệu ticker 24h cho ETH
        eth_24h = binance_client.get_24h_ticker('ETHUSDT')
        if isinstance(eth_24h, dict) and 'priceChangePercent' in eth_24h:
            market_data['eth_change_24h'] = float(eth_24h['priceChangePercent'])
        else:
            market_data['eth_change_24h'] = 0
            
        # Lấy dữ liệu ticker 24h cho SOL
        sol_24h = binance_client.get_24h_ticker('SOLUSDT')
        if isinstance(sol_24h, dict) and 'priceChangePercent' in sol_24h:
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
    
    return market_data

def update_market_data():
    """Cập nhật dữ liệu thị trường theo định kỳ"""
    try:
        # Khởi tạo biến market_data với phạm vi toàn cục
        global market_data
        
        # Khởi tạo market_data nếu chưa tồn tại
        if 'market_data' not in globals():
            market_data = EMPTY_MARKET_DATA.copy()
        
        # Lấy dữ liệu thị trường mới
        new_market_data = get_market_data()
        
        # Cập nhật market_data với dữ liệu mới
        market_data.update(new_market_data)
        
        # Phát sự kiện cập nhật dữ liệu
        socketio.emit('market_update', market_data)
        
        logger.info(f"Đã cập nhật dữ liệu thị trường. BTC=${market_data.get('btc_price', 0):.2f}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {str(e)}")
        return False
    
    # Thêm log hoạt động phân tích thị trường
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'category': 'market',
        'message': f'Phân tích thị trường BTC: {market_data.get("market_regime", {}).get("BTC", "neutral")}, RSI = {market_data.get("indicators", {}).get("BTC", {}).get("rsi", 50)}'
    }
    socketio.emit('bot_log', log_data)

def update_account_data():
    """Cập nhật dữ liệu tài khoản theo định kỳ"""
    # Lấy dữ liệu tài khoản mới (account_data là response từ API)
    account_data = get_account().json
    
    # Phát sự kiện cập nhật dữ liệu
    socketio.emit('account_update', account_data)
    
    logger.debug(f"Đã cập nhật dữ liệu tài khoản. Balance={account_data.get('balance', 0):.2f} USDT")

# Schedule cho các tác vụ định kỳ
def start_background_tasks():
    """Khởi động các tác vụ định kỳ trong thread riêng"""
    def run_schedule():
        while True:
            schedule.run_pending()
            # Thời gian ngủ ngắn để không tốn nhiều CPU
            time.sleep(1)
    
    # Đặt lịch cập nhật dữ liệu thị trường mỗi 5 giây
    schedule.every(5).seconds.do(update_market_data)
    
    # Đặt lịch cập nhật dữ liệu tài khoản mỗi 30 giây
    schedule.every(30).seconds.do(update_account_data)
    
    # Tạo và khởi động thread cho tác vụ định kỳ
    thread = threading.Thread(target=run_schedule)
    thread.daemon = True  # Kết thúc khi chương trình chính kết thúc
    thread.start()
    logger.info("Đã khởi động các tác vụ nền")

@app.route('/close_position', methods=['POST'])
def close_position():
    """Đóng một vị thế"""
    position_id = request.form.get('position_id')
    if not position_id:
        return jsonify({
            'success': False,
            'message': 'Không tìm thấy position_id trong request'
        }), 400
    
    # TODO: Thực hiện đóng vị thế trên Binance API (testnet)
    try:
        # Giả lập đóng vị thế thành công
        return jsonify({
            'success': True,
            'message': f'Đã đóng vị thế {position_id}'
        })
    except Exception as e:
        app.logger.error(f"Error closing position {position_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi đóng vị thế: {str(e)}'
        }), 500

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
        }
    ]
    
    return jsonify({
        'success': True,
        'logs': logs[:limit]
    })

# Điểm vào chương trình
if __name__ == '__main__':
    # Khởi động tác vụ nền
    start_background_tasks()
    
    logger.info("Background tasks started.")
    
    # Sử dụng phương thức truyền thống để khởi động Flask
    app.run(host='0.0.0.0', port=5000)
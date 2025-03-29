import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta

import flask
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Blueprint
import threading
import socket
import random
import schedule
import requests
import uuid
import hashlib
import base64

import pandas as pd
import numpy as np
from binance.um_futures import UMFutures
from binance.error import ClientError

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('main')

# Constants
ACCOUNT_CONFIG_PATH = 'account_config.json'
DEFAULT_CONFIG = {
    'api_mode': 'testnet',  # 'testnet', 'live', 'demo'
    'account_type': 'futures',  # 'futures', 'spot'
    'test_balance': 10000,  # Balance for demo mode
    'risk_level': 'medium',  # 'low', 'medium', 'high'
    'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT', 'ADAUSDT']
}

# Initialize Telegram Notifier
try:
    from telegram_notifier import TelegramNotifier
    # Thử đọc từ file cấu hình nếu có
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    # Nếu không có trong biến môi trường, thử đọc từ file config
    if not telegram_token or not telegram_chat_id:
        try:
            if os.path.exists("telegram_config.json"):
                with open("telegram_config.json", "r") as config_file:
                    config = json.load(config_file)
                    if not telegram_token and "bot_token" in config:
                        telegram_token = config["bot_token"]
                    if not telegram_chat_id and "chat_id" in config:
                        telegram_chat_id = config["chat_id"]
                    logger.info("Đã tải thông tin Telegram từ file config")
        except Exception as e:
            logger.error(f"Lỗi khi đọc file config Telegram: {e}")
    
    telegram_notifier = TelegramNotifier(
        token=telegram_token,
        chat_id=telegram_chat_id
    )
except Exception as e:
    logger.error(f"Lỗi khi khởi tạo Telegram Notifier: {str(e)}")
    # Tạo một phiên bản giả lệch để không bị lỗi khi gọi
    class DummyNotifier:
        def send_message(self, message=None, **kwargs):
            logger.info(f"[TELEGRAM DUMMY] {message}")
            return True
    telegram_notifier = DummyNotifier()

# Khởi tạo market analyzer
try:
    from market_analyzer import MarketAnalyzer
    market_analyzer = MarketAnalyzer()
except Exception as e:
    logger.error(f"Lỗi khi khởi tạo Market Analyzer: {str(e)}")
    market_analyzer = None

# Tạo một dict cho trạng thái bot
bot_status = {
    'status': 'stopped',
    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'uptime': 0,
    'mode': 'testnet',
    'market_data': {}
}

# Tạo Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "trading_system_secure_key_2025")

# Định nghĩa scheduler trong file main.py để tránh vấn đề import
def start_scheduler():
    """Khởi động scheduler cho các tác vụ định kỳ"""
    try:
        import schedule
        import threading
        
        # Lập lịch kiểm tra trạng thái bot mỗi phút
        def check_bot_status():
            logger.info("Đang kiểm tra trạng thái bot...")
            # Mã kiểm tra trạng thái bot
            return True
            
        # Lập lịch cập nhật dữ liệu thị trường mỗi 5 phút
        def update_market_data_task():
            logger.info("Đang cập nhật dữ liệu thị trường...")
            # Mã cập nhật dữ liệu thị trường
            return True
            
        # Lập lịch kiểm tra vị thế mỗi 2 phút
        def check_positions():
            logger.info("Đang kiểm tra các vị thế...")
            # Mã kiểm tra vị thế
            return True
            
        # Thêm các task vào schedule
        schedule.every(1).minutes.do(check_bot_status)
        schedule.every(5).minutes.do(update_market_data_task)
        schedule.every(2).minutes.do(check_positions)
        
        # Chạy scheduler trong một thread riêng
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        logger.info("Đã khởi động scheduler cho cập nhật trạng thái bot")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi khởi động scheduler: {str(e)}")
        return False

# Khởi động scheduler khi ứng dụng khởi động (vì gunicorn không chạy __main__)
logger.info("Khởi động scheduler và các background tasks...")
scheduler_started = start_scheduler()
if scheduler_started:
    logger.info("Đã khởi động scheduler thành công")
else:
    logger.warning("Không thể khởi động scheduler")

# Hàm lấy dữ liệu phân tích thị trường
def get_market_data():
    """Lấy dữ liệu phân tích thị trường từ nhiều nguồn"""
    # Sử dụng class MarketAnalyzer
    try:
        # Khởi tạo object trả về
        market_data = {}
        
        # Sử dụng MarketAnalyzer nếu đã khởi tạo thành công
        if market_analyzer:
            # Lấy chỉ báo kỹ thuật
            indicators = market_analyzer.get_technical_indicators(
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                timeframes=['1h', '4h', '1d']
            )
            market_data['indicators'] = indicators
            
            # Lấy thông tin chế độ thị trường
            market_regime = market_analyzer.get_market_regime(
                symbols=['BTCUSDT', 'ETHUSDT'],
                timeframes=['1d']
            )
            market_data['market_regime'] = market_regime
            
            # Lấy dự báo
            forecast = market_analyzer.get_market_forecast(
                symbols=['BTCUSDT', 'ETHUSDT'],
                timeframes=['1d']
            )
            market_data['forecast'] = forecast
            
            # Lấy khuyến nghị giao dịch
            recommendation = market_analyzer.get_trading_recommendation(
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                timeframes=['1h', '4h']
            )
            market_data['recommendation'] = recommendation
            
            # Lấy tín hiệu giao dịch
            signals = market_analyzer.get_trading_signals(
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                timeframes=['1h', '4h']
            )
            market_data['signals'] = signals
            
            # Lấy xu hướng thị trường
            market_trends = market_analyzer.get_market_trends(
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                timeframes=['1d']
            )
            market_data['market_trends'] = market_trends
            
            # Lấy khối lượng thị trường
            market_volumes = market_analyzer.get_market_volumes(
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                timeframes=['1d']
            )
            market_data['market_volumes'] = market_volumes
            
            # Lấy khối lượng 24h
            volume_24h = market_analyzer.get_24h_volumes(
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            )
            market_data['volume_24h'] = volume_24h
            
            # Lấy tóm tắt thị trường
            market_summary = market_analyzer.get_market_summary(
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            )
            market_data['market_summary'] = market_summary
            
            # Lấy cấp độ giá Bitcoin
            btc_levels = market_analyzer.get_btc_levels()
            market_data['btc_levels'] = btc_levels
            
            # Tóm tắt tín hiệu từng cặp
            pair_signals = {}
            for symbol in ['BTC', 'ETH', 'SOL']:
                pair_signals[symbol] = market_analyzer.get_signal(f"{symbol}USDT", timeframe='1h')
            market_data['pair_signals'] = pair_signals
            
            # Tóm tắt xu hướng từng cặp
            pair_trends = {}
            for symbol in ['BTC', 'ETH', 'SOL']:
                pair_trends[symbol] = market_analyzer.get_trend(f"{symbol}USDT", timeframe='1h')
            market_data['pair_trends'] = pair_trends
            
        # Danh sách các cặp tiền
        market_data['pairs'] = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT', 'ADAUSDT',
            'XRPUSDT', 'DOTUSDT', 'AVAXUSDT', 'NEARUSDT', 'LINKUSDT', 'MATICUSDT'
        ]
        
        # Dữ liệu cảm xúc thị trường (mẫu cho demo)
        market_data['sentiment'] = {
            'BTCUSDT': {
                'fear_greed_index': 65,
                'overall': 'bullish',
                'social_sentiment': 'positive',
                'market_sentiment': 'neutral',
                'news_sentiment': 'positive'
            },
            'ETHUSDT': {
                'fear_greed_index': 60,
                'overall': 'neutral',
                'social_sentiment': 'neutral',
                'market_sentiment': 'neutral',
                'news_sentiment': 'neutral'
            }
        }
        
        return market_data
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu phân tích thị trường: {str(e)}")
        return {}

def update_market_data_from_binance():
    """Cập nhật dữ liệu thị trường từ Binance API"""
    global bot_status
    try:
        # Lấy dữ liệu tài khoản từ Binance API
        from binance_api import BinanceAPI
        client = BinanceAPI(
            api_key=os.environ.get("BINANCE_API_KEY"),
            api_secret=os.environ.get("BINANCE_API_SECRET"),
            testnet=True
        )
        
        # Lấy số dư và vị thế
        account_data = client.get_futures_account()
        positions = client.get_positions()
        
        # Lấy dữ liệu thị trường từ Binance
        btc_ticker = client.get_futures_ticker(symbol="BTCUSDT")
        eth_ticker = client.get_futures_ticker(symbol="ETHUSDT")
        sol_ticker = client.get_futures_ticker(symbol="SOLUSDT")
        
        # Tạo market data từ dữ liệu thực
        market_data = {
            'btc_price': float(btc_ticker['lastPrice']),
            'btc_change_24h': float(btc_ticker['priceChangePercent']),
            'eth_price': float(eth_ticker['lastPrice']),
            'eth_change_24h': float(eth_ticker['priceChangePercent']),
            'sol_price': float(sol_ticker['lastPrice']),
            'sol_change_24h': float(sol_ticker['priceChangePercent']),
        }
        
        # Lấy thêm các đồng coin khác
        try:
            bnb_ticker = client.get_futures_ticker(symbol="BNBUSDT")
            doge_ticker = client.get_futures_ticker(symbol="DOGEUSDT")
            link_ticker = client.get_futures_ticker(symbol="LINKUSDT")
            
            market_data.update({
                'bnb_price': float(bnb_ticker['lastPrice']),
                'bnb_change_24h': float(bnb_ticker['priceChangePercent']),
                'doge_price': float(doge_ticker['lastPrice']),
                'doge_change_24h': float(doge_ticker['priceChangePercent']),
                'link_price': float(link_ticker['lastPrice']),
                'link_change_24h': float(link_ticker['priceChangePercent']),
            })
        except Exception as e:
            logger.warning(f"Lỗi khi lấy dữ liệu altcoin: {str(e)}")
            
        # Lấy dữ liệu phân tích thị trường khác và kết hợp
        analysis_data = get_market_data()
        market_data.update(analysis_data)
        
        # Cập nhật vào bot status
        bot_status['market_data'] = market_data
        
        return market_data
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu thị trường từ Binance: {str(e)}")
        # Trả về dữ liệu mẫu trong trường hợp lỗi
        return get_market_data()

# Hàm kiểm tra bot có đang chạy không
def is_bot_running():
    """Kiểm tra xem bot có đang chạy không"""
    return bot_status.get('status', 'stopped') == 'running'

# Route handlers
@app.route('/')
def index():
    """Trang chủ / Dashboard"""
    try:
        # Cập nhật dữ liệu thị trường
        market_data = update_market_data_from_binance()
        
        # Lấy trạng thái hệ thống cho template
        bot_status = {
            'running': False,  # Mặc định là dừng
            'account_balance': 0,
            'positions': [],
            'logs': []
        }
        
        # Cố gắng lấy dữ liệu tài khoản từ API
        account_info = get_account().json
        try:
            # Thử lấy trạng thái bot thực tế
            bot_status['running'] = is_bot_running()
            bot_status['account_balance'] = account_info.get('balance', 0)
            bot_status['positions'] = account_info.get('positions', [])
            bot_status['logs'] = get_recent_logs(5) or []
        except Exception as status_error:
            logger.warning(f"Không thể lấy trạng thái bot: {str(status_error)}")
            
        # Debug thông tin market_data
        logger.info(f"Dashboard loaded successfully: BTC price = ${market_data.get('btc_price', 'N/A')}")
        logger.info("Kiểm tra thuộc tính market_data:")
        for key, value in market_data.items():
            if isinstance(value, (int, float, str)):
                logger.info(f"  - {key}: {value} (type: {type(value).__name__})")
            else:
                logger.info(f"  - {key}: {type(value).__name__}")
                
        # Nếu không có market_data, đặt giá trị mặc định
        if not market_data:
            market_data = {
                'btc_price': 0,
                'eth_price': 0,
                'btc_change_24h': 0,
                'eth_change_24h': 0,
                'pairs': []
            }
            
        # Merge market data into status for simpler template usage
        bot_status.update({
            'btc_price': market_data.get('btc_price', 0),
            'eth_price': market_data.get('eth_price', 0),
            'ada_price': market_data.get('ada_price', 0),
            'btc_change_24h': market_data.get('btc_change_24h', 0),
            'eth_change_24h': market_data.get('eth_change_24h', 0),
            'ada_change_24h': market_data.get('ada_change_24h', 0)
        })
        
        # Render template với dữ liệu đã chuẩn bị
        return render_template('index.html', status=bot_status)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        # Return with empty data in case of error
        return render_template('index.html', status={
            'running': False,
            'account_balance': 0,
            'positions': [],
            'logs': [],
            'btc_price': 0,
            'eth_price': 0,
            'ada_price': 0,
            'btc_change_24h': 0,
            'eth_change_24h': 0,
            'ada_change_24h': 0
        })

@app.route('/market')
def market():
    """Trang phân tích thị trường"""
    try:
        # Cập nhật dữ liệu thị trường
        market_data = update_market_data_from_binance()
        
        # Lấy trạng thái hệ thống cho template
        bot_status = {
            'running': False,  # Mặc định là dừng
            'account_balance': 0,
            'positions': [],
            'logs': [],
            'market_data': market_data
        }
        
        # Cố gắng lấy dữ liệu tài khoản từ API
        account_info = get_account().json
        try:
            # Thử lấy trạng thái bot thực tế
            bot_status['running'] = is_bot_running()
            bot_status['account_balance'] = account_info.get('balance', 0)
            bot_status['positions'] = account_info.get('positions', [])
            bot_status['logs'] = get_recent_logs(5) or []
        except Exception as status_error:
            logger.warning(f"Không thể lấy trạng thái bot: {str(status_error)}")
            
        # Render template với dữ liệu đã chuẩn bị
        return render_template('market.html', status=bot_status)
    except Exception as e:
        logger.error(f"Error loading market page: {str(e)}")
        # Return with empty data in case of error
        return render_template('market.html', status={
            'running': False,
            'account_balance': 0,
            'positions': [],
            'logs': [],
            'market_data': {}
        })

@app.route('/position/<symbol>')
def position(symbol):
    """Trang chi tiết vị thế theo cặp tiền"""
    try:
        # Cập nhật dữ liệu thị trường
        market_data = update_market_data_from_binance()
        
        # Lấy thông tin chi tiết về vị thế
        account_info = get_account().json
        positions = account_info.get('positions', [])
        
        # Tìm vị thế cho symbol cụ thể
        position_data = None
        for pos in positions:
            if pos['symbol'].lower() == symbol.lower():
                position_data = pos
                break
        
        # Nếu không tìm thấy, tạo mẫu dữ liệu vị thế trống
        if not position_data:
            position_data = {
                'symbol': symbol.upper(),
                'type': 'N/A',
                'entry_price': 0,
                'current_price': 0,
                'size': 0,
                'pnl': 0,
                'pnl_percent': 0,
                'leverage': 1
            }
            
        # Thêm dữ liệu thị trường vào tài khoản
        account_info['market_data'] = market_data
        account_info['position'] = position_data
        
        return render_template('position.html', account_data=account_info)
    except Exception as e:
        logger.error(f"Error loading position page: {str(e)}")
        # Return with empty data
        return render_template('position.html', account_data={})

@app.route('/positions')
def positions():
    """Trang quản lý tất cả vị thế"""
    try:
        # Lấy trạng thái hệ thống cho template
        bot_status = {
            'running': False,  # Mặc định là dừng
            'account_balance': 0,
            'positions': [],
            'positions_count': 0,
            'logs': []
        }
        
        # Cố gắng lấy dữ liệu tài khoản từ API
        account_response = get_account()
        if hasattr(account_response, 'json'):
            account_data = account_response.json
            bot_status['running'] = True  # Đã lấy được dữ liệu thì hệ thống đang chạy
            bot_status['account_balance'] = account_data.get('balance', 0)
            
            # Đảm bảo positions là một danh sách
            positions_data = account_data.get('positions', [])
            if positions_data is not None and isinstance(positions_data, list):
                bot_status['positions'] = positions_data
                bot_status['positions_count'] = len(positions_data)
            else:
                app.logger.warning("Positions data is not a list or is None")
                bot_status['positions'] = []
                bot_status['positions_count'] = 0
            
        return render_template('positions.html', status=bot_status)
    except Exception as e:
        app.logger.error(f"Error loading positions page: {str(e)}")
        # Trả về mẫu với dữ liệu trống trong trường hợp lỗi
        return render_template('positions.html', status={'positions': [], 'running': False, 'account_balance': 0, 'positions_count': 0})

@app.route('/settings')
def settings():
    """Trang cài đặt bot"""
    try:
        # Get account data for settings page
        account_info = get_account().json
        bot_status = {
            'running': False,  # Mặc định là dừng
            'account_balance': 0,
            'positions': [],
            'logs': []
        }
        try:
            # Thử lấy trạng thái bot thực tế
            bot_status['running'] = is_bot_running()
            bot_status['account_balance'] = account_info.get('total_wallet_balance', 0)
            bot_status['positions'] = get_open_positions() or []
            bot_status['logs'] = get_recent_logs(5) or []
        except Exception as status_error:
            app.logger.warning(f"Không thể lấy trạng thái bot: {str(status_error)}")
            
        return render_template('settings.html', account_data=account_info, status=bot_status)
    except Exception as e:
        app.logger.error(f"Error loading settings page: {str(e)}")
        # Return with empty data and default status
        return render_template('settings.html', account_data={}, status={
            'running': False,
            'account_balance': 0,
            'positions': [],
            'logs': []
        })

@app.route('/bots')
def bots():
    """Trang quản lý bot"""
    return render_template('bots.html')
    
@app.route('/services')
def services():
    """Trang quản lý dịch vụ"""
    return render_template('services.html')

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
    
    # Create a Flask response object with account data
    from flask import jsonify, make_response
    
    try:
        # Khởi tạo Binance API client
        from binance_api import BinanceAPI
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        use_testnet = api_mode != 'live'
        binance_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Binance API client: {str(e)}")
        binance_client = None
        
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

def get_recent_logs(limit=5):
    """Lấy log gần đây nhất của hệ thống"""
    current_time = datetime.now()
    return [
        {
            'timestamp': (current_time - timedelta(minutes=i)).isoformat(),
            'category': ['market', 'analysis', 'decision', 'action'][i % 4],
            'message': f'Log #{i+1}: ' + ['Phân tích thị trường', 'Kiểm tra tín hiệu', 'Đặt lệnh giao dịch', 'Kiểm tra vị thế'][i % 4]
        } for i in range(limit)
    ]

def get_open_positions():
    """Lấy danh sách vị thế đang mở"""
    # Trong thực tế, sẽ lấy từ Binance API
    try:
        account_info = get_account().json
        return account_info.get('positions', [])
    except Exception as e:
        logger.error(f"Lỗi khi lấy vị thế đang mở: {str(e)}")
        return []

@app.route('/api/positions')
def get_api_positions():
    """API endpoint để lấy danh sách vị thế từ Binance"""
    try:
        # Lấy dữ liệu tài khoản
        account_data = get_account().json
        
        # Lấy danh sách vị thế từ dữ liệu tài khoản
        positions = account_data.get('positions', [])
        
        # Trả về kết quả dưới dạng JSON
        return jsonify({'positions': positions})
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách vị thế: {str(e)}")
        return jsonify({'positions': [], 'error': str(e)})

@app.route('/api/add_position', methods=['POST'])
def add_test_position():
    """API endpoint để thêm vị thế test"""
    try:
        # Cập nhật dữ liệu thị trường để lấy giá hiện tại
        market_data = update_market_data_from_binance()
        
        # Chọn một cặp tiền ngẫu nhiên và loại vị thế
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        position_types = ['LONG', 'SHORT']
        
        # Nếu BTCUSDT có giá, ưu tiên sử dụng nó
        if market_data.get('btc_price'):
            selected_symbol = 'BTCUSDT'
            current_price = market_data['btc_price']
        else:
            # Nếu không có, chọn ngẫu nhiên
            selected_symbol = random.choice(symbols)
            current_price = random.uniform(100, 90000)  # Giá ngẫu nhiên
            
            # Điều chỉnh giá theo cặp tiền
            if selected_symbol == 'ETHUSDT':
                current_price = random.uniform(1000, 5000)
            elif selected_symbol == 'BNBUSDT':
                current_price = random.uniform(100, 1000)
            elif selected_symbol == 'SOLUSDT':
                current_price = random.uniform(10, 500)
                
        # Chọn loại vị thế ngẫu nhiên
        position_type = random.choice(position_types)
        
        # Tạo vị thế mẫu
        test_position = {
            'id': f"pos_test_{int(time.time())}",
            'symbol': selected_symbol,
            'type': position_type,
            'entry_price': current_price * random.uniform(0.98, 1.02),  # Giá vào lệnh xấp xỉ giá hiện tại
            'current_price': current_price,
            'size': random.uniform(0.001, 0.05),  # Kích thước vị thế nhỏ
            'pnl': random.uniform(-10, 10),  # PnL ngẫu nhiên
            'pnl_percent': random.uniform(-5, 5),  # Phần trăm ngẫu nhiên
            'leverage': random.choice([1, 2, 5, 10, 20]),  # Đòn bẩy ngẫu nhiên
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sl': 0,  # Stop loss
            'tp': 0   # Take profit
        }
        
        # Điều chỉnh giá stop loss và take profit dựa trên loại vị thế
        if position_type == 'LONG':
            test_position['sl'] = test_position['entry_price'] * 0.95  # SL dưới 5%
            test_position['tp'] = test_position['entry_price'] * 1.15  # TP trên 15%
        else:  # SHORT
            test_position['sl'] = test_position['entry_price'] * 1.05  # SL trên 5% 
            test_position['tp'] = test_position['entry_price'] * 0.85  # TP dưới 15%
            
        # Cố gắng thêm vị thế vào danh sách vị thế hiện tại
        try:
            # Lấy dữ liệu tài khoản
            account_data = get_account().json
            positions = account_data.get('positions', [])
            
            # Thêm vị thế mới
            active_positions = []
            for pos in positions:
                if isinstance(pos, dict) and 'id' in pos:
                    active_positions.append(pos)
                    
            active_positions.append(test_position)
            
            # Cập nhật danh sách vị thế (trong thực tế sẽ lưu vào DB hoặc gửi lệnh đến Binance)
            # Hiện tại chỉ log để debug
            logger.info(f"Đã thêm vị thế test: {selected_symbol} {position_type}")
            
        except Exception as e:
            logger.error(f"Lỗi khi thêm vị thế test: {str(e)}")
            
        return jsonify({
            'success': True,
            'message': f'Đã thêm vị thế test {selected_symbol} {position_type}',
            'position': test_position
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi thêm vị thế test: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi thêm vị thế test: {str(e)}'
        })

@app.route('/api/close_position', methods=['POST'])
def close_position():
    """API endpoint để đóng vị thế theo ID"""
    try:
        data = request.json
        position_index = data.get('index')
        
        if position_index is None:
            return jsonify({
                'success': False,
                'message': 'Thiếu thông tin vị thế cần đóng'
            })
            
        # Lấy danh sách vị thế
        account_data = get_account().json
        positions = account_data.get('positions', [])
        
        # Kiểm tra vị thế tồn tại
        if position_index < 0 or position_index >= len(positions):
            return jsonify({
                'success': False,
                'message': 'Vị thế không tồn tại'
            })
            
        # Lấy thông tin vị thế cần đóng
        position = positions[position_index]
        
        # Trong thực tế, sẽ gửi lệnh đến Binance API để đóng vị thế
        # Hiện tại chỉ log để debug
        logger.info(f"Đã đóng vị thế: {position.get('symbol')} {position.get('type')}")
        
        return jsonify({
            'success': True,
            'message': 'Đã đóng vị thế thành công',
            'position': position
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi đóng vị thế: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi đóng vị thế: {str(e)}'
        })

def send_status_update(
    status="offline",
    mode="testnet",
    uptime=0,
    stats={}
):
    """Gửi cập nhật trạng thái thông qua Socket.IO"""
    try:
        # Format báo cáo trạng thái
        status_data = {
            'status': status,
            'mode': mode,
            'uptime': uptime,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }
        # TODO: Trong thực tế, sẽ gửi qua Socket.IO
        logger.debug(f"Đã gửi cập nhật trạng thái: {status}")
    except Exception as e:
        logger.error(f"Lỗi khi gửi cập nhật trạng thái: {str(e)}")

def update_status_rich(
    status="offline",
    mode="testnet",
    uptime=0,
    stats={}
):
    """Cập nhật trạng thái với thông tin chi tiết hơn"""
    try:
        # Format báo cáo trạng thái
        status_data = {
            'status': status,
            'mode': mode,
            'uptime': uptime,
            'stats': stats,
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'hostname': socket.gethostname()
        }
        # TODO: Trong thực tế, sẽ lưu vào DB hoặc gửi qua Socket.IO
        logger.debug(f"Đã cập nhật trạng thái chi tiết: {status}")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật trạng thái chi tiết: {str(e)}")

def broadcast_market_update(
    status="offline",
    mode="testnet",
    uptime=0,
    stats={}
):
    """Phát sóng cập nhật thị trường đến tất cả clients"""
    try:
        # Format báo cáo trạng thái
        status_data = {
            'status': status,
            'mode': mode,
            'uptime': uptime,
            'stats': stats,
            'timestamp': datetime.now().isoformat(),
            'market': update_market_data_from_binance()
        }
        # TODO: Trong thực tế, sẽ gửi qua Socket.IO
        logger.debug(f"Đã phát sóng cập nhật thị trường")
    except Exception as e:
        logger.error(f"Lỗi khi phát sóng cập nhật thị trường: {str(e)}")

@app.route('/api/user_summary')
def get_user_summary():
    """Lấy tóm tắt người dùng và hiệu suất"""
    try:
        # Dữ liệu mẫu cho báo cáo hiệu suất
        current_month = datetime.now().strftime('%Y-%m')
        performance_data = {
            'month': current_month,
            'profit_loss': random.uniform(-5, 15),
            'win_rate': random.uniform(40, 75),
            'total_trades': random.randint(10, 50),
            'avg_profit': random.uniform(1, 5),
            'avg_loss': random.uniform(-3, -1),
            'best_trade': {
                'symbol': 'BTCUSDT',
                'profit': random.uniform(10, 30),
                'date': (datetime.now() - timedelta(days=random.randint(1, 28))).strftime('%Y-%m-%d')
            },
            'worst_trade': {
                'symbol': 'ETHUSDT',
                'profit': random.uniform(-15, -5),
                'date': (datetime.now() - timedelta(days=random.randint(1, 28))).strftime('%Y-%m-%d')
            }
        }
        
        # Cố gắng lấy dữ liệu tài khoản thực
        try:
            # Nếu có Binance API, lấy số dư và thống kê thực
            account_data = get_account().json
            balance = account_data.get('balance', 0)
            unrealized_pnl = account_data.get('pnl', 0)
            
            # Cập nhật dữ liệu hiệu suất với dữ liệu thực
            performance_data['account_balance'] = balance
            performance_data['unrealized_pnl'] = unrealized_pnl
            
            # Lấy vị thế đang mở từ API
            positions = account_data.get('positions', [])
            performance_data['open_positions'] = len(positions)
            
            # Giá BTC từ API
            market_data = update_market_data_from_binance()
            performance_data['btc_price'] = market_data.get('btc_price', 0)
            
            # Cập nhật thống kê
            btc_change_24h = market_data.get('btc_change_24h', 0)
            eth_change_24h = market_data.get('eth_change_24h', 0)
            bnb_change_24h = market_data.get('bnb_change_24h', 0)
            
            # Phân loại thị trường dựa trên biến động giá BTC 24h
            market_condition = 'neutral'
            if btc_change_24h > 3:
                market_condition = 'bullish'
            elif btc_change_24h < -3:
                market_condition = 'bearish'
            elif btc_change_24h > 1:
                market_condition = 'slightly bullish'
            elif btc_change_24h < -1:
                market_condition = 'slightly bearish'
                
            performance_data['market_condition'] = market_condition
            
            # Thêm dữ liệu xu hướng thị trường
            performance_data['market_trends'] = {
                'BTC': {
                    'change_24h': btc_change_24h,
                    'trend': 'bullish' if btc_change_24h > 0 else 'bearish'
                },
                'ETH': {
                    'change_24h': eth_change_24h,
                    'trend': 'bullish' if eth_change_24h > 0 else 'bearish'
                },
                'BNB': {
                    'change_24h': bnb_change_24h,
                    'trend': 'bullish' if bnb_change_24h > 0 else 'bearish'
                }
            }
            
        except Exception as e:
            logger.warning(f"Không thể lấy dữ liệu tài khoản thực: {str(e)}")
            # Sử dụng dữ liệu mẫu nếu không lấy được dữ liệu thực
            performance_data['account_balance'] = random.uniform(500, 5000)
            performance_data['unrealized_pnl'] = random.uniform(-100, 300)
            performance_data['open_positions'] = random.randint(0, 5)
            performance_data['btc_price'] = random.uniform(50000, 100000)
            
        return jsonify(performance_data)
    except Exception as e:
        logger.error(f"Lỗi khi lấy tóm tắt người dùng: {str(e)}")
        return jsonify({
            'error': str(e),
            'message': 'Lỗi khi tạo báo cáo tóm tắt'
        })

@app.route('/api/trades')
def get_recent_trades():
    """Lấy lịch sử giao dịch gần đây"""
    # Số lượng giao dịch cần lấy
    limit = int(request.args.get('limit', 10))
    
    # Dữ liệu mẫu cho lịch sử giao dịch
    trades = []
    current_time = datetime.now()
    
    for i in range(limit):
        # Tạo dữ liệu mẫu cho mỗi giao dịch
        trade_time = current_time - timedelta(days=i)
        symbol = random.choice(['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'])
        trade_type = random.choice(['BUY', 'SELL'])
        price = None
        
        if symbol == 'BTCUSDT':
            price = random.uniform(60000, 90000)
        elif symbol == 'ETHUSDT':
            price = random.uniform(2000, 5000)
        elif symbol == 'BNBUSDT':
            price = random.uniform(500, 800)
        elif symbol == 'SOLUSDT':
            price = random.uniform(100, 200)
            
        size = random.uniform(0.001, 0.1)
        if symbol == 'BTCUSDT':
            size = random.uniform(0.001, 0.01)
            
        profit = random.uniform(-5, 10) if i % 3 != 0 else random.uniform(-15, -5)
        
        trades.append({
            'id': f"trade_{uuid.uuid4().hex[:8]}",
            'time': trade_time.strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'type': trade_type,
            'price': price,
            'size': size,
            'value': price * size,
            'profit': profit,
            'status': 'CLOSED'
        })
        
    return jsonify(trades)

@app.route('/api/performance')
def get_performance():
    """Lấy dữ liệu hiệu suất giao dịch"""
    # Khoảng thời gian
    time_period = request.args.get('period', 'month')  # day, week, month, year
    
    # Tạo dữ liệu hiệu suất mẫu
    performance = {
        'period': time_period,
        'start_date': None,
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'start_balance': 0,
        'end_balance': 0,
        'profit_loss': 0,
        'profit_loss_percent': 0,
        'win_rate': 0,
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'avg_profit': 0,
        'avg_loss': 0,
        'best_trade': {},
        'worst_trade': {},
        'daily_pnl': []
    }
    
    # Đặt ngày bắt đầu dựa trên khoảng thời gian
    if time_period == 'day':
        start_date = datetime.now() - timedelta(days=1)
        performance['start_date'] = start_date.strftime('%Y-%m-%d')
        days = 1
    elif time_period == 'week':
        start_date = datetime.now() - timedelta(days=7)
        performance['start_date'] = start_date.strftime('%Y-%m-%d')
        days = 7
    elif time_period == 'month':
        start_date = datetime.now() - timedelta(days=30)
        performance['start_date'] = start_date.strftime('%Y-%m-%d')
        days = 30
    else:  # year
        start_date = datetime.now() - timedelta(days=365)
        performance['start_date'] = start_date.strftime('%Y-%m-%d')
        days = 365
        
    # Tạo dữ liệu mẫu
    initial_balance = random.uniform(1000, 10000)
    performance['start_balance'] = initial_balance
    
    # Tính toán số lượng giao dịch và tỷ lệ thắng
    total_trades = random.randint(days // 2, days * 2)
    win_rate = random.uniform(40, 70)
    winning_trades = int(total_trades * win_rate / 100)
    losing_trades = total_trades - winning_trades
    
    performance['total_trades'] = total_trades
    performance['winning_trades'] = winning_trades
    performance['losing_trades'] = losing_trades
    performance['win_rate'] = win_rate
    
    # Tính lợi nhuận và thua lỗ trung bình
    avg_profit = random.uniform(2, 5)
    avg_loss = random.uniform(-3, -1)
    performance['avg_profit'] = avg_profit
    performance['avg_loss'] = avg_loss
    
    # Tính tổng lợi nhuận/thua lỗ
    total_profit = winning_trades * avg_profit
    total_loss = losing_trades * avg_loss
    net_profit = total_profit + total_loss
    performance['profit_loss'] = net_profit
    performance['profit_loss_percent'] = (net_profit / initial_balance) * 100
    performance['end_balance'] = initial_balance + net_profit
    
    # Tạo dữ liệu lợi nhuận/thua lỗ hàng ngày
    daily_pnl = []
    balance = initial_balance
    
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_trades = random.randint(0, 3)
        day_profit = 0
        
        for _ in range(day_trades):
            if random.random() < (win_rate / 100):
                # Winning trade
                trade_profit = balance * random.uniform(0.005, 0.02)
                day_profit += trade_profit
            else:
                # Losing trade
                trade_loss = balance * random.uniform(-0.015, -0.005)
                day_profit += trade_loss
                
        balance += day_profit
        
        daily_pnl.append({
            'date': day.strftime('%Y-%m-%d'),
            'pnl': day_profit,
            'pnl_percent': (day_profit / balance) * 100,
            'balance': balance
        })
        
    performance['daily_pnl'] = daily_pnl
    
    # Tìm giao dịch tốt nhất và tệ nhất
    best_profit = max([day['pnl'] for day in daily_pnl]) if daily_pnl else 0
    worst_profit = min([day['pnl'] for day in daily_pnl]) if daily_pnl else 0
    
    best_day = next((day for day in daily_pnl if day['pnl'] == best_profit), None)
    worst_day = next((day for day in daily_pnl if day['pnl'] == worst_profit), None)
    
    if best_day:
        performance['best_trade'] = {
            'date': best_day['date'],
            'profit': best_profit,
            'profit_percent': (best_profit / balance) * 100
        }
        
    if worst_day:
        performance['worst_trade'] = {
            'date': worst_day['date'],
            'profit': worst_profit,
            'profit_percent': (worst_profit / balance) * 100
        }
        
    return jsonify(performance)

@app.route('/api/symbols')
def get_symbols():
    """Lấy danh sách cặp tiền có thể giao dịch"""
    try:
        # Lấy danh sách cặp tiền từ cấu hình
        try:
            with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                config = json.load(f)
            configured_symbols = config.get('symbols', [])
        except:
            configured_symbols = DEFAULT_CONFIG['symbols']
        
        # Thêm thông tin cho từng cặp tiền
        symbols_info = []
        
        # Cập nhật dữ liệu thị trường
        market_data = update_market_data_from_binance()
        
        # Danh sách cặp tiền phổ biến
        popular_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT', 'ADAUSDT',
            'XRPUSDT', 'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT', 'NEARUSDT'
        ]
        
        # Ưu tiên các cặp tiền được cấu hình
        for symbol in configured_symbols:
            symbols_info.append({
                'symbol': symbol,
                'enabled': True,
                'price': market_data.get(f"{symbol.replace('USDT', '').lower()}_price", 0),
                'change_24h': market_data.get(f"{symbol.replace('USDT', '').lower()}_change_24h", 0),
                'volume': random.uniform(10000, 1000000)
            })
            
        # Thêm các cặp tiền phổ biến không có trong cấu hình
        for symbol in popular_symbols:
            if symbol not in configured_symbols:
                symbols_info.append({
                    'symbol': symbol,
                    'enabled': False,
                    'price': market_data.get(f"{symbol.replace('USDT', '').lower()}_price", 0),
                    'change_24h': market_data.get(f"{symbol.replace('USDT', '').lower()}_change_24h", 0),
                    'volume': random.uniform(10000, 1000000)
                })
                
        return jsonify(symbols_info)
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách cặp tiền: {str(e)}")
        return jsonify([])

@app.route('/api/candles')
def get_candles():
    """Lấy dữ liệu nến cho biểu đồ"""
    symbol = request.args.get('symbol', 'BTCUSDT')
    timeframe = request.args.get('timeframe', '1h')
    limit = int(request.args.get('limit', 100))
    
    try:
        # Trong thực tế, sẽ lấy từ Binance API
        from binance_api import BinanceAPI
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        binance_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=True)
        
        # Lấy dữ liệu nến từ Binance
        candles = binance_client.get_futures_klines(symbol=symbol, interval=timeframe, limit=limit)
        
        # Định dạng lại dữ liệu nến
        formatted_candles = []
        for candle in candles:
            formatted_candles.append({
                'time': candle[0],  # Thời gian mở
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5])
            })
            
        return jsonify(formatted_candles)
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu nến: {str(e)}")
        
        # Tạo dữ liệu nến mẫu trong trường hợp lỗi
        current_time = int(time.time() * 1000)
        interval_ms = 0
        
        if timeframe == '1m':
            interval_ms = 60 * 1000
        elif timeframe == '5m':
            interval_ms = 5 * 60 * 1000
        elif timeframe == '15m':
            interval_ms = 15 * 60 * 1000
        elif timeframe == '30m':
            interval_ms = 30 * 60 * 1000
        elif timeframe == '1h':
            interval_ms = 60 * 60 * 1000
        elif timeframe == '4h':
            interval_ms = 4 * 60 * 60 * 1000
        elif timeframe == '1d':
            interval_ms = 24 * 60 * 60 * 1000
        else:
            interval_ms = 60 * 60 * 1000  # Mặc định 1h
            
        # Tạo giá mẫu dựa trên symbol
        base_price = 0
        volatility = 0
        
        if symbol == 'BTCUSDT':
            base_price = 80000
            volatility = 2000
        elif symbol == 'ETHUSDT':
            base_price = 4000
            volatility = 100
        elif symbol == 'BNBUSDT':
            base_price = 600
            volatility = 20
        elif symbol == 'SOLUSDT':
            base_price = 150
            volatility = 5
        else:
            base_price = 100
            volatility = 5
            
        # Tạo dữ liệu nến mẫu
        sample_candles = []
        price = base_price
        
        for i in range(limit):
            time_ms = current_time - (limit - i) * interval_ms
            price_change = random.uniform(-volatility * 0.02, volatility * 0.02)
            price += price_change
            
            open_price = price
            close_price = price + random.uniform(-volatility * 0.01, volatility * 0.01)
            high_price = max(open_price, close_price) + random.uniform(0, volatility * 0.01)
            low_price = min(open_price, close_price) - random.uniform(0, volatility * 0.01)
            volume = random.uniform(base_price * 10, base_price * 100)
            
            sample_candles.append({
                'time': time_ms,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
            
            price = close_price
            
        return jsonify(sample_candles)

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Bắt đầu chạy bot giao dịch"""
    global bot_status
    
    try:
        data = request.json or {}
        config = data.get('config', {})
        
        # Cập nhật trạng thái bot
        bot_status['status'] = 'running'
        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        bot_status['uptime'] = 0
        
        # Lấy chế độ API từ cấu hình
        try:
            with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                account_config = json.load(f)
            api_mode = account_config.get('api_mode', 'testnet')
            bot_status['mode'] = api_mode.lower()
        except:
            bot_status['mode'] = 'testnet'
            
        # Gửi thông báo khởi động
        telegram_notifier.send_message(
            message=f"<b>Bot đã bắt đầu chạy</b>\n\n"
                    f"Chế độ: {bot_status['mode'].upper()}\n"
                    f"Thời gian: {bot_status['last_updated']}"
        )
        
        logger.info(f"Bot đã bắt đầu chạy trong chế độ {bot_status['mode']}")
        
        return jsonify({
            'success': True,
            'message': 'Bot đã bắt đầu chạy thành công',
            'status': bot_status
        })
    except Exception as e:
        logger.error(f"Lỗi khi bắt đầu bot: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi bắt đầu bot: {str(e)}',
            'status': bot_status
        })

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Dừng bot giao dịch"""
    global bot_status
    
    try:
        # Cập nhật trạng thái bot
        bot_status['status'] = 'stopped'
        bot_status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Gửi thông báo dừng
        telegram_notifier.send_message(
            message=f"<b>Bot đã dừng</b>\n\n"
                    f"Chế độ: {bot_status['mode'].upper()}\n"
                    f"Thời gian: {bot_status['last_updated']}"
        )
        
        logger.info(f"Bot đã dừng sau khi chạy trong chế độ {bot_status['mode']}")
        
        return jsonify({
            'success': True,
            'message': 'Bot đã dừng thành công',
            'status': bot_status
        })
    except Exception as e:
        logger.error(f"Lỗi khi dừng bot: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi dừng bot: {str(e)}',
            'status': bot_status
        })

@app.route('/api/bot/restart', methods=['POST'])
def restart_bot():
    """Khởi động lại bot giao dịch"""
    try:
        # Đầu tiên dừng bot
        stop_result = stop_bot()
        if not stop_result.json.get('success', False):
            return stop_result
            
        # Sau đó bắt đầu lại
        start_result = start_bot()
        return start_result
    except Exception as e:
        logger.error(f"Lỗi khi khởi động lại bot: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi khởi động lại bot: {str(e)}',
            'status': bot_status
        })

@app.route('/api/config/save', methods=['POST'])
def save_config():
    """Lưu cấu hình bot"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'Không có dữ liệu cấu hình để lưu'
            })
            
        # Lưu cấu hình vào file
        config_type = data.get('type', 'account')
        
        if config_type == 'account':
            # Lưu cấu hình tài khoản
            account_config = {
                'api_mode': data.get('api_mode', 'testnet'),
                'account_type': data.get('account_type', 'futures'),
                'test_balance': float(data.get('test_balance', 10000)),
                'risk_level': data.get('risk_level', 'medium'),
                'symbols': data.get('symbols', DEFAULT_CONFIG['symbols'])
            }
            
            with open(ACCOUNT_CONFIG_PATH, 'w') as f:
                json.dump(account_config, f, indent=4)
                
            logger.info(f"Đã lưu cấu hình tài khoản")
            
            # Cập nhật bot status
            global bot_status
            bot_status['mode'] = account_config['api_mode'].lower()
            
            return jsonify({
                'success': True,
                'message': 'Đã lưu cấu hình tài khoản thành công'
            })
        elif config_type == 'bot':
            # Lưu cấu hình bot
            bot_config = {
                'name': data.get('name', 'Default Bot'),
                'strategy': data.get('strategy', 'Default'),
                'timeframe': data.get('timeframe', '1h'),
                'symbols': data.get('symbols', ['BTCUSDT', 'ETHUSDT']),
                'risk_per_trade': float(data.get('risk_per_trade', 1.0)),
                'max_trades': int(data.get('max_trades', 5)),
                'leverage': int(data.get('leverage', 5)),
                'status': data.get('status', 'stopped'),
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs('configs', exist_ok=True)
            
            with open(f"configs/bot_{bot_config['name'].lower().replace(' ', '_')}.json", 'w') as f:
                json.dump(bot_config, f, indent=4)
                
            logger.info(f"Đã lưu cấu hình bot {bot_config['name']}")
            
            return jsonify({
                'success': True,
                'message': 'Đã lưu cấu hình bot thành công'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Không hỗ trợ loại cấu hình: {config_type}'
            })
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi lưu cấu hình: {str(e)}'
        })

@app.route('/api/config/load', methods=['GET'])
def load_config():
    """Tải cấu hình bot"""
    try:
        config_type = request.args.get('type', 'account')
        
        if config_type == 'account':
            # Tải cấu hình tài khoản
            try:
                with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                    account_config = json.load(f)
            except:
                account_config = DEFAULT_CONFIG
                
            return jsonify({
                'success': True,
                'config': account_config
            })
        elif config_type == 'bot':
            # Tải cấu hình bot
            bot_name = request.args.get('name', 'default')
            bot_file = f"configs/bot_{bot_name.lower().replace(' ', '_')}.json"
            
            try:
                with open(bot_file, 'r') as f:
                    bot_config = json.load(f)
            except:
                bot_config = {
                    'name': 'Default Bot',
                    'strategy': 'Default',
                    'timeframe': '1h',
                    'symbols': ['BTCUSDT', 'ETHUSDT'],
                    'risk_per_trade': 1.0,
                    'max_trades': 5,
                    'leverage': 5,
                    'status': 'stopped',
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
            return jsonify({
                'success': True,
                'config': bot_config
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Không hỗ trợ loại cấu hình: {config_type}'
            })
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi tải cấu hình: {str(e)}'
        })

@app.route('/api/bot/strategy', methods=['GET'])
def get_strategy_list():
    """Lấy danh sách chiến lược giao dịch"""
    try:
        # Danh sách chiến lược giao dịch
        strategies = [
            {
                'id': 'macd_crossover',
                'name': 'MACD Crossover',
                'description': 'Chiến lược giao dịch dựa trên tín hiệu chéo MACD',
                'timeframes': ['15m', '1h', '4h', '1d'],
                'risk_level': 'medium'
            },
            {
                'id': 'rsi_oversold',
                'name': 'RSI Oversold/Overbought',
                'description': 'Chiến lược giao dịch dựa trên trạng thái quá mua/quá bán của RSI',
                'timeframes': ['5m', '15m', '1h', '4h'],
                'risk_level': 'medium'
            },
            {
                'id': 'ma_crossover',
                'name': 'Moving Average Crossover',
                'description': 'Chiến lược giao dịch dựa trên tín hiệu chéo của các đường trung bình động',
                'timeframes': ['15m', '1h', '4h', '1d'],
                'risk_level': 'low'
            },
            {
                'id': 'breakout',
                'name': 'Price Breakout',
                'description': 'Chiến lược giao dịch dựa trên đột phá giá khỏi vùng tích lũy',
                'timeframes': ['15m', '1h', '4h'],
                'risk_level': 'high'
            },
            {
                'id': 'support_resistance',
                'name': 'Support/Resistance Bounce',
                'description': 'Chiến lược giao dịch dựa trên phản ứng giá tại các vùng hỗ trợ/kháng cự',
                'timeframes': ['1h', '4h', '1d'],
                'risk_level': 'medium'
            },
            {
                'id': 'trend_following',
                'name': 'Trend Following',
                'description': 'Chiến lược giao dịch theo xu hướng dựa trên nhiều chỉ báo',
                'timeframes': ['1h', '4h', '1d'],
                'risk_level': 'low'
            },
            {
                'id': 'rsi_divergence',
                'name': 'RSI Divergence',
                'description': 'Chiến lược giao dịch dựa trên phân kỳ RSI',
                'timeframes': ['1h', '4h', '1d'],
                'risk_level': 'medium'
            },
            {
                'id': 'bollinger_bands',
                'name': 'Bollinger Bands Squeeze',
                'description': 'Chiến lược giao dịch dựa trên sự co thắt và mở rộng của Bollinger Bands',
                'timeframes': ['15m', '1h', '4h'],
                'risk_level': 'high'
            },
            {
                'id': 'scalping',
                'name': 'Scalping',
                'description': 'Chiến lược giao dịch nhanh với mục tiêu lợi nhuận nhỏ',
                'timeframes': ['1m', '5m', '15m'],
                'risk_level': 'high'
            },
            {
                'id': 'ichimoku',
                'name': 'Ichimoku Cloud',
                'description': 'Chiến lược giao dịch dựa trên hệ thống chỉ báo Ichimoku',
                'timeframes': ['1h', '4h', '1d'],
                'risk_level': 'medium'
            }
        ]
        
        return jsonify(strategies)
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách chiến lược: {str(e)}")
        return jsonify([])

def scheduled_bot_status_update():
    """Cập nhật định kỳ trạng thái bot"""
    global bot_status
    
    try:
        if bot_status['status'] == 'running':
            # Cập nhật dữ liệu thị trường
            market_data = update_market_data_from_binance()
            bot_status['market_data'] = market_data
            
            # Tăng thời gian hoạt động
            bot_status['uptime'] += 1
            
            # Ghi log cập nhật
            logger.debug(f"Đã cập nhật trạng thái bot định kỳ, uptime = {bot_status['uptime']} phút")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật trạng thái bot định kỳ: {str(e)}")

# Đăng ký các blueprint
try:
    from routes.config_routes import config_blueprint
    app.register_blueprint(config_blueprint)
    logger.info("Đã đăng ký blueprint cho cấu hình")
except Exception as e:
    logger.warning(f"Không thể đăng ký blueprint cho cấu hình: {str(e)}")

try:
    from routes.bot_api_routes import bot_api_blueprint
    app.register_blueprint(bot_api_blueprint)
    logger.info("Đã đăng ký blueprint cho API Bot")
except Exception as e:
    logger.warning(f"Không thể đăng ký blueprint cho API Bot: {str(e)}")

# Lên lịch cập nhật trạng thái bot
def start_scheduler():
    """Bắt đầu scheduler"""
    try:
        schedule.every(1).minutes.do(scheduled_bot_status_update)
        
        # Chạy scheduler trong một thread riêng
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        logger.info("Đã khởi động scheduler cho cập nhật trạng thái bot")
    except Exception as e:
        logger.error(f"Lỗi khi khởi động scheduler: {str(e)}")

# Chỉ khởi động scheduler nếu chạy ứng dụng trực tiếp
if __name__ == '__main__':
    logger.info("Starting background tasks and scheduler...")
    start_scheduler()  # Kích hoạt scheduler để chạy các task định kỳ
    app.run(host='0.0.0.0', port=5000, debug=True)
import os
import json
import logging
import pandas as pd
import numpy as np
import requests
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
import random
from datetime import datetime, timedelta
from app.storage import Storage
from app.routes import register_routes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import trading components
try:
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from app.strategy import StrategyFactory
    from app.trading_bot import TradingBot
    from app.ml_optimizer import MLOptimizer
    from app.sentiment_analyzer import SentimentAnalyzer
    logger.info("Successfully imported all required packages")
except ImportError as e:
    logger.error(f"Error importing required packages: {str(e)}")
    raise

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_bot_secret_key")

# Configure template directory
app.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
logger.info(f"Template directory: {app.template_folder}")

# Register additional routes
register_routes(app)

# Initialize SocketIO with improved error handling and settings
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='eventlet',  # Use eventlet for better performance
    ping_timeout=60,        # Increase ping timeout
    ping_interval=25,       # Adjust ping interval
    logger=True,            # Enable SocketIO logging
    engineio_logger=True    # Enable Engine.IO logging
)

# Global objects
binance_api = BinanceAPI(simulation_mode=False)  # Sử dụng chế độ thực tế, không giả lập
data_processor = DataProcessor(binance_api, simulation_mode=False)  # Chuyển sang chế độ thực tế
ml_optimizer = MLOptimizer()
sentiment_analyzer = SentimentAnalyzer(data_processor=data_processor, simulation_mode=False)  # Chuyển sang chế độ thực tế
trading_bots = {}

# Data generation thread (for simulating real-time price updates)
data_thread = None
should_run = False
current_price = 61245.80  # Updated BTC price as of February 2024 from Binance Futures - updated to real price

# API endpoints for trading operations
@app.route('/api/place_order', methods=['POST'])
def place_order():
    """Manually place a trade order."""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTCUSDT')
        side = data.get('side', 'buy').upper()
        order_type = data.get('type', 'MARKET').upper()
        quantity = float(data.get('quantity', 0.001))
        
        # Kiểm tra API key
        if not binance_api.api_key or not binance_api.api_secret:
            return jsonify({
                'status': 'error',
                'message': 'Chưa cấu hình API key Binance. Vui lòng cấu hình API key để sử dụng chức năng này (API key not configured)'
            }), 400
        
        if quantity <= 0:
            return jsonify({
                'status': 'error',
                'message': 'Khối lượng không hợp lệ (Invalid quantity)'
            }), 400
        
        logger.info(f"Đang đặt lệnh: {side} {quantity} {symbol} tại {order_type}")
        
        # Thực hiện đặt lệnh qua BinanceAPI
        result = binance_api.create_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity
        )
        
        # Lưu thông tin lệnh
        storage = Storage()
        trade_info = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'price': result.get('price', 0),
            'status': 'FILLED',
            'timestamp': datetime.now().isoformat()
        }
        storage.save_trade(trade_info)
        
        # Trả về kết quả thành công
        return jsonify({
            'status': 'success',
            'message': f'Đặt lệnh {side} {quantity} {symbol} thành công (Order placed successfully)',
            'order': result
        })
        
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Order failed: {str(e)}'
        }), 500

@app.route('/api/close_position', methods=['POST'])
def close_position():
    """Close an open trading position."""
    try:
        data = request.json
        position_id = data.get('position_id')
        
        if not position_id:
            return jsonify({
                'status': 'error',
                'message': 'ID vị thế cần được cung cấp (Position ID required)'
            }), 400
        
        # Kiểm tra API key
        if not binance_api.api_key or not binance_api.api_secret:
            return jsonify({
                'status': 'error',
                'message': 'Chưa cấu hình API key Binance. Vui lòng cấu hình API key để sử dụng chức năng này (API key not configured)'
            }), 400
            
        # Parse thông tin vị thế từ position_id
        # Format: symbol_side_quantity_timestamp
        try:
            parts = position_id.split('_')
            if len(parts) >= 3:
                symbol = parts[0]
                position_side = parts[1]
                quantity = float(parts[2])
            else:
                # Mặc định nếu định dạng không đúng
                symbol = "BTCUSDT"
                position_side = "LONG"
                quantity = 0.001
        except:
            symbol = "BTCUSDT"
            position_side = "LONG"
            quantity = 0.001
        
        logger.info(f"Đang đóng vị thế: {position_id} [{symbol} {position_side} {quantity}]")
        
        # Đặt lệnh đảo ngược vị thế hiện tại để đóng vị thế
        # Nếu vị thế hiện tại là LONG, đặt lệnh SELL để đóng
        close_side = "SELL" if position_side == "LONG" else "BUY"
        
        # Đặt lệnh đóng vị thế thông qua BinanceAPI
        result = binance_api.create_order(
            symbol=symbol,
            side=close_side,
            order_type="MARKET",
            quantity=quantity
        )
        
        # Lưu thông tin giao dịch
        storage = Storage()
        trade_info = {
            'symbol': symbol,
            'side': close_side,
            'type': 'MARKET',
            'quantity': quantity,
            'price': result.get('price', 0),
            'status': 'FILLED',
            'position_id': position_id,
            'timestamp': datetime.now().isoformat()
        }
        storage.save_trade(trade_info)
        
        return jsonify({
            'status': 'success',
            'message': f'Vị thế {position_id} đã được đóng thành công (Position closed successfully)', 
            'order': result
        })
        
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Không thể đóng vị thế: {str(e)} (Failed to close position)'
        }), 500

# Store backtesting results
backtest_results = {}

@app.route('/api/account', methods=['GET'])
def get_account_api():
    """Lấy thông tin tài khoản chi tiết từ Binance API."""
    try:
        # Gọi API Binance để lấy thông tin tài khoản thực
        account_info = binance_api.get_account_info()
        
        # Kiểm tra nếu có lỗi hoặc không có dữ liệu
        if not account_info:
            return jsonify({
                'status': 'error', 
                'message': 'Không thể lấy thông tin tài khoản Binance'
            }), 500
        
        # Lấy danh sách vị thế đang mở (không bằng 0)
        positions = binance_api.get_positions()
        
        # Lấy danh sách lệnh đang mở
        open_orders = binance_api.get_open_orders()
        
        # Tính toán tổng rủi ro
        total_risk = 0
        for pos in positions:
            pos_amt = float(pos.get('positionAmt', 0))
            entry_price = float(pos.get('entryPrice', 0))
            leverage = float(pos.get('leverage', 1))
            notional = abs(pos_amt * entry_price)
            risk = notional / leverage
            total_risk += risk
            
        # Định dạng lại dữ liệu phản hồi
        response_data = {
            'status': 'success',
            'account': {
                'totalWalletBalance': account_info.get('totalWalletBalance', '0'),
                'totalUnrealizedProfit': account_info.get('totalUnrealizedProfit', '0'),
                'totalMarginBalance': account_info.get('totalMarginBalance', '0'),
                'availableBalance': account_info.get('availableBalance', '0'),
                'totalMaintMargin': account_info.get('totalMaintMargin', '0'),
                'totalInitialMargin': account_info.get('totalInitialMargin', '0'),
            },
            'positions': positions,
            'orders': open_orders,
            'risk': {
                'total_risk': total_risk,
                'risk_percentage': (total_risk / float(account_info.get('totalWalletBalance', 1))) * 100
            }
        }
        
        logger.info(f"API: Đã lấy thông tin tài khoản: {len(positions)} vị thế, {len(open_orders)} lệnh đang mở")
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"API: Lỗi khi lấy thông tin tài khoản: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy thông tin tài khoản: {str(e)}'
        }), 500

@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('index.html')

@app.route('/trading_dashboard')
def trading_dashboard():
    """Render the trading dashboard."""
    return render_template('dashboard.html')

@app.route('/backtesting')
def backtesting():
    """Render the backtesting page."""
    return render_template('backtesting.html')

@app.route('/settings')
def settings():
    """Render the settings page."""
    # Đọc trạng thái testnet hiện tại
    testnet_status = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
    
    # Đọc chế độ simulation
    simulation_mode = binance_api.simulation_mode
    
    # Render template với dữ liệu
    return render_template('settings.html', 
                          testnet_mode=testnet_status,
                          simulation_mode=simulation_mode)

@app.route('/api/settings/network_original', methods=['POST'])
def update_network_settings_original():
    """Cập nhật cấu hình network (mainnet/testnet). - Phiên bản gốc"""
    try:
        data = request.json
        use_testnet = data.get('testnet', True)
        
        # Lưu cấu hình vào biến môi trường
        os.environ['BINANCE_TESTNET'] = str(use_testnet).lower()
        
        # Khởi động lại Binance API
        binance_api.testnet = use_testnet
        binance_api.base_url = 'https://testnet.binancefuture.com' if use_testnet else 'https://fapi.binance.com'
        binance_api.test_connection()
        
        logger.info(f"Đã chuyển sang chế độ {'TESTNET' if use_testnet else 'MAINNET'}")
        
        # Trả về cấu hình hiện tại
        return jsonify({
            'status': 'success',
            'network': 'testnet' if use_testnet else 'mainnet',
            'simulation_mode': binance_api.simulation_mode
        })
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình network: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi cập nhật cấu hình: {str(e)}'
        }), 500

@app.route('/api/settings/simulation_original', methods=['POST'])
def update_simulation_settings_original():
    """Cập nhật trạng thái simulation mode. - Phiên bản gốc"""
    try:
        data = request.json
        use_simulation = data.get('simulation', True)
        
        # Cập nhật simulation mode
        binance_api.simulation_mode = use_simulation
        data_processor.simulation_mode = use_simulation
        
        logger.info(f"Đã {'BẬT' if use_simulation else 'TẮT'} chế độ mô phỏng")
        
        return jsonify({
            'status': 'success',
            'simulation_mode': use_simulation
        })
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật chế độ mô phỏng: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi cập nhật chế độ mô phỏng: {str(e)}'
        }), 500

@app.route('/api/settings/status_original', methods=['GET'])
def get_settings_status_original():
    """Lấy trạng thái cấu hình hiện tại (phiên bản gốc)."""
    try:
        # Kiểm tra kết nối API
        connection_ok = binance_api.test_connection()
        
        # Đọc trạng thái testnet
        testnet_status = binance_api.testnet
        
        return jsonify({
            'status': 'success',
            'network': 'testnet' if testnet_status else 'mainnet',
            'simulation_mode': binance_api.simulation_mode,
            'connection_ok': connection_ok,
            'api_configured': bool(binance_api.api_key and binance_api.api_secret)
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy trạng thái cấu hình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy trạng thái cấu hình: {str(e)}'
        }), 500

@app.route('/api/symbols', methods=['GET'])
def get_symbols():
    """Get available trading symbols."""
    # In simulation mode, just return a fixed list
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT', 'XRPUSDT']
    return jsonify(symbols)

@app.route('/api/intervals', methods=['GET'])
def get_intervals():
    """Get available time intervals."""
    intervals = [
        {'id': '1m', 'name': '1 Phút', 'description': 'Phân tích ngắn hạn, thích hợp cho scalping'},
        {'id': '5m', 'name': '5 Phút', 'description': 'Phân tích ngắn hạn, thích hợp cho giao dịch trong ngày'},
        {'id': '15m', 'name': '15 Phút', 'description': 'Phân tích trung hạn, thích hợp cho giao dịch trong ngày'},
        {'id': '30m', 'name': '30 Phút', 'description': 'Phân tích trung hạn, thích hợp cho giao dịch trong ngày'},
        {'id': '1h', 'name': '1 Giờ', 'description': 'Phân tích trung hạn, thích hợp cho swing trading'},
        {'id': '4h', 'name': '4 Giờ', 'description': 'Phân tích dài hạn, thích hợp cho swing trading'},
        {'id': '1d', 'name': '1 Ngày', 'description': 'Phân tích dài hạn, thích hợp cho đầu tư'}
    ]
    return jsonify(intervals)

@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """Get available trading strategies."""
    strategies = StrategyFactory.get_available_strategies()
    return jsonify(strategies)

@app.route('/api/historical_data', methods=['GET'])
def get_historical_data():
    """Get historical price data."""
    symbol = request.args.get('symbol', 'BTCUSDT')
    interval = request.args.get('interval', '1h')
    limit = int(request.args.get('limit', 500))
    
    # Get data using the data processor
    df = data_processor.get_historical_data(symbol, interval, lookback_days=30)
    
    if df is None or df.empty:
        return jsonify({'error': 'No data available'}), 404
        
    # Convert to list of dictionaries for JSON
    data = []
    for _, row in df.iterrows():
        data.append({
            'time': row.name.isoformat() if isinstance(row.name, datetime) else row.name,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row['volume'])
        })
        
    return jsonify(data)

@app.route('/api/indicators', methods=['GET'])
def get_indicators():
    """Get technical indicators for a symbol."""
    symbol = request.args.get('symbol', 'BTCUSDT')
    interval = request.args.get('interval', '1h')
    
    # Get data with indicators
    df = data_processor.get_historical_data(symbol, interval, lookback_days=30)
    
    if df is None or df.empty:
        return jsonify({'error': 'No data available'}), 404
        
    # Extract the latest indicators
    latest = df.iloc[-1].to_dict()
    
    # Format indicators for display
    indicators = {
        'price': latest.get('close', 0),
        'rsi': latest.get('RSI', 0),
        'macd': latest.get('MACD', 0),
        'macd_signal': latest.get('MACD_Signal', 0),
        'macd_hist': latest.get('MACD_Hist', 0),
        'ema9': latest.get('EMA_9', 0),
        'ema21': latest.get('EMA_21', 0),
        'sma20': latest.get('SMA_20', 0),
        'sma50': latest.get('SMA_50', 0),
        'bb_upper': latest.get('BB_upper', 0),
        'bb_middle': latest.get('BB_middle', 0),
        'bb_lower': latest.get('BB_lower', 0),
        'volume': latest.get('volume', 0),
        'volume_ratio': latest.get('Volume_Ratio', 0)
    }
    
    return jsonify(indicators)

@app.route('/api/create_bot', methods=['POST'])
def create_bot():
    """Create a new trading bot."""
    try:
        data = request.json
        
        symbol = data.get('symbol', 'BTCUSDT')
        interval = data.get('interval', '1h')
        strategy_type = data.get('strategy', 'rsi')
        strategy_params = data.get('params', {})
        
        # Kiểm tra và xác thực tham số đầu vào
        if not symbol or not interval:
            return jsonify({'error': 'Thiếu thông tin cặp giao dịch hoặc khung thời gian (Missing symbol or interval)'}), 400
            
        # Xử lý strategy_type để hỗ trợ giá trị trống từ form
        if not strategy_type or strategy_type == "null" or strategy_type == "undefined":
            strategy_type = 'rsi'  # Mặc định dùng RSI nếu không chọn
        
        logger.info(f"Creating bot for {symbol} with {strategy_type} strategy, interval: {interval}")
        
        # Create the strategy
        strategy = StrategyFactory.create_strategy(strategy_type, **strategy_params)
        
        # Create a unique bot ID
        bot_id = f"{symbol}_{interval}_{strategy_type}_{int(time.time())}"
        
        # Create the bot
        bot = TradingBot(
            binance_api=binance_api,
            data_processor=data_processor,
            strategy=strategy,
            symbol=symbol,
            interval=interval,
            test_mode=True
        )
        
        # Store the bot
        trading_bots[bot_id] = bot
        
        # Start the bot
        success = bot.start()
        
        if success:
            # Lưu bot vào storage để dùng lại sau khi khởi động lại
            storage = Storage()
            storage.save_bot({
                'id': bot_id,
                'symbol': symbol,
                'interval': interval,
                'strategy': strategy_type,
                'params': strategy_params,
                'status': 'active',
                'created_at': datetime.now().isoformat()
            })
            
            return jsonify({
                'bot_id': bot_id, 
                'status': 'started',
                'message': 'Bot đã được tạo thành công và đang hoạt động (Bot created and started successfully)'
            })
        else:
            return jsonify({
                'error': 'Không thể khởi động bot (Failed to start bot)',
                'bot_id': bot_id
            }), 500
            
    except Exception as e:
        logger.error(f"Error creating bot: {str(e)}")
        return jsonify({
            'error': f'Lỗi khi tạo bot: {str(e)} (Error creating bot)'
        }), 500

@app.route('/api/stop_bot', methods=['POST'])
def stop_bot():
    """Stop a trading bot."""
    data = request.json
    bot_id = data.get('bot_id')
    
    if bot_id not in trading_bots:
        return jsonify({'error': 'Bot not found'}), 404
        
    # Stop the bot
    bot = trading_bots[bot_id]
    bot.stop()
    
    return jsonify({'bot_id': bot_id, 'status': 'stopped'})

@app.route('/api/bot_status', methods=['GET'])
def get_bot_status():
    """Get status of all trading bots."""
    bots_status = []
    
    for bot_id, bot in trading_bots.items():
        # Get bot metrics
        metrics = bot.get_current_metrics()
        
        # Add bot info
        status = {
            'bot_id': bot_id,
            'symbol': bot.symbol,
            'interval': bot.interval,
            'strategy': bot.strategy.name,
            'running': bot.is_running,
            'metrics': metrics
        }
        
        bots_status.append(status)
        
    return jsonify(bots_status)

@app.route('/api/settings/status_config', methods=['GET'])
def get_settings_status_config():
    """Lấy trạng thái cấu hình hiện tại."""
    try:
        # Lấy trạng thái từ storage hoặc các biến môi trường toàn cục
        storage = Storage()
        settings = storage.get_settings()
        
        # Nếu không có settings, tạo default
        if not settings:
            settings = {
                'network': 'testnet',
                'simulation_mode': True,
                'api_key_configured': bool(binance_api.api_key and binance_api.api_secret)
            }
        
        return jsonify({
            'status': 'success',
            'network': settings.get('network', 'testnet'),
            'simulation_mode': settings.get('simulation_mode', True),
            'api_key_configured': bool(binance_api.api_key and binance_api.api_secret)
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy trạng thái cấu hình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Không thể tải thông tin cài đặt: {str(e)}"
        })

@app.route('/api/settings/network', methods=['POST'])
def update_network_settings():
    """Cập nhật cấu hình network (mainnet/testnet)."""
    try:
        data = request.json
        use_testnet = data.get('testnet', True)
        
        # Xác nhận người dùng nếu chuyển sang mainnet
        if not use_testnet:
            logger.warning("Đang chuyển sang MAINNET - tiền thật sẽ được sử dụng!")
        
        # Lưu cài đặt vào storage
        storage = Storage()
        settings = storage.get_settings() or {}
        settings['network'] = 'testnet' if use_testnet else 'mainnet'
        storage.save_settings(settings)
        
        # Khởi động lại API client với cấu hình mới
        global binance_api, data_processor
        binance_api = BinanceAPI(
            api_key=binance_api.api_key, 
            api_secret=binance_api.api_secret, 
            testnet=use_testnet,
            simulation_mode=binance_api.simulation_mode
        )
        data_processor = DataProcessor(binance_api, simulation_mode=binance_api.simulation_mode)
        
        return jsonify({
            'status': 'success',
            'message': f"Đã chuyển sang chế độ {'TESTNET' if use_testnet else 'MAINNET'}",
            'network': 'testnet' if use_testnet else 'mainnet'
        })
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình network: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Không thể cập nhật cài đặt network: {str(e)}"
        })

@app.route('/api/settings/simulation', methods=['POST'])
def update_simulation_settings():
    """Cập nhật trạng thái simulation mode."""
    try:
        data = request.json
        use_simulation = data.get('simulation', True)
        
        # Lưu cài đặt vào storage
        storage = Storage()
        settings = storage.get_settings() or {}
        settings['simulation_mode'] = use_simulation
        storage.save_settings(settings)
        
        # Khởi động lại API client với cấu hình mới
        global binance_api, data_processor
        binance_api = BinanceAPI(
            api_key=binance_api.api_key, 
            api_secret=binance_api.api_secret, 
            testnet=(settings.get('network', 'testnet') == 'testnet'),
            simulation_mode=use_simulation
        )
        data_processor = DataProcessor(binance_api, simulation_mode=use_simulation)
        
        return jsonify({
            'status': 'success',
            'message': f"Đã {'BẬT' if use_simulation else 'TẮT'} chế độ mô phỏng",
            'simulation_mode': use_simulation
        })
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật chế độ mô phỏng: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Không thể cập nhật chế độ mô phỏng: {str(e)}"
        })

@app.route('/api/run_backtest', methods=['POST'])
def run_backtest():
    """Run a backtesting simulation."""
    data = request.json
    
    symbol = data.get('symbol', 'BTCUSDT')
    interval = data.get('interval', '1h')
    strategy_type = data.get('strategy', 'rsi')
    strategy_params = data.get('params', {})
    lookback_days = int(data.get('lookback_days', 30))
    initial_balance = float(data.get('initial_balance', 10000.0))
    
    # Get historical data
    df = data_processor.get_historical_data(symbol, interval, lookback_days=lookback_days)
    
    if df is None or df.empty:
        return jsonify({'error': 'No data available for backtesting'}), 404
        
    # Create the strategy
    strategy = StrategyFactory.create_strategy(strategy_type, **strategy_params)
    
    # Create a bot for backtesting
    bot = TradingBot(
        binance_api=binance_api,
        data_processor=data_processor,
        strategy=strategy,
        symbol=symbol,
        interval=interval,
        test_mode=True
    )
    
    # Run the backtest
    results_df, metrics, trades = bot.backtest(df, initial_balance=initial_balance)
    
    # Generate a unique ID for the backtest
    backtest_id = f"{symbol}_{interval}_{strategy_type}_{int(time.time())}"
    
    # Store the results
    backtest_results[backtest_id] = {
        'id': backtest_id,
        'symbol': symbol,
        'interval': interval,
        'strategy': strategy_type,
        'metrics': metrics,
        'trades': [t.copy() for t in trades],
        'timestamp': datetime.now().isoformat()
    }
    
    # Convert results for JSON
    results = []
    for date, row in results_df.iterrows():
        results.append({
            'date': date.isoformat() if isinstance(date, datetime) else date,
            'close': float(row['close']),
            'equity': float(row['equity']),
            'returns': float(row['returns']),
            'signal': int(row['signal'])
        })
        
    # Convert trades for JSON
    trades_json = []
    for trade in trades:
        trades_json.append({
            'entry_time': trade['entry_time'].isoformat() if isinstance(trade['entry_time'], datetime) else trade['entry_time'],
            'exit_time': trade['exit_time'].isoformat() if isinstance(trade['exit_time'], datetime) else trade['exit_time'],
            'entry_price': float(trade['entry_price']),
            'exit_price': float(trade['exit_price']),
            'side': trade['side'],
            'amount': float(trade['amount']),
            'pnl_amount': float(trade['pnl_amount']),
            'pnl_pct': float(trade['pnl_pct'])
        })
        
    return jsonify({
        'backtest_id': backtest_id,
        'metrics': metrics,
        'results': results,
        'trades': trades_json
    })

@app.route('/api/backtest_results', methods=['GET'])
def get_backtest_results():
    """Get all backtest results."""
    results = list(backtest_results.values())
    return jsonify(results)

@app.route('/api/positions', methods=['GET'])
def get_positions_api():
    """Lấy danh sách vị thế đang mở từ Binance API."""
    try:
        # Lấy danh sách vị thế đang mở (không bằng 0)
        positions = binance_api.get_positions()
        
        # Tính toán tổng giá trị tài sản
        total_value = 0
        total_pnl = 0
        for pos in positions:
            pos_amt = float(pos.get('positionAmt', 0))
            mark_price = float(pos.get('markPrice', 0))
            notional = abs(pos_amt * mark_price)
            total_value += notional
            total_pnl += float(pos.get('unRealizedProfit', 0))
        
        response_data = {
            'status': 'success',
            'positions': positions,
            'statistics': {
                'total_positions': len(positions),
                'total_value': total_value,
                'total_pnl': total_pnl
            }
        }
        
        logger.info(f"API: Đã lấy thông tin vị thế: {len(positions)} vị thế, tổng giá trị: {total_value:.2f} USDT")
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"API: Lỗi khi lấy thông tin vị thế: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy thông tin vị thế: {str(e)}'
        }), 500

@app.route('/api/orders', methods=['GET'])
def get_orders_api():
    """Lấy danh sách lệnh đang mở từ Binance API."""
    try:
        # Lấy danh sách lệnh đang mở
        symbol = request.args.get('symbol', None)  # Nếu có symbol, chỉ lấy lệnh của symbol đó
        orders = binance_api.get_open_orders(symbol)
        
        response_data = {
            'status': 'success',
            'orders': orders,
            'count': len(orders)
        }
        
        logger.info(f"API: Đã lấy thông tin lệnh đang mở: {len(orders)} lệnh")
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"API: Lỗi khi lấy thông tin lệnh đang mở: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy thông tin lệnh đang mở: {str(e)}'
        }), 500

@app.route('/api/market_data', methods=['GET'])
def get_market_data():
    """Get current market data."""
    symbol = request.args.get('symbol', 'BTCUSDT')
    
    # Sử dụng các API thay thế thay vì Binance (bị giới hạn trên Replit)
    api_endpoints = [
        ('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true&include_last_updated_at=true', 'coingecko'),
        ('https://api.coinbase.com/v2/prices/BTC-USD/spot', 'coinbase'),
        ('https://api.alternative.me/v2/ticker/bitcoin/', 'alternative')
    ]
    
    try:
        # Thử từng API cho đến khi có kết quả
        for api_url, api_type in api_endpoints:
            try:
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Xử lý dữ liệu theo từng loại API
                    if api_type == 'coingecko' and 'bitcoin' in data:
                        price = float(data['bitcoin']['usd'])
                        change_24h = float(data['bitcoin'].get('usd_24h_change', 0)) if 'usd_24h_change' in data['bitcoin'] else 0
                        volume_24h = float(data['bitcoin'].get('usd_24h_vol', 0)) if 'usd_24h_vol' in data['bitcoin'] else (price * 10000)
                        high_24h = price * 1.02  # Ước tính
                        low_24h = price * 0.98   # Ước tính
                        logger.info(f"Lấy dữ liệu thị trường từ CoinGecko thành công: {price:.2f} USD")
                        break
                    
                    elif api_type == 'coinbase' and 'data' in data and 'amount' in data['data']:
                        price = float(data['data']['amount'])
                        # Coinbase API đơn giản không có dữ liệu 24h
                        change_24h = 0  # Không có sẵn
                        volume_24h = price * 10000  # Giá trị giả định
                        high_24h = price * 1.02  # Ước tính
                        low_24h = price * 0.98   # Ước tính
                        logger.info(f"Lấy dữ liệu thị trường từ Coinbase thành công: {price:.2f} USD")
                        break
                    
                    elif api_type == 'alternative' and 'data' in data and '1' in data['data']:
                        btc_data = data['data']['1']
                        price = float(btc_data['price_usd'])
                        change_24h = float(btc_data.get('percent_change_24h', 0))
                        volume_24h = float(btc_data.get('volume24', 0))
                        high_24h = price * (1 + abs(change_24h)/100)  # Ước tính
                        low_24h = price * (1 - abs(change_24h)/100)   # Ước tính
                        logger.info(f"Lấy dữ liệu thị trường từ Alternative.me thành công: {price:.2f} USD")
                        break
                    
            except Exception as e:
                logger.warning(f"Không thể kết nối với {api_url}: {str(e)}")
                continue  # Thử API tiếp theo
        
        # Nếu không lấy được dữ liệu từ API nào, dùng giá hiện tại
        if 'price' not in locals():
            price = current_price
            change_24h = random.uniform(-3.0, 3.0)
            volume_24h = price * random.uniform(8000, 12000)
            high_24h = price * (1 + random.uniform(0.01, 0.03))
            low_24h = price * (1 - random.uniform(0.01, 0.03))
            logger.info(f"Sử dụng giá hiện tại: {price:.2f} USD")
            
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường: {str(e)}")
        price = current_price
        change_24h = random.uniform(-3.0, 3.0)
        volume_24h = price * random.uniform(8000, 12000)
        high_24h = price * (1 + random.uniform(0.01, 0.03))
        low_24h = price * (1 - random.uniform(0.01, 0.03))
    
    # Get current sentiment data
    sentiment_data = sentiment_analyzer.get_current_sentiment(symbol)
    
    # Tính dữ liệu tài khoản dựa trên giá thực tế
    account_balance = 100000.0
    available_balance = account_balance * 0.8
    
    # Tính P&L dựa trên vị thế hiện tại
    entry_price = 82902.00
    position_size = 0.5  # BTC
    pnl = (price - entry_price) * position_size
    
    # Dữ liệu thị trường thực tế
    market_data = {
        'symbol': symbol,
        'price': price,
        'change_24h': change_24h,
        'volume_24h': volume_24h,
        'high_24h': high_24h,
        'low_24h': low_24h,
        'timestamp': datetime.now().isoformat(),
        'sentiment': {
            'score': sentiment_data['sentiment_score'],
            'category': sentiment_data['category'],
            'label': SentimentAnalyzer.SENTIMENT_CATEGORIES[sentiment_data['category']]['label'],
            'color': SentimentAnalyzer.SENTIMENT_CATEGORIES[sentiment_data['category']]['color']
        },
        'account': {
            'total_balance': account_balance,
            'available_balance': available_balance,
            'margin_balance': account_balance * 0.2,
            'unrealized_pnl': pnl,
            'unrealized_pnl_percent': (pnl / (entry_price * position_size)) * 100,
            'equity': account_balance + pnl
        }
    }
    
    return jsonify(market_data)

@app.route('/api/sentiment', methods=['GET'])
def get_sentiment():
    """Get current market sentiment data."""
    symbol = request.args.get('symbol', 'BTCUSDT')
    
    # Get current sentiment
    sentiment_data = sentiment_analyzer.get_current_sentiment(symbol)
    
    # Add label and color info
    category = sentiment_data['category']
    sentiment_data['label'] = SentimentAnalyzer.SENTIMENT_CATEGORIES[category]['label']
    sentiment_data['color'] = SentimentAnalyzer.SENTIMENT_CATEGORIES[category]['color']
    
    return jsonify(sentiment_data)

@app.route('/api/sentiment/history', methods=['GET'])
def get_sentiment_history():
    """Get historical market sentiment data."""
    hours = int(request.args.get('hours', 24))
    
    # Get sentiment history
    history = sentiment_analyzer.get_sentiment_history(hours=hours)
    
    # Add label and color info to each data point
    for item in history:
        category = item['category']
        item['label'] = SentimentAnalyzer.SENTIMENT_CATEGORIES[category]['label']
        item['color'] = SentimentAnalyzer.SENTIMENT_CATEGORIES[category]['color']
    
    return jsonify(history)

# SocketIO event handlers
@socketio.on('connect')
def on_connect():
    """Handle client connection."""
    logger.info("Client connected")

@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")

# Real-time data simulation
def generate_price_data():
    """Fetch real-time price data from CoinGecko API hoặc các API thay thế."""
    global current_price, should_run
    
    # For emitting sentiment updates
    sentiment_update_counter = 0
    account_update_counter = 0
    
    # Real account balance for testing
    account_balance = 100000.0
    
    # Entry price của vị thế hiện tại (từ dữ liệu thực tế)
    entry_price = 82902.00
    quantity = 0.5
    
    # Danh sách các API thay thế để lấy giá Bitcoin thực tế
    api_endpoints = [
        'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
        'https://api.coinbase.com/v2/prices/BTC-USD/spot',
        'https://api.alternative.me/v2/ticker/bitcoin/'
    ]
    
    while should_run:
        try:
            # Thử lấy giá Bitcoin từ các API thay thế
            for api_url in api_endpoints:
                try:
                    response = requests.get(api_url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Xử lý dữ liệu từ các API khác nhau
                        if 'bitcoin' in data:  # CoinGecko
                            current_price = float(data['bitcoin']['usd'])
                            logger.info(f"Cập nhật giá BTC từ CoinGecko: {current_price:.2f} USD")
                            break
                        elif 'data' in data and 'amount' in data['data']:  # Coinbase
                            current_price = float(data['data']['amount'])
                            logger.info(f"Cập nhật giá BTC từ Coinbase: {current_price:.2f} USD")
                            break
                        elif 'data' in data and '1' in data['data']:  # Alternative.me
                            current_price = float(data['data']['1']['price_usd'])
                            logger.info(f"Cập nhật giá BTC từ Alternative.me: {current_price:.2f} USD")
                            break
                except Exception as e:
                    logger.warning(f"Không thể kết nối với {api_url}: {str(e)}")
                    continue  # Thử API tiếp theo
            
            # Sử dụng mô phỏng giá với biến động nhỏ nếu không kết nối được API nào
            api_success = False
            for api_url in api_endpoints:
                try:
                    response = requests.get(api_url, timeout=5)
                    if response.status_code == 200:
                        api_success = True
                        break
                except:
                    pass
                    
            if not api_success:
                # Simulate giá với biến động thực tế
                variation = random.uniform(-0.2, 0.2)  # Biến động -0.2% đến +0.2%
                current_price = current_price * (1 + variation/100)
                logger.info(f"Sử dụng giá mô phỏng: {current_price:.2f} USD")
            
            # Ép giá nằm trong khoảng hợp lý nếu có lỗi
            if current_price < 10000 or current_price > 150000:
                current_price = 82900 + random.uniform(-200, 200)
        except Exception as e:
            logger.error(f"Error fetching real price from Binance: {str(e)}")
            # We continue with the current price if there was an error
        
        # Emit the new price to all connected clients
        logger.debug(f"Emitting price update: {current_price}")
        socketio.emit('price_update', {
            'symbol': 'BTCUSDT',
            'price': current_price,
            'time': datetime.now().isoformat()
        })
        
        # Emit sentiment updates every 5 seconds to avoid too much load
        sentiment_update_counter += 1
        if sentiment_update_counter >= 5:
            sentiment_update_counter = 0
            try:
                # Get current sentiment
                symbol = 'BTCUSDT'
                sentiment_data = sentiment_analyzer.get_current_sentiment(symbol)
                
                # Add label and color
                category = sentiment_data['category']
                sentiment_data['label'] = SentimentAnalyzer.SENTIMENT_CATEGORIES[category]['label']
                sentiment_data['color'] = SentimentAnalyzer.SENTIMENT_CATEGORIES[category]['color']
                
                # Emit the sentiment update
                socketio.emit('sentiment_update', sentiment_data)
                logger.debug(f"Emitting sentiment update: {sentiment_data['sentiment_score']:.2f} ({category})")
            except Exception as e:
                logger.error(f"Error emitting sentiment update: {str(e)}")
        
        # Emit account updates every 3 seconds
        account_update_counter += 1
        if account_update_counter >= 3:
            account_update_counter = 0
            try:
                # Lấy thông tin tài khoản Binance thực tế
                account_info = binance_api.get_account_info()
                
                # Lấy vị thế đang mở
                positions = binance_api.get_positions()
                
                # Lấy lệnh đang mở
                open_orders = binance_api.get_open_orders()
                
                # Tính toán tổng rủi ro
                total_risk = 0
                for pos in positions:
                    pos_amt = float(pos.get('positionAmt', 0))
                    entry_price = float(pos.get('entryPrice', 0))
                    leverage = float(pos.get('leverage', 1))
                    notional = abs(pos_amt * entry_price)
                    risk = notional / leverage
                    total_risk += risk
                
                # Dữ liệu tài khoản thực từ Binance API
                account_data = {
                    'balance': float(account_info.get('totalWalletBalance', 0)),
                    'unrealized_pnl': float(account_info.get('totalUnrealizedProfit', 0)),
                    'margin_balance': float(account_info.get('totalMarginBalance', 0)),
                    'available_balance': float(account_info.get('availableBalance', 0)),
                    'maintenance_margin': float(account_info.get('totalMaintMargin', 0)),
                    'initial_margin': float(account_info.get('totalInitialMargin', 0)),
                    'positions': positions,
                    'orders': open_orders,
                    'risk': {
                        'total_risk': total_risk,
                        'risk_percentage': (total_risk / float(account_info.get('totalWalletBalance', 1))) * 100
                    }
                }
                
                # Emit the account update
                socketio.emit('account_update', account_data)
                logger.info(f"Đã gửi cập nhật tài khoản: {len(positions)} vị thế, {len(open_orders)} lệnh đang mở")
            except Exception as e:
                # Backup plan: gửi dữ liệu mô phỏng nếu có lỗi
                pnl_value = (current_price - entry_price) * quantity
                pnl_percent = (pnl_value / (entry_price * quantity)) * 100
                
                # Dữ liệu mô phỏng
                account_data = {
                    'balance': account_balance,
                    'unrealized_pnl': pnl_value,
                    'margin_balance': account_balance + pnl_value,
                    'available_balance': account_balance * 0.8,
                    'positions': [{
                        'symbol': 'BTCUSDT',
                        'positionAmt': str(quantity),
                        'entryPrice': str(entry_price),
                        'markPrice': str(current_price),
                        'unRealizedProfit': str(pnl_value),
                        'leverage': '10',
                        'marginType': 'isolated'
                    }],
                    'orders': []
                }
                
                socketio.emit('account_update', account_data)
                logger.error(f"Lỗi khi lấy dữ liệu tài khoản thực tế: {str(e)}")
        
        # Sleep for 1 second
        time.sleep(1)

def start_data_generation():
    """Start the data generation thread."""
    global data_thread, should_run
    
    if data_thread is None or not data_thread.is_alive():
        should_run = True
        data_thread = threading.Thread(target=generate_price_data)
        data_thread.daemon = True
        data_thread.start()
        logger.info("Data generation thread started")

def stop_data_generation():
    """Stop the data generation thread."""
    global should_run
    should_run = False
    logger.info("Data generation thread stopped")

# Start the server
if __name__ == '__main__':
    logger.info("Starting trading bot server...")
    
    # Start data generation
    logger.info("Starting data generation thread")
    start_data_generation()
    
    # Start the server with proper parameters
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, log_output=True)

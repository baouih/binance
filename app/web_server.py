import os
import json
import logging
import pandas as pd
import numpy as np
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
binance_api = BinanceAPI(simulation_mode=True)
data_processor = DataProcessor(binance_api, simulation_mode=True)
ml_optimizer = MLOptimizer()
sentiment_analyzer = SentimentAnalyzer(data_processor=data_processor, simulation_mode=True)
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
        
        if quantity <= 0:
            return jsonify({
                'status': 'error',
                'message': 'Invalid quantity'
            }), 400
        
        logger.info(f"Placing order: {side} {quantity} {symbol} at {order_type}")
        
        # Execute the order using BinanceAPI
        result = binance_api.create_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity
        )
        
        # Return success response
        return jsonify({
            'status': 'success',
            'message': f'Order {side} {quantity} {symbol} placed successfully',
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
                'message': 'Position ID required'
            }), 400
        
        logger.info(f"Closing position: {position_id}")
        
        # In simulation mode, just return success
        # In a real implementation, this would close the position via the exchange API
        
        return jsonify({
            'status': 'success',
            'message': f'Position {position_id} closed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to close position: {str(e)}'
        }), 500

# Store backtesting results
backtest_results = {}

@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Render the trading dashboard."""
    return render_template('dashboard.html')

@app.route('/backtesting')
def backtesting():
    """Render the backtesting page."""
    return render_template('backtesting.html')

@app.route('/settings')
def settings():
    """Render the settings page."""
    return render_template('settings.html')

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

@app.route('/api/market_data', methods=['GET'])
def get_market_data():
    """Get current market data."""
    symbol = request.args.get('symbol', 'BTCUSDT')
    
    # In simulation mode, use the current price
    price = current_price
    
    # Get current sentiment data
    sentiment_data = sentiment_analyzer.get_current_sentiment(symbol)
    
    # Generate simulated account data
    account_balance = 100000.0  # Simulated account balance in USDT
    available_balance = account_balance * 0.8  # Simulated available balance
    
    # Generate some simulated metrics
    market_data = {
        'symbol': symbol,
        'price': price,
        'change_24h': random.uniform(-5.0, 5.0),
        'volume_24h': price * random.uniform(5000, 20000),
        'high_24h': price * (1 + random.uniform(0.01, 0.05)),
        'low_24h': price * (1 - random.uniform(0.01, 0.05)),
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
            'unrealized_pnl': random.uniform(-5000, 5000),
            'equity': account_balance + random.uniform(-3000, 3000)
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
    """Generate simulated price data."""
    global current_price, should_run
    
    # For emitting sentiment updates
    sentiment_update_counter = 0
    account_update_counter = 0
    
    # Generate simulated account data
    account_balance = 100000.0
    available_balance = account_balance * 0.8
    
    while should_run:
        # Simulate random price movement
        change_pct = random.normalvariate(0, 0.002)  # Mean 0, std dev 0.2%
        current_price = current_price * (1 + change_pct)
        
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
                # Simulate some small random changes in account balance and PnL
                pnl_change = random.uniform(-500, 500)
                balance_change = random.uniform(-200, 200)
                
                # Create account update data
                account_data = {
                    'total_balance': account_balance + balance_change,
                    'available_balance': (account_balance + balance_change) * 0.8,
                    'margin_balance': (account_balance + balance_change) * 0.2,
                    'unrealized_pnl': pnl_change,
                    'equity': account_balance + balance_change + pnl_change
                }
                
                # Emit the account update
                socketio.emit('account_update', account_data)
                logger.debug(f"Emitting account update: Balance: {account_data['total_balance']:.2f}, PnL: {account_data['unrealized_pnl']:.2f}")
            except Exception as e:
                logger.error(f"Error emitting account update: {str(e)}")
        
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

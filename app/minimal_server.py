import logging
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import random
import time
from datetime import datetime, timedelta
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_bot_secret_key")

# Configure templates directory
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app.template_folder = template_dir

# Global variables for simulated data
current_price = 50000.0
price_history = []
trading_active = False
simulation_thread = None

# Simulated trading data
account_balance = 10000.0
positions = []
trade_history = []
performance_metrics = {
    'win_rate': 0.0,
    'profit_factor': 0.0,
    'total_trades': 0,
    'winning_trades': 0,
    'losing_trades': 0,
    'total_profit': 0.0,
    'max_drawdown': 0.0
}

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

@app.route('/api/price')
def get_price():
    """Get the current simulated price."""
    return jsonify({
        'price': current_price,
        'timestamp': datetime.now().isoformat(),
        'symbol': 'BTCUSDT'
    })

@app.route('/api/price_history')
def get_price_history():
    """Get historical price data."""
    return jsonify(price_history)

@app.route('/api/account')
def get_account():
    """Get account information."""
    return jsonify({
        'balance': account_balance,
        'positions': positions,
        'trade_history': trade_history,
        'performance_metrics': performance_metrics
    })

@app.route('/api/start_trading', methods=['POST'])
def start_trading():
    """Start automated trading."""
    global trading_active
    data = request.json or {}
    strategy = data.get('strategy', 'rsi')
    symbol = data.get('symbol', 'BTCUSDT')
    
    if not trading_active:
        trading_active = True
        return jsonify({'status': 'success', 'message': f'Trading started with {strategy} strategy on {symbol}'})
    else:
        return jsonify({'status': 'error', 'message': 'Trading already active'})

@app.route('/api/stop_trading', methods=['POST'])
def stop_trading():
    """Stop automated trading."""
    global trading_active
    if trading_active:
        trading_active = False
        return jsonify({'status': 'success', 'message': 'Trading stopped'})
    else:
        return jsonify({'status': 'error', 'message': 'Trading not active'})

@app.route('/api/place_order', methods=['POST'])
def place_order():
    """Manually place a trade order."""
    global account_balance, positions
    data = request.json
    
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
    order_type = data.get('type', 'market')
    side = data.get('side', 'buy')
    symbol = data.get('symbol', 'BTCUSDT')
    quantity = float(data.get('quantity', 0.0))
    price = float(data.get('price', current_price))
    
    # Validate the order
    if quantity <= 0:
        return jsonify({'status': 'error', 'message': 'Invalid quantity'}), 400
        
    # Calculate order cost
    cost = quantity * price
    
    # Check if enough balance
    if side.lower() == 'buy' and cost > account_balance:
        return jsonify({'status': 'error', 'message': 'Insufficient balance'}), 400
        
    # Process the order
    order_id = int(time.time() * 1000)
    
    if side.lower() == 'buy':
        # Subtract from balance
        account_balance -= cost
        
        # Add position
        positions.append({
            'id': order_id,
            'symbol': symbol,
            'side': 'LONG',
            'quantity': quantity,
            'entry_price': price,
            'current_price': price,
            'pnl': 0.0,
            'pnl_percent': 0.0,
            'timestamp': datetime.now().isoformat()
        })
    else:  # SELL
        # Find a matching position to close
        for i, pos in enumerate(positions):
            if pos['symbol'] == symbol and pos['side'] == 'LONG':
                # Close the position
                pnl = (price - pos['entry_price']) * pos['quantity']
                pnl_percent = (price - pos['entry_price']) / pos['entry_price'] * 100
                
                # Add to trade history
                trade_history.append({
                    'id': order_id,
                    'symbol': symbol,
                    'side': 'SELL',
                    'quantity': pos['quantity'],
                    'entry_price': pos['entry_price'],
                    'exit_price': price,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Update balance
                account_balance += cost + pnl
                
                # Update metrics
                update_performance_metrics(pnl > 0, pnl, pnl_percent)
                
                # Remove the position
                positions.pop(i)
                break
        else:
            # If no matching position, create a new SHORT position
            positions.append({
                'id': order_id,
                'symbol': symbol,
                'side': 'SHORT',
                'quantity': quantity,
                'entry_price': price,
                'current_price': price,
                'pnl': 0.0,
                'pnl_percent': 0.0,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update balance
            account_balance -= cost
    
    return jsonify({
        'status': 'success',
        'order_id': order_id,
        'message': f'{side.upper()} order executed at {price}',
        'account_balance': account_balance
    })

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """Run a backtest simulation."""
    data = request.json
    
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
    strategy = data.get('strategy', 'rsi')
    symbol = data.get('symbol', 'BTCUSDT')
    timeframe = data.get('timeframe', '1h')
    start_date = data.get('start_date', (datetime.now() - timedelta(days=30)).isoformat())
    end_date = data.get('end_date', datetime.now().isoformat())
    initial_capital = float(data.get('initial_capital', 10000.0))
    
    # Simulate backtest results
    trades = generate_mock_trades(20, initial_capital)
    metrics = calculate_performance_metrics(trades, initial_capital)
    
    # Generate equity curve
    equity_curve = generate_mock_equity_curve(trades, initial_capital)
    
    return jsonify({
        'status': 'success',
        'trades': trades,
        'performance_metrics': metrics,
        'equity_curve': equity_curve
    })

@app.route('/api/strategies')
def get_strategies():
    """Get available trading strategies."""
    return jsonify([
        {'id': 'rsi', 'name': 'RSI Strategy', 'description': 'Relative Strength Index strategy'},
        {'id': 'macd', 'name': 'MACD Strategy', 'description': 'Moving Average Convergence Divergence strategy'},
        {'id': 'ema_cross', 'name': 'EMA Cross Strategy', 'description': 'Exponential Moving Average crossover strategy'},
        {'id': 'bbands', 'name': 'Bollinger Bands Strategy', 'description': 'Bollinger Bands mean reversion strategy'},
        {'id': 'ml', 'name': 'Machine Learning Strategy', 'description': 'ML-based prediction strategy'}
    ])

@app.route('/api/symbols')
def get_symbols():
    """Get available trading symbols."""
    return jsonify([
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT', 'XRPUSDT',
        'SOLUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT'
    ])

@app.route('/api/timeframes')
def get_timeframes():
    """Get available timeframes."""
    return jsonify([
        '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'
    ])

def update_performance_metrics(is_win, pnl, pnl_percent):
    """Update performance metrics with a new trade."""
    global performance_metrics
    
    performance_metrics['total_trades'] += 1
    performance_metrics['total_profit'] += pnl
    
    if is_win:
        performance_metrics['winning_trades'] += 1
    else:
        performance_metrics['losing_trades'] += 1
        
    if performance_metrics['total_trades'] > 0:
        performance_metrics['win_rate'] = performance_metrics['winning_trades'] / performance_metrics['total_trades']
        
    # Update other metrics
    # (Would calculate profit factor, max drawdown, etc. in a real implementation)

def generate_mock_trades(num_trades, initial_capital):
    """Generate mock trades for backtesting."""
    trades = []
    
    # Starting parameters
    capital = initial_capital
    entry_price = 50000.0
    
    for i in range(num_trades):
        # Random price change
        price_change = random.uniform(-0.05, 0.05)
        exit_price = entry_price * (1 + price_change)
        
        # Random quantity
        quantity = round(capital * 0.1 / entry_price, 8)
        
        # Calculate P&L
        pnl = (exit_price - entry_price) * quantity
        pnl_percent = price_change * 100
        
        # Create trade
        trade = {
            'id': i + 1,
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'quantity': quantity,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'entry_time': (datetime.now() - timedelta(days=num_trades - i, hours=random.randint(0, 23))).isoformat(),
            'exit_time': (datetime.now() - timedelta(days=num_trades - i - 1, hours=random.randint(0, 23))).isoformat(),
            'pnl': pnl,
            'pnl_percent': pnl_percent
        }
        
        trades.append(trade)
        
        # Update capital and entry price for next trade
        capital += pnl
        entry_price = exit_price
        
    return trades

def calculate_performance_metrics(trades, initial_capital):
    """Calculate performance metrics from trades."""
    if not trades:
        return {
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_profit_percent': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        }
        
    # Calculate basic metrics
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t['pnl'] > 0)
    losing_trades = sum(1 for t in trades if t['pnl'] <= 0)
    
    total_profit = sum(t['pnl'] for t in trades)
    total_profit_percent = total_profit / initial_capital * 100
    
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    # Calculate avg win/loss
    wins = [t['pnl'] for t in trades if t['pnl'] > 0]
    losses = [t['pnl'] for t in trades if t['pnl'] <= 0]
    
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    
    # Calculate profit factor
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] <= 0))
    
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Simulate other metrics
    max_drawdown = random.uniform(5, 20)
    sharpe_ratio = random.uniform(0.5, 2.5)
    
    return {
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'total_profit': total_profit,
        'total_profit_percent': total_profit_percent,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'avg_win': avg_win,
        'avg_loss': avg_loss
    }

def generate_mock_equity_curve(trades, initial_capital):
    """Generate a mock equity curve from trades."""
    equity_curve = []
    
    # Start with initial capital
    capital = initial_capital
    
    # Start date (30 days ago)
    date = datetime.now() - timedelta(days=30)
    
    # Generate daily equity points
    for i in range(31):  # 30 days + today
        current_date = date + timedelta(days=i)
        
        # Random daily change
        daily_change = random.normalvariate(0.001, 0.02)  # Mean 0.1%, std dev 2%
        capital *= (1 + daily_change)
        
        equity_curve.append({
            'date': current_date.isoformat(),
            'equity': capital,
            'return': (capital / initial_capital - 1) * 100
        })
        
    return equity_curve

def update_simulated_price():
    """Update the simulated price in a separate thread."""
    global current_price, price_history
    
    while True:
        # Calculate price change (random walk with slight upward bias)
        change_pct = random.normalvariate(0.0001, 0.002)  # Mean 0.01%, std dev 0.2%
        current_price *= (1 + change_pct)
        
        # Add to price history (keeping last 1000 points)
        price_history.append({
            'timestamp': datetime.now().isoformat(),
            'price': current_price
        })
        
        if len(price_history) > 1000:
            price_history.pop(0)
            
        # Update positions
        for position in positions:
            position['current_price'] = current_price
            
            # Calculate P&L
            if position['side'] == 'LONG':
                position['pnl'] = (current_price - position['entry_price']) * position['quantity']
                position['pnl_percent'] = (current_price - position['entry_price']) / position['entry_price'] * 100
            else:  # SHORT
                position['pnl'] = (position['entry_price'] - current_price) * position['quantity']
                position['pnl_percent'] = (position['entry_price'] - current_price) / position['entry_price'] * 100
                
        # Sleep for 1 second
        time.sleep(1)

def start_simulation():
    """Start the price simulation thread."""
    global simulation_thread
    
    if simulation_thread is None or not simulation_thread.is_alive():
        simulation_thread = threading.Thread(target=update_simulated_price)
        simulation_thread.daemon = True
        simulation_thread.start()

if __name__ == '__main__':
    logger.info("Attempting to start server...")
    logger.info(f"Python version: {sys.version}")
    
    try:
        # Start the price simulation thread
        start_simulation()
        
        # Start the Flask server
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        logger.error("Detailed error traceback:")
        logger.error(str(e), exc_info=True)

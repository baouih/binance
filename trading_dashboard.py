from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import logging
import pandas as pd
from datetime import datetime
from binance_api import BinanceAPI
from adaptive_stop_loss_manager import AdaptiveStopLossManager

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_dashboard_secret")

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trading_dashboard')

# Khởi tạo API và các manager
api = BinanceAPI()
sl_manager = AdaptiveStopLossManager()

# Đường dẫn lưu trữ dữ liệu
TRADE_HISTORY_FILE = "trade_history.json"

# Hàm hỗ trợ
def load_trade_history():
    """Tải lịch sử giao dịch từ file"""
    if os.path.exists(TRADE_HISTORY_FILE):
        with open(TRADE_HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_trade_history(trades):
    """Lưu lịch sử giao dịch vào file"""
    with open(TRADE_HISTORY_FILE, 'w') as f:
        json.dump(trades, f, indent=2)

def format_number(num, decimals=2):
    """Format số với số chữ số thập phân"""
    if num is None:
        return "N/A"
    return f"{float(num):.{decimals}f}"

# Các route
@app.route('/')
def index():
    """Trang chủ - Dashboard tổng quan"""
    try:
        # Lấy dữ liệu tài khoản
        account_info = api.get_futures_account()
        balance = float(account_info.get('totalWalletBalance', 0))
        
        # Lấy danh sách vị thế hiện tại
        positions = []
        positions_info = api.get_futures_position_risk()
        
        for position in positions_info:
            amt = float(position.get('positionAmt', 0))
            if amt != 0:  # Vị thế đang mở
                unrealized_pnl = float(position.get('unrealizedProfit', 0))
                entry_price = float(position.get('entryPrice', 0))
                mark_price = float(position.get('markPrice', 0))
                
                # Tính ROE (Return on Equity)
                leverage = int(position.get('leverage', 1))
                roe = (unrealized_pnl / (abs(amt) * entry_price / leverage)) * 100 if entry_price > 0 else 0
                
                positions.append({
                    'symbol': position['symbol'],
                    'amount': format_number(amt, 4),
                    'entryPrice': format_number(entry_price, 2),
                    'markPrice': format_number(mark_price, 2),
                    'pnl': format_number(unrealized_pnl, 2),
                    'roe': format_number(roe, 2),
                    'side': 'LONG' if amt > 0 else 'SHORT',
                    'leverage': position.get('leverage', 1)
                })
        
        # Lấy market data
        market_data = []
        for symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]:
            ticker = api.futures_ticker_price(symbol)
            price = float(ticker['price'])
            
            market_data.append({
                'symbol': symbol,
                'price': format_number(price, 2)
            })
        
        # Lấy lịch sử giao dịch
        trade_history = load_trade_history()
        
        return render_template(
            'index.html',
            balance=format_number(balance),
            positions=positions,
            market_data=market_data,
            trade_history=trade_history,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Lỗi khi tải dashboard: {str(e)}")
        return render_template('error.html', error_message=str(e))

@app.route('/create_order', methods=['GET', 'POST'])
def create_order():
    """Trang tạo lệnh giao dịch mới"""
    if request.method == 'POST':
        try:
            # Lấy dữ liệu từ form
            symbol = request.form.get('symbol')
            side = request.form.get('side')
            order_type = request.form.get('type', 'MARKET')
            quantity = float(request.form.get('quantity', 0))
            leverage = int(request.form.get('leverage', 5))
            
            # Thiết lập đòn bẩy
            api.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            # Nếu là lệnh LIMIT, lấy thêm giá
            price = None
            if order_type == 'LIMIT':
                price = float(request.form.get('price', 0))
            
            # Tạo lệnh
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity
            }
            
            if price:
                order_params['price'] = price
                order_params['timeInForce'] = 'GTC'
            
            order = api.futures_create_order(**order_params)
            
            # Lưu lịch sử giao dịch
            trade_history = load_trade_history()
            trade_history.append({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'price': price if price else 'MARKET',
                'leverage': leverage,
                'order_id': order.get('orderId', 'N/A')
            })
            save_trade_history(trade_history)
            
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Lỗi khi tạo lệnh: {str(e)}")
            return render_template('error.html', error_message=str(e))
    
    # GET request - hiển thị form tạo lệnh
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT", 
               "XRPUSDT", "LINKUSDT", "AVAXUSDT", "DOTUSDT"]
    
    return render_template('create_order.html', symbols=symbols)

@app.route('/close_position/<symbol>', methods=['POST'])
def close_position(symbol):
    """Đóng vị thế cho một symbol"""
    try:
        # Lấy thông tin vị thế
        positions = api.get_futures_position_risk(symbol=symbol)
        position = next((p for p in positions if float(p.get('positionAmt', 0)) != 0), None)
        
        if position:
            # Xác định phía đóng vị thế (ngược với phía hiện tại)
            amt = float(position.get('positionAmt', 0))
            close_side = 'SELL' if amt > 0 else 'BUY'
            
            # Đặt lệnh đóng vị thế
            order = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='MARKET',
                closePosition='true'
            )
            
            # Lưu lịch sử giao dịch
            trade_history = load_trade_history()
            trade_history.append({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'symbol': symbol,
                'side': close_side,
                'type': 'MARKET',
                'quantity': abs(amt),
                'price': 'MARKET',
                'leverage': position.get('leverage', 1),
                'order_id': order.get('orderId', 'N/A'),
                'action': 'CLOSE_POSITION'
            })
            save_trade_history(trade_history)
            
            return jsonify({'success': True, 'message': f'Đã đóng vị thế {symbol}'})
        else:
            return jsonify({'success': False, 'message': f'Không tìm thấy vị thế cho {symbol}'})
    except Exception as e:
        logger.error(f"Lỗi khi đóng vị thế {symbol}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/account_balance')
def api_account_balance():
    """API endpoint để lấy số dư tài khoản"""
    try:
        account_info = api.get_futures_account()
        balance = float(account_info.get('totalWalletBalance', 0))
        total_equity = float(account_info.get('totalMarginBalance', 0))
        unrealized_pnl = float(account_info.get('totalUnrealizedProfit', 0))
        
        return jsonify({
            'success': True,
            'balance': format_number(balance),
            'equity': format_number(total_equity),
            'unrealized_pnl': format_number(unrealized_pnl),
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy số dư tài khoản: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/market_data')
def api_market_data():
    """API endpoint để lấy dữ liệu thị trường"""
    try:
        market_data = []
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
        
        for symbol in symbols:
            ticker = api.futures_ticker_price(symbol)
            price = float(ticker['price'])
            
            market_data.append({
                'symbol': symbol,
                'price': format_number(price, 2)
            })
        
        return jsonify({
            'success': True,
            'data': market_data,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/positions')
def api_positions():
    """API endpoint để lấy thông tin vị thế"""
    try:
        positions = []
        positions_info = api.get_futures_position_risk()
        
        for position in positions_info:
            amt = float(position.get('positionAmt', 0))
            if amt != 0:  # Vị thế đang mở
                unrealized_pnl = float(position.get('unrealizedProfit', 0))
                entry_price = float(position.get('entryPrice', 0))
                mark_price = float(position.get('markPrice', 0))
                
                # Tính ROE (Return on Equity)
                leverage = int(position.get('leverage', 1))
                roe = (unrealized_pnl / (abs(amt) * entry_price / leverage)) * 100 if entry_price > 0 else 0
                
                positions.append({
                    'symbol': position['symbol'],
                    'amount': format_number(amt, 4),
                    'entryPrice': format_number(entry_price, 2),
                    'markPrice': format_number(mark_price, 2),
                    'pnl': format_number(unrealized_pnl, 2),
                    'roe': format_number(roe, 2),
                    'side': 'LONG' if amt > 0 else 'SHORT',
                    'leverage': position.get('leverage', 1)
                })
        
        return jsonify({
            'success': True,
            'positions': positions,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin vị thế: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    # Tạo thư mục templates nếu chưa tồn tại
    os.makedirs('templates', exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
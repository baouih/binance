from flask import Flask, render_template, request, jsonify
import random
import os

app = Flask(__name__, template_folder='simple_templates', static_folder='simple_static')
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

# Dữ liệu mô phỏng
mock_balance = 10000.0
mock_trades = []
mock_positions = []

@app.route('/')
def home():
    """Trang chủ đơn giản"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Bảng điều khiển giao dịch đơn giản"""
    return render_template('dashboard.html')

@app.route('/settings')
def settings():
    """Trang cài đặt đơn giản"""
    return render_template('settings.html')

@app.route('/api/price')
def get_price():
    """API lấy giá mô phỏng"""
    base_price = 79500
    variance = 500
    price = base_price + random.random() * variance
    return jsonify({
        'price': price,
        'change': random.uniform(-2, 2)
    })

@app.route('/api/account')
def get_account():
    """API lấy thông tin tài khoản mô phỏng"""
    return jsonify({
        'balance': mock_balance,
        'positions': mock_positions,
        'trades': mock_trades
    })

@app.route('/api/trade', methods=['POST'])
def place_trade():
    """API đặt lệnh giao dịch mô phỏng"""
    global mock_balance, mock_trades, mock_positions
    data = request.json
    
    # Đặt lệnh mô phỏng
    trade = {
        'id': len(mock_trades) + 1,
        'symbol': data.get('symbol', 'BTCUSDT'),
        'side': data.get('side', 'BUY'),
        'quantity': data.get('quantity', 0.01),
        'price': data.get('price', 79500 + random.random() * 500),
        'timestamp': 'simulated'
    }
    
    mock_trades.append(trade)
    
    return jsonify({
        'success': True,
        'message': f"Đã đặt lệnh {trade['side']} thành công", 
        'trade': trade
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
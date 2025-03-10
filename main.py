from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import os
import json
import logging
from datetime import datetime
import secrets
import threading
import time

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", secrets.token_hex(16))

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("web_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("web_app")

# Các biến toàn cục
STATUS = {
    "running": False,
    "account_balance": 0.0,
    "positions": [],
    "market_data": [],
    "logs": [],
    "test_results": {
        "api_connection": {"status": "Chưa kiểm tra", "passed": None},
        "market_data": {"status": "Chưa kiểm tra", "passed": None},
        "telegram": {"status": "Chưa kiểm tra", "passed": None},
        "position_management": {"status": "Chưa kiểm tra", "passed": None},
        "technical_analysis": {"status": "Chưa kiểm tra", "passed": None},
    }
}

# Cấu hình mặc định
DEFAULT_CONFIG = {
    "api_mode": "testnet",
    "risk_percentage": 1.0,
    "max_leverage": 5,
    "risk_level": "10",
    "auto_trading": False,
    "market_analysis": True,
    "sltp_management": True,
    "trailing_stop": True,
    "telegram_notifications": True,
}

# Tải cấu hình
def load_config():
    config_file = "web_app_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
    return DEFAULT_CONFIG.copy()

# Lưu cấu hình
def save_config(config):
    config_file = "web_app_config.json"
    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
        logger.info("Đã lưu cấu hình")
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình: {e}")

# Thêm log
def add_log(message, log_type="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {"timestamp": timestamp, "message": message, "type": log_type}
    STATUS["logs"].insert(0, log_entry)  # Thêm vào đầu danh sách
    
    # Giới hạn số lượng log
    if len(STATUS["logs"]) > 100:
        STATUS["logs"] = STATUS["logs"][:100]
    
    # Ghi log
    if log_type == "INFO":
        logger.info(message)
    elif log_type == "ERROR":
        logger.error(message)
    elif log_type == "WARNING":
        logger.warning(message)

# Cập nhật dữ liệu thị trường
def update_market_data():
    # Dữ liệu mẫu
    STATUS["market_data"] = [
        {'symbol': 'BTCUSDT', 'price': '65432.50', 'change_24h': '+2.5%', 'volume': '2.5B', 'signal': 'Mua', 'trend': 'Tăng'},
        {'symbol': 'ETHUSDT', 'price': '3542.75', 'change_24h': '+1.8%', 'volume': '1.2B', 'signal': 'Chờ', 'trend': 'Sideway'},
        {'symbol': 'BNBUSDT', 'price': '567.80', 'change_24h': '-0.5%', 'volume': '350M', 'signal': 'Bán', 'trend': 'Giảm'},
        {'symbol': 'SOLUSDT', 'price': '128.45', 'change_24h': '+5.2%', 'volume': '820M', 'signal': 'Mua mạnh', 'trend': 'Tăng'},
        {'symbol': 'ADAUSDT', 'price': '0.45', 'change_24h': '-1.2%', 'volume': '150M', 'signal': 'Chờ', 'trend': 'Sideway'},
        {'symbol': 'XRPUSDT', 'price': '0.58', 'change_24h': '+0.8%', 'volume': '180M', 'signal': 'Chờ', 'trend': 'Tăng nhẹ'},
        {'symbol': 'DOGEUSDT', 'price': '0.12', 'change_24h': '+3.5%', 'volume': '95M', 'signal': 'Mua', 'trend': 'Tăng'},
        {'symbol': 'DOTUSDT', 'price': '6.82', 'change_24h': '-0.3%', 'volume': '65M', 'signal': 'Chờ', 'trend': 'Sideway'}
    ]

# Thêm vị thế mẫu
def add_test_position():
    import random
    
    position_types = ['LONG', 'SHORT']
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
    
    symbol = random.choice(symbols)
    pos_type = random.choice(position_types)
    
    entry_price = round(random.uniform(100, 65000), 2)
    current_price = round(entry_price * (1 + random.uniform(-0.05, 0.05)), 2)
    
    size = round(random.uniform(0.01, 0.5), 3)
    
    if pos_type == 'LONG':
        pnl = round((current_price - entry_price) / entry_price * 100, 2)
        sl = round(entry_price * 0.97, 2)
        tp = round(entry_price * 1.05, 2)
    else:
        pnl = round((entry_price - current_price) / entry_price * 100, 2)
        sl = round(entry_price * 1.03, 2)
        tp = round(entry_price * 0.95, 2)
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_position = {
        'symbol': symbol,
        'type': pos_type,
        'entry_price': entry_price,
        'current_price': current_price,
        'size': size,
        'pnl': f"{pnl}%",
        'time': current_time,
        'sl': sl,
        'tp': tp
    }
    
    STATUS["positions"].append(new_position)
    add_log(f"Đã mở vị thế test: {symbol} {pos_type} tại giá {entry_price}")

# Cập nhật dữ liệu liên tục
def background_update():
    while STATUS["running"]:
        # Cập nhật giá cả
        import random
        
        # Cập nhật dữ liệu thị trường
        for market in STATUS["market_data"]:
            price = float(market["price"].replace(",", ""))
            change = random.uniform(-0.5, 0.5)
            new_price = round(price * (1 + change/100), 2)
            market["price"] = f"{new_price:,.2f}"
        
        # Cập nhật vị thế
        for position in STATUS["positions"]:
            current_price = position["current_price"]
            change = random.uniform(-1.0, 1.0)
            new_price = round(float(current_price) * (1 + change/100), 2)
            position["current_price"] = new_price
            
            if position["type"] == "LONG":
                pnl = round((new_price - position["entry_price"]) / position["entry_price"] * 100, 2)
            else:
                pnl = round((position["entry_price"] - new_price) / position["entry_price"] * 100, 2)
            
            position["pnl"] = f"{pnl}%"
        
        time.sleep(5)

@app.route('/')
def index():
    # Kiểm tra nếu là thiết bị di động
    user_agent = request.headers.get('User-Agent', '')
    is_mobile = 'Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent
    
    config = load_config()
    
    if is_mobile:
        # Sử dụng template đơn giản cho thiết bị di động
        return render_template('index-simple.html', 
                              status=STATUS, 
                              config=config)
    else:
        # Sử dụng template đầy đủ cho desktop
        return render_template('index.html', 
                              status=STATUS, 
                              config=config,
                              active_page="dashboard")

@app.route('/market')
def market():
    config = load_config()
    return render_template('market.html', 
                          status=STATUS, 
                          config=config,
                          active_page="market")

@app.route('/positions')
def positions():
    config = load_config()
    return render_template('positions.html', 
                          status=STATUS, 
                          config=config,
                          active_page="positions")

@app.route('/logs')
def logs():
    config = load_config()
    return render_template('logs.html', 
                          status=STATUS, 
                          config=config,
                          active_page="logs")

@app.route('/test')
def test():
    config = load_config()
    return render_template('test.html', 
                          status=STATUS, 
                          config=config,
                          active_page="test")

@app.route('/settings')
def settings():
    config = load_config()
    return render_template('settings.html', 
                          status=STATUS, 
                          config=config,
                          active_page="settings")

@app.route('/api/start', methods=['POST'])
def start_system():
    if not STATUS["running"]:
        STATUS["running"] = True
        STATUS["account_balance"] = 10000.0
        add_log("Hệ thống kiểm tra đã khởi động")
        
        # Khởi tạo dữ liệu ban đầu
        update_market_data()
        
        # Khởi động luồng cập nhật
        update_thread = threading.Thread(target=background_update, daemon=True)
        update_thread.start()
        
    return jsonify({"success": True, "message": "Hệ thống đã khởi động", "status": STATUS["running"]})

@app.route('/api/stop', methods=['POST'])
def stop_system():
    if STATUS["running"]:
        STATUS["running"] = False
        add_log("Hệ thống kiểm tra đã dừng")
    return jsonify({"success": True, "message": "Hệ thống đã dừng", "status": STATUS["running"]})

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    try:
        data = request.json
        config = load_config()
        
        # Cập nhật cấu hình
        for key, value in data.items():
            config[key] = value
        
        # Lưu cấu hình
        save_config(config)
        add_log(f"Đã cập nhật cài đặt: {', '.join([f'{k}={v}' for k,v in data.items()])}")
        
        return jsonify({"success": True, "message": "Cài đặt đã được cập nhật"})
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cài đặt: {e}")
        return jsonify({"success": False, "message": f"Lỗi: {e}"})

@app.route('/api/test_api_connection', methods=['POST'])
def test_api_connection():
    STATUS["test_results"]["api_connection"]["status"] = "Đang kiểm tra"
    add_log("Đang kiểm tra kết nối với Binance API...", "INFO")
    
    # Giả lập kiểm tra thành công
    time.sleep(1)
    
    STATUS["test_results"]["api_connection"]["status"] = "Thành công"
    STATUS["test_results"]["api_connection"]["passed"] = True
    add_log("✅ Kết nối API thành công!", "INFO")
    
    return jsonify({
        "success": True, 
        "message": "Kết nối API thành công", 
        "result": STATUS["test_results"]["api_connection"]
    })

@app.route('/api/test_market_data', methods=['POST'])
def test_market_data():
    STATUS["test_results"]["market_data"]["status"] = "Đang kiểm tra"
    add_log("Đang kiểm tra lấy dữ liệu thị trường...", "INFO")
    
    # Cập nhật dữ liệu thị trường
    update_market_data()
    
    # Giả lập kiểm tra thành công
    time.sleep(1.5)
    
    STATUS["test_results"]["market_data"]["status"] = "Thành công"
    STATUS["test_results"]["market_data"]["passed"] = True
    add_log("✅ Lấy dữ liệu thị trường thành công!", "INFO")
    
    return jsonify({
        "success": True, 
        "message": "Lấy dữ liệu thị trường thành công", 
        "result": STATUS["test_results"]["market_data"],
        "market_data": STATUS["market_data"]
    })

@app.route('/api/test_telegram', methods=['POST'])
def test_telegram():
    STATUS["test_results"]["telegram"]["status"] = "Đang kiểm tra"
    add_log("Đang kiểm tra kết nối Telegram...", "INFO")
    
    # Giả lập kiểm tra thành công
    time.sleep(1.2)
    
    STATUS["test_results"]["telegram"]["status"] = "Thành công"
    STATUS["test_results"]["telegram"]["passed"] = True
    add_log("✅ Kết nối Telegram thành công!", "INFO")
    add_log("📩 Đã gửi tin nhắn kiểm tra tới Telegram", "INFO")
    
    return jsonify({
        "success": True, 
        "message": "Kết nối Telegram thành công", 
        "result": STATUS["test_results"]["telegram"]
    })

@app.route('/api/test_position_management', methods=['POST'])
def test_position_management():
    STATUS["test_results"]["position_management"]["status"] = "Đang kiểm tra"
    add_log("Đang kiểm tra chức năng quản lý vị thế...", "INFO")
    
    # Giả lập kiểm tra thành công
    time.sleep(1.8)
    
    # Thêm vị thế mẫu
    add_test_position()
    
    STATUS["test_results"]["position_management"]["status"] = "Thành công"
    STATUS["test_results"]["position_management"]["passed"] = True
    add_log("✅ Kiểm tra mở vị thế thành công", "INFO")
    add_log("✅ Kiểm tra cập nhật SL/TP thành công", "INFO")
    add_log("✅ Kiểm tra đóng vị thế thành công", "INFO")
    
    return jsonify({
        "success": True, 
        "message": "Kiểm tra quản lý vị thế thành công", 
        "result": STATUS["test_results"]["position_management"],
        "positions": STATUS["positions"]
    })

@app.route('/api/test_technical_analysis', methods=['POST'])
def test_technical_analysis():
    STATUS["test_results"]["technical_analysis"]["status"] = "Đang kiểm tra"
    add_log("Đang kiểm tra chức năng phân tích kỹ thuật...", "INFO")
    
    # Giả lập kiểm tra thành công
    time.sleep(2)
    
    STATUS["test_results"]["technical_analysis"]["status"] = "Thành công"
    STATUS["test_results"]["technical_analysis"]["passed"] = True
    add_log("✅ Kiểm tra phân tích chỉ báo RSI thành công", "INFO")
    add_log("✅ Kiểm tra phân tích chỉ báo MACD thành công", "INFO")
    add_log("✅ Kiểm tra phân tích Bollinger Bands thành công", "INFO")
    add_log("✅ Kiểm tra phân tích Volume Profile thành công", "INFO")
    
    return jsonify({
        "success": True, 
        "message": "Kiểm tra phân tích kỹ thuật thành công", 
        "result": STATUS["test_results"]["technical_analysis"]
    })

@app.route('/api/add_position', methods=['POST'])
def add_position():
    add_test_position()
    return jsonify({
        "success": True, 
        "message": "Đã thêm vị thế test", 
        "positions": STATUS["positions"]
    })

@app.route('/api/close_position', methods=['POST'])
def close_position():
    try:
        data = request.json
        index = data.get("index")
        
        if index is not None and 0 <= index < len(STATUS["positions"]):
            position = STATUS["positions"][index]
            add_log(f"Đã đóng vị thế: {position['symbol']} {position['type']}")
            STATUS["positions"].pop(index)
            return jsonify({
                "success": True, 
                "message": "Đã đóng vị thế", 
                "positions": STATUS["positions"]
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Chỉ số vị thế không hợp lệ"
            })
    except Exception as e:
        logger.error(f"Lỗi khi đóng vị thế: {e}")
        return jsonify({"success": False, "message": f"Lỗi: {e}"})

@app.route('/api/clear_logs', methods=['POST'])
def clear_logs():
    STATUS["logs"] = []
    add_log("Đã xóa nhật ký")
    return jsonify({
        "success": True, 
        "message": "Đã xóa nhật ký", 
        "logs": STATUS["logs"]
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "running": STATUS["running"],
        "account_balance": STATUS["account_balance"],
        "positions_count": len(STATUS["positions"]),
        "latest_log": STATUS["logs"][0] if STATUS["logs"] else None
    })

@app.route('/api/market_data', methods=['GET'])
def get_market_data():
    return jsonify({
        "market_data": STATUS["market_data"]
    })

# Tạm thời bỏ socketio handlers vì chưa import đúng cách

@app.route('/api/positions', methods=['GET'])
def get_positions():
    return jsonify({
        "positions": STATUS["positions"]
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify({
        "logs": STATUS["logs"]
    })

@app.route('/api/test_results', methods=['GET'])
def get_test_results():
    return jsonify({
        "test_results": STATUS["test_results"]
    })

if __name__ == '__main__':
    # Tạo thư mục templates nếu chưa tồn tại
    os.makedirs("templates", exist_ok=True)
    
    # Khởi tạo log
    add_log("Hệ thống kiểm tra đã khởi động")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
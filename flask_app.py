from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Binance Trading Bot API đang hoạt động"

@app.route('/health')
def health():
    return jsonify({
        "status": "ok", 
        "message": "Binance Trader API đang hoạt động",
        "version": "1.0.0"
    })

# Thêm một endpoint để kiểm tra cấu hình
@app.route('/config')
def config():
    return jsonify({
        "app": "Binance Trading Bot",
        "mode": "testnet",
        "port": 5000,
        "api_enabled": True
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
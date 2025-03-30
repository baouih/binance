import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Tạo ứng dụng Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_system_secret_key")

# Cấu hình cơ sở dữ liệu
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///trading.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Khởi tạo SQLAlchemy
db = SQLAlchemy(app)

if __name__ == "__main__":
    # Tạo tất cả các bảng trong cơ sở dữ liệu
    with app.app_context():
        db.create_all()
    
    # Chạy ứng dụng
    app.run(host="0.0.0.0", port=5000, debug=True)
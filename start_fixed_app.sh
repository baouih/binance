#!/bin/bash

# Thiết lập môi trường
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=UTF-8
export SESSION_SECRET="binance_trader_bot_secret"
export SENDFILE=FALSE  # Đảm bảo tắt sendfile

# In ra thông tin phiên bản
echo "Khởi động Binance Trading Bot"
echo "Python version: $(python3 --version)"

# Dừng các tiến trình hiện có nếu có
echo "Dừng các tiến trình hiện có..."
pkill -f "python fixed_app.py" || true
pkill -f gunicorn || true

# Chờ các tiến trình cũ dừng hẳn
sleep 1

# Chạy ứng dụng trực tiếp (không sử dụng gunicorn)
echo "Khởi động ứng dụng với fixed_app.py..."
python3 fixed_app.py
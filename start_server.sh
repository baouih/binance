#!/bin/bash

# Thiết lập môi trường
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=UTF-8
export SESSION_SECRET="binance_trader_bot_secret"

# In ra thông tin phiên bản
echo "Khởi động Binance Trading Bot Server"
echo "Python version: $(python3 --version)"
echo "Gunicorn version: $(gunicorn --version)"
echo "Eventlet version: $(python3 -c 'import eventlet; print(eventlet.__version__)')"

# Dừng các tiến trình hiện có nếu có
echo "Dừng các tiến trình hiện có..."
pkill -f gunicorn || true

# Chờ các tiến trình cũ dừng hẳn
sleep 2

# Khởi động server với eventlet worker
echo "Khởi động server với main_fixed.py..."
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --worker-class eventlet \
    --workers 1 \
    --timeout 120 \
    --reload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    main_fixed:app
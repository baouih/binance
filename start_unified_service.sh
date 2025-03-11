#!/bin/bash

# Script khởi động Dịch vụ hợp nhất
# ----------------------------------
# Script này khởi động unified_trading_service.py trong nền,
# ghi log vào một file riêng.

# Đặt biến môi trường cần thiết
export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1

# Đường dẫn đến các file
LOG_FILE="unified_service.log"
SERVICE_SCRIPT="unified_trading_service.py"
PID_FILE="unified_trading_service.pid"

# Kiểm tra xem dịch vụ đã chạy chưa
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Dịch vụ hợp nhất đã đang chạy với PID $PID"
        exit 0
    else
        echo "File PID tồn tại nhưng process không còn chạy. Xóa file PID cũ."
        rm -f "$PID_FILE"
    fi
fi

# Đảm bảo script có quyền thực thi
chmod +x $SERVICE_SCRIPT

# Khởi động dịch vụ trong nền
echo "Khởi động dịch vụ hợp nhất..."
nohup python $SERVICE_SCRIPT > $LOG_FILE 2>&1 &

# Đợi một chút để đảm bảo service đã khởi động và tạo PID file
sleep 2

# Kiểm tra xem có file PID được tạo không
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "Dịch vụ hợp nhất đã khởi động với PID $PID"
    exit 0
else
    echo "Không thể khởi động dịch vụ hợp nhất. Kiểm tra log: $LOG_FILE"
    exit 1
fi
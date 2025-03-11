#!/bin/bash
# Script để khởi động dịch vụ hợp nhất
# Tác giả: BinanceTrader Bot

# Đường dẫn tới file log
LOG_FILE="unified_service.log"

# Kiểm tra xem dịch vụ đã chạy chưa
if [ -f "unified_trading_service.pid" ]; then
    PID=$(cat unified_trading_service.pid)
    if ps -p $PID > /dev/null; then
        echo "Dịch vụ hợp nhất đã đang chạy với PID $PID"
        exit 1
    else
        echo "Tìm thấy file PID nhưng process không tồn tại, xóa file PID cũ..."
        rm unified_trading_service.pid
    fi
fi

# Tạo file log mới nếu chưa tồn tại
if [ ! -f "$LOG_FILE" ]; then
    touch "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Tạo file log mới" >> "$LOG_FILE"
fi

# Khởi động dịch vụ trong background
echo "Đang khởi động dịch vụ hợp nhất..."
nohup python unified_trading_service.py >> "$LOG_FILE" 2>&1 &

# Đợi một chút và kiểm tra xem dịch vụ đã chạy chưa
sleep 2
if [ -f "unified_trading_service.pid" ]; then
    PID=$(cat unified_trading_service.pid)
    if ps -p $PID > /dev/null; then
        echo "Dịch vụ hợp nhất đã được khởi động thành công với PID $PID"
        exit 0
    fi
fi

echo "Không thể khởi động dịch vụ hợp nhất, kiểm tra file log để biết chi tiết"
exit 1
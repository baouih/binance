#!/bin/bash

# Script tự động khởi động dịch vụ cập nhật dữ liệu thị trường
# Được chạy khi Replit khởi động

# Thiết lập môi trường
export PATH=$PATH:/home/runner/.local/bin

# Đường dẫn đến log
LOG_FILE="auto_start_market_updater.log"

# Ghi log
echo "$(date) - Bắt đầu khởi động dịch vụ cập nhật dữ liệu thị trường" >> $LOG_FILE

# Kiểm tra xem dịch vụ đã chạy chưa
PID_FILE="market_updater.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if kill -0 $PID 2>/dev/null; then
        echo "$(date) - Dịch vụ đã đang chạy với PID $PID" >> $LOG_FILE
        exit 0
    else
        echo "$(date) - PID file tồn tại nhưng dịch vụ không chạy, xóa PID file" >> $LOG_FILE
        rm -f $PID_FILE
    fi
fi

# Khởi động dịch vụ trong nền
echo "$(date) - Khởi động dịch vụ cập nhật dữ liệu thị trường" >> $LOG_FILE
nohup python3 start_market_updater.py > market_updater_nohup.log 2>&1 &

# Ghi log thành công
echo "$(date) - Dịch vụ đã được khởi động với PID $!" >> $LOG_FILE

# Thông báo ra màn hình console
echo "Dịch vụ cập nhật dữ liệu thị trường đã được khởi động."
echo "Log: tail -f market_updater_nohup.log"
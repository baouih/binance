#!/bin/bash
# Script giám sát và đảm bảo dịch vụ trailing stop luôn chạy

LOG_FILE="trailing_stop_monitor.log"
CHECK_INTERVAL=300  # Kiểm tra mỗi 5 phút

echo "$(date) - Khởi động giám sát dịch vụ Trailing Stop" >> $LOG_FILE

while true; do
    # Kiểm tra xem dịch vụ có đang chạy không
    pid=$(ps aux | grep "python position_trailing_stop.py --mode service" | grep -v grep | awk '{print $2}')
    
    if [ -z "$pid" ]; then
        echo "$(date) - Dịch vụ Trailing Stop không chạy, đang khởi động lại..." >> $LOG_FILE
        ./start_trailing_stop.sh >> $LOG_FILE 2>&1
        
        # Kiểm tra xem đã khởi động thành công chưa
        sleep 5
        new_pid=$(ps aux | grep "python position_trailing_stop.py --mode service" | grep -v grep | awk '{print $2}')
        if [ ! -z "$new_pid" ]; then
            echo "$(date) - Đã khởi động lại dịch vụ thành công với PID $new_pid" >> $LOG_FILE
        else
            echo "$(date) - CẢNH BÁO: Không thể khởi động lại dịch vụ!" >> $LOG_FILE
        fi
    else
        echo "$(date) - Dịch vụ Trailing Stop đang chạy với PID $pid" >> $LOG_FILE
    fi
    
    # Chờ đến lần kiểm tra tiếp theo
    sleep $CHECK_INTERVAL
done
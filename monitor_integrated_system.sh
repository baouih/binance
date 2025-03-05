#!/bin/bash
# Script giám sát hệ thống tích hợp quản lý rủi ro và trailing stop

LOG_FILE="integrated_system_monitor.log"
CHECK_INTERVAL=60  # Kiểm tra mỗi 60 giây

# Đảm bảo có quyền thực thi
chmod +x start_integrated_system.sh

echo "$(date) - Bắt đầu giám sát hệ thống tích hợp" > $LOG_FILE

monitor_service() {
    while true; do
        # Kiểm tra xem dịch vụ có đang chạy không
        pid=$(ps aux | grep "python integrated_risk_trailing_system.py --mode service" | grep -v grep | awk '{print $2}')
        
        if [ -z "$pid" ]; then
            echo "$(date) - CẢNH BÁO: Hệ thống tích hợp KHÔNG ĐANG CHẠY! Đang khởi động lại..." >> $LOG_FILE
            ./start_integrated_system.sh >> $LOG_FILE 2>&1
            sleep 5
            
            # Kiểm tra lại sau khi khởi động
            new_pid=$(ps aux | grep "python integrated_risk_trailing_system.py --mode service" | grep -v grep | awk '{print $2}')
            if [ -z "$new_pid" ]; then
                echo "$(date) - LỖI: Không thể khởi động lại hệ thống tích hợp!" >> $LOG_FILE
            else
                echo "$(date) - Đã khởi động lại hệ thống tích hợp thành công với PID $new_pid" >> $LOG_FILE
            fi
        else
            # Ghi nhật ký hoạt động bình thường sau mỗi giờ
            if [ $(( $(date +%s) % 3600 )) -lt $CHECK_INTERVAL ]; then
                echo "$(date) - Hệ thống tích hợp đang hoạt động bình thường (PID: $pid)" >> $LOG_FILE
            fi
        fi
        
        # Chờ đến lần kiểm tra tiếp theo
        sleep $CHECK_INTERVAL
    done
}

# Kiểm tra xem dịch vụ giám sát đã đang chạy chưa
if ps aux | grep -v grep | grep -q "monitor_integrated_system.sh"; then
    pid=$(ps aux | grep -v grep | grep "monitor_integrated_system.sh" | awk '{print $2}' | head -n 1)
    echo "CẢNH BÁO: Dịch vụ giám sát đã đang chạy với PID $pid"
    echo "Nếu bạn muốn khởi động lại, hãy tắt tiến trình cũ trước:"
    echo "  kill $pid"
    exit 1
fi

# Bắt đầu giám sát
echo "Bắt đầu giám sát hệ thống tích hợp..."
monitor_service &

echo "Dịch vụ giám sát đã khởi động."
echo "Log được lưu tại: $LOG_FILE"
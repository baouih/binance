#!/bin/bash
# Script tự động khởi động hệ thống tích hợp khi Replit khởi động lại

LOG_FILE="auto_start_integrated_system.log"

echo "$(date) - Đang tự động khởi động hệ thống tích hợp..." >> $LOG_FILE

# Đảm bảo các script có quyền thực thi
chmod +x start_integrated_system.sh monitor_integrated_system.sh check_trailing_stop.sh

# Cấp quyền thực thi cho tất cả các script cần thiết
chmod +x *.sh

# Khởi động hệ thống tích hợp
./start_integrated_system.sh >> $LOG_FILE 2>&1
sleep 5

# Kiểm tra xem đã khởi động thành công chưa
pid=$(ps aux | grep "python integrated_risk_trailing_system.py --mode service" | grep -v grep | awk '{print $2}')
if [ ! -z "$pid" ]; then
    echo "$(date) - Hệ thống tích hợp đã khởi động thành công với PID $pid" >> $LOG_FILE
else
    echo "$(date) - CẢNH BÁO: Không thể khởi động hệ thống tích hợp!" >> $LOG_FILE
    # Thử khởi động lại
    echo "$(date) - Đang thử khởi động lại..." >> $LOG_FILE
    ./start_integrated_system.sh >> $LOG_FILE 2>&1
fi

# Khởi động dịch vụ giám sát
echo "$(date) - Đang khởi động dịch vụ giám sát..." >> $LOG_FILE
nohup ./monitor_integrated_system.sh > integrated_monitor.log 2>&1 &

echo "$(date) - Quá trình khởi động tự động hoàn tất" >> $LOG_FILE
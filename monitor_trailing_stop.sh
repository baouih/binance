#!/bin/bash
# Script giám sát và đảm bảo dịch vụ trailing stop luôn hoạt động
# Kiểm tra định kỳ và khởi động lại nếu dịch vụ không hoạt động

LOG_FILE="logs/monitor_trailing_stop.log"

# Đảm bảo thư mục logs tồn tại
mkdir -p logs

echo "$(date) - Bắt đầu giám sát hệ thống trailing stop" >> $LOG_FILE

# Kiểm tra xem dịch vụ scheduler có đang chạy không
function check_scheduler() {
    if [ -f "trailing_stop_scheduler.pid" ]; then
        pid=$(cat trailing_stop_scheduler.pid)
        if ps -p $pid > /dev/null; then
            return 0  # Đang chạy
        fi
    fi
    return 1  # Không chạy
}

# Kiểm tra xem dịch vụ trailing stop có đang chạy không
function check_trailing_stop() {
    if [ -f "trailing_stop.pid" ]; then
        pid=$(cat trailing_stop.pid)
        if ps -p $pid > /dev/null; then
            return 0  # Đang chạy
        fi
    fi
    return 1  # Không chạy
}

# Đếm số lần khởi động lại
scheduler_restarts=0
trailing_restarts=0

# Loop kiểm tra mỗi 5 phút
while true; do
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    # Kiểm tra scheduler
    if ! check_scheduler; then
        echo "$timestamp - Scheduler không hoạt động, đang khởi động lại..." >> $LOG_FILE
        scheduler_restarts=$((scheduler_restarts+1))
        
        # Khởi động lại scheduler
        nohup python trailing_stop_scheduler.py schedule --schedule-interval 3600 > logs/scheduler.log 2>&1 &
        echo "$timestamp - Đã khởi động lại scheduler (lần thứ $scheduler_restarts)" >> $LOG_FILE
    else
        echo "$timestamp - Scheduler đang hoạt động bình thường" >> $LOG_FILE
    fi
    
    # Kiểm tra trailing stop
    if ! check_trailing_stop; then
        echo "$timestamp - Dịch vụ trailing stop không hoạt động, đang khởi động lại..." >> $LOG_FILE
        trailing_restarts=$((trailing_restarts+1))
        
        # Khởi động lại dịch vụ trailing stop thông qua scheduler
        python trailing_stop_scheduler.py start --interval 60 >> $LOG_FILE 2>&1
        echo "$timestamp - Đã khởi động lại dịch vụ trailing stop (lần thứ $trailing_restarts)" >> $LOG_FILE
    else
        echo "$timestamp - Dịch vụ trailing stop đang hoạt động bình thường" >> $LOG_FILE
    fi
    
    # Kiểm tra trạng thái tổng thể
    echo "$timestamp - Tổng số lần khởi động lại: Scheduler=$scheduler_restarts, TrailingStop=$trailing_restarts" >> $LOG_FILE
    
    # Nếu có quá nhiều lần khởi động lại, thêm cảnh báo vào log
    if [ $scheduler_restarts -gt 5 ] || [ $trailing_restarts -gt 5 ]; then
        echo "$timestamp - CẢNH BÁO: Có quá nhiều lần khởi động lại, có thể có vấn đề nghiêm trọng!" >> $LOG_FILE
    fi
    
    # Đợi 5 phút
    sleep 300
done
#!/bin/bash

# Script giám sát toàn bộ hệ thống SLTP-Telegram
# V1.0 - 2025-03-09

LOG_FILE="sltp_system_monitor.log"
DATE_FORMAT="+%Y-%m-%d %H:%M:%S"
SLTP_PID_FILE="sltp_telegram_integration.pid"
WATCHDOG_PID_FILE="sltp_watchdog.pid"
MAX_INACTIVE_TIME=900  # 15 phút - thời gian tối đa không có cập nhật log

# Hàm ghi log
log_message() {
    local message="$1"
    local timestamp=$(date "$DATE_FORMAT")
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

# Hàm kiểm tra log file đã được cập nhật gần đây chưa
check_log_activity() {
    local log_file="$1"
    local max_time="$2"
    
    if [ ! -f "$log_file" ]; then
        log_message "CẢNH BÁO: File log $log_file không tồn tại"
        return 1
    fi
    
    # Kiểm tra thời gian cập nhật cuối
    local current_time=$(date +%s)
    local file_time=$(stat -c %Y "$log_file")
    local time_diff=$((current_time - file_time))
    
    if [ $time_diff -gt $max_time ]; then
        log_message "CẢNH BÁO: File log $log_file không được cập nhật trong $time_diff giây (>$max_time)"
        return 1
    fi
    
    return 0
}

# Hàm kiểm tra và khởi động lại hệ thống nếu cần
check_and_restart() {
    # Kiểm tra watchdog
    if [ -f "$WATCHDOG_PID_FILE" ]; then
        WATCHDOG_PID=$(cat "$WATCHDOG_PID_FILE")
        if ! ps -p $WATCHDOG_PID > /dev/null; then
            log_message "CẢNH BÁO: Watchdog với PID $WATCHDOG_PID không còn chạy"
            need_restart=1
        else
            log_message "Watchdog đang chạy với PID $WATCHDOG_PID"
        fi
    else
        log_message "CẢNH BÁO: Không tìm thấy file PID của watchdog"
        need_restart=1
    fi
    
    # Kiểm tra SLTP Telegram
    if [ -f "$SLTP_PID_FILE" ]; then
        SLTP_PID=$(cat "$SLTP_PID_FILE")
        if ! ps -p $SLTP_PID > /dev/null; then
            log_message "CẢNH BÁO: SLTP Telegram với PID $SLTP_PID không còn chạy"
            need_restart=1
        else
            log_message "SLTP Telegram đang chạy với PID $SLTP_PID"
        fi
    else
        log_message "CẢNH BÁO: Không tìm thấy file PID của SLTP Telegram"
        need_restart=1
    fi
    
    # Kiểm tra các log file
    if ! check_log_activity "sltp_telegram_integration.log" $MAX_INACTIVE_TIME; then
        log_message "CẢNH BÁO: Log của SLTP Telegram không hoạt động"
        need_restart=1
    fi
    
    if ! check_log_activity "sltp_watchdog.log" $MAX_INACTIVE_TIME; then
        log_message "CẢNH BÁO: Log của watchdog không hoạt động"
        need_restart=1
    fi
    
    # Nếu cần restart
    if [ "$need_restart" == "1" ]; then
        log_message "Tiến hành khởi động lại toàn bộ hệ thống SLTP-Telegram..."
        
        # Dừng các tiến trình cũ nếu còn chạy
        if [ -f "$WATCHDOG_PID_FILE" ]; then
            WATCHDOG_PID=$(cat "$WATCHDOG_PID_FILE")
            if ps -p $WATCHDOG_PID > /dev/null; then
                log_message "Dừng watchdog cũ (PID: $WATCHDOG_PID)"
                kill $WATCHDOG_PID 2>/dev/null
            fi
            rm -f "$WATCHDOG_PID_FILE"
        fi
        
        if [ -f "$SLTP_PID_FILE" ]; then
            SLTP_PID=$(cat "$SLTP_PID_FILE")
            if ps -p $SLTP_PID > /dev/null; then
                log_message "Dừng SLTP Telegram cũ (PID: $SLTP_PID)"
                kill $SLTP_PID 2>/dev/null
                sleep 2
                # Buộc dừng nếu vẫn còn
                if ps -p $SLTP_PID > /dev/null; then
                    kill -9 $SLTP_PID 2>/dev/null
                fi
            fi
            rm -f "$SLTP_PID_FILE"
        fi
        
        # Đợi các tiến trình dừng hẳn
        sleep 5
        
        # Khởi động lại toàn bộ hệ thống
        log_message "Khởi động lại toàn bộ hệ thống với auto_start_sltp_telegram.sh"
        bash ./auto_start_sltp_telegram.sh
        
        # Thông báo hoàn tất
        log_message "Đã hoàn tất quy trình khởi động lại"
    else
        log_message "Tất cả các thành phần của hệ thống SLTP-Telegram đang hoạt động bình thường"
    fi
}

# Thực thi kiểm tra chính
log_message "Bắt đầu kiểm tra hệ thống SLTP-Telegram..."
need_restart=0

check_and_restart

log_message "Hoàn tất kiểm tra hệ thống"
exit 0
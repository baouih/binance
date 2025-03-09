#!/bin/bash
LOG_FILE="sltp_telegram_integration.log"
PID_FILE="sltp_telegram_integration.pid"
RESTART_FILE="sltp_telegram_integration.restart"
DATE_FORMAT="+%Y-%m-%d %H:%M:%S"
MONITOR_INTERVAL=60  # Kiểm tra mỗi 60 giây
MAX_INACTIVE_TIME=180  # Thời gian tối đa (giây) không có hoạt động trước khi restart

# Hàm ghi log
log_message() {
    local message="$1"
    local timestamp=$(date "$DATE_FORMAT")
    echo "[$timestamp] $message" | tee -a "sltp_telegram_restart.log"
}

# Hàm kiểm tra hoạt động của tiến trình
check_process_activity() {
    local pid=$1
    local log_file=$2
    
    # Kiểm tra xem tiến trình có tồn tại không
    if ! ps -p $pid > /dev/null; then
        log_message "Tiến trình với PID $pid không còn tồn tại"
        return 1
    fi
    
    # Kiểm tra xem log file có được cập nhật gần đây không
    if [ -f "$log_file" ]; then
        local current_time=$(date +%s)
        local file_time=$(stat -c %Y "$log_file")
        local time_diff=$((current_time - file_time))
        
        if [ $time_diff -gt $MAX_INACTIVE_TIME ]; then
            log_message "Log file không được cập nhật trong $time_diff giây (> $MAX_INACTIVE_TIME)"
            return 1
        fi
    else
        log_message "Log file $log_file không tồn tại"
        return 1
    fi
    
    return 0
}

# Đánh dấu restart để tránh vòng lặp vô hạn nếu liên tục lỗi
touch $RESTART_FILE
RESTART_COUNT=0
MAX_RESTARTS=5
RESTART_WINDOW=3600  # 1 giờ

start_sltp_process() {
    # Đảm bảo thư mục logs tồn tại
    mkdir -p logs

    # Khởi động tiến trình với nhiều thông tin gỡ lỗi hơn
    log_message "Khởi động quy trình SLTP Telegram tích hợp..."
    python sltp_telegram_integration.py --testnet --interval 60 >> $LOG_FILE 2>&1 &
    
    # Lấy PID của tiến trình mới
    local new_pid=$!
    echo $new_pid > $PID_FILE
    log_message "Quy trình SLTP Telegram đã khởi động với PID $new_pid"
    
    return $new_pid
}

# Hàm để dừng tiến trình hiện tại nếu cần
stop_current_process() {
    local pid=$1
    
    if [ -n "$pid" ] && ps -p $pid > /dev/null; then
        log_message "Dừng tiến trình hiện tại với PID $pid"
        kill $pid
        sleep 2
        
        # Buộc dừng nếu vẫn còn chạy
        if ps -p $pid > /dev/null; then
            log_message "Buộc dừng tiến trình $pid"
            kill -9 $pid
            sleep 1
        fi
    fi
    
    # Xóa PID file
    if [ -f "$PID_FILE" ]; then
        rm -f $PID_FILE
    fi
}

# Quy trình watchdog chính
while true; do
    # Kiểm tra số lần restart trong window
    CURRENT_TIME=$(date +%s)
    if [ -f "$RESTART_FILE" ]; then
        FILE_TIME=$(stat -c %Y "$RESTART_FILE")
        TIME_DIFF=$((CURRENT_TIME - FILE_TIME))
        
        if [ $TIME_DIFF -gt $RESTART_WINDOW ]; then
            # Reset counter nếu đã qua window
            RESTART_COUNT=0
            touch $RESTART_FILE
        elif [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
            log_message "Đã restart quá nhiều lần ($RESTART_COUNT) trong $RESTART_WINDOW giây. Tạm dừng 1 giờ."
            sleep 3600
            RESTART_COUNT=0
            touch $RESTART_FILE
        fi
    fi
    
    # Kiểm tra xem tiến trình có đang chạy không
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        
        # Kiểm tra hoạt động của tiến trình
        if ! check_process_activity $PID $LOG_FILE; then
            log_message "Phát hiện tiến trình không hoạt động hoặc bị treo. PID: $PID"
            
            # Dừng tiến trình hiện tại nếu cần
            stop_current_process $PID
            
            # Chờ một chút
            sleep 5
            
            # Khởi động lại tiến trình
            log_message "Khởi động lại tiến trình, lần thứ $((RESTART_COUNT+1)) trong window hiện tại"
            start_sltp_process
            RESTART_COUNT=$((RESTART_COUNT+1))
        else
            # Ghi log định kỳ
            log_message "Tiến trình SLTP Telegram đang hoạt động bình thường (PID: $PID)"
        fi
    else
        log_message "Không tìm thấy PID file. Khởi động quy trình"
        start_sltp_process
    fi
    
    # Chờ trước khi kiểm tra lại
    sleep $MONITOR_INTERVAL
done

#!/bin/bash
LOG_FILE="sltp_telegram_integration.log"
PID_FILE="sltp_telegram_integration.pid"
RESTART_FILE="sltp_telegram_integration.restart"
DATE_FORMAT="+%Y-%m-%d %H:%M:%S"

# Hàm ghi log
log_message() {
    local message="$1"
    local timestamp=$(date "$DATE_FORMAT")
    echo "[$timestamp] $message" | tee -a "sltp_telegram_restart.log"
}

# Đánh dấu restart để tránh vòng lặp vô hạn nếu liên tục lỗi
touch $RESTART_FILE
RESTART_COUNT=0
MAX_RESTARTS=5
RESTART_WINDOW=3600  # 1 giờ

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
    
    # Khởi động tiến trình
    log_message "Khởi động lần thứ $((RESTART_COUNT+1)) trong window hiện tại"
    python sltp_telegram_integration.py --testnet --interval 60 >> $LOG_FILE 2>&1
    
    # Nếu tiến trình thoát, ghi log và đợi 10 giây trước khi khởi động lại
    EXIT_CODE=$?
    log_message "Tiến trình SL/TP đã thoát với mã $EXIT_CODE. Khởi động lại sau 10 giây."
    RESTART_COUNT=$((RESTART_COUNT+1))
    
    # Xóa PID file
    if [ -f "$PID_FILE" ]; then
        rm -f $PID_FILE
    fi
    
    sleep 10
done

#!/bin/bash

# Auto start SL/TP with Telegram Integration
# Script tự động khởi động hệ thống quản lý SL/TP tích hợp với Telegram

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

# Kiểm tra xem tiến trình đã chạy chưa
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        log_message "SL/TP with Telegram Integration đã đang chạy với PID $PID. Dừng tiến trình cũ."
        kill $PID
        sleep 2
        # Nếu tiến trình vẫn chạy, buộc dừng
        if ps -p $PID > /dev/null; then
            log_message "Buộc dừng tiến trình $PID"
            kill -9 $PID
            sleep 1
        fi
    else
        log_message "PID file tồn tại nhưng tiến trình không chạy. Xóa PID file cũ."
    fi
    rm -f $PID_FILE
fi

# Kiểm tra file cấu hình Telegram
if [ ! -f "configs/telegram_config.json" ]; then
    log_message "Chưa có file cấu hình Telegram. Tạo file cấu hình mặc định..."
    python -c "from advanced_telegram_notifier import AdvancedTelegramNotifier; AdvancedTelegramNotifier().create_default_config()"
    log_message "Vui lòng cập nhật Telegram Bot Token và Chat ID trong file configs/telegram_config.json"
    exit 1
fi

# Dừng Auto SL/TP Manager nếu đang chạy
if [ -f "auto_sltp_manager.pid" ]; then
    OLD_PID=$(cat auto_sltp_manager.pid)
    if ps -p $OLD_PID > /dev/null; then
        log_message "Dừng Auto SL/TP Manager đang chạy với PID $OLD_PID"
        kill $OLD_PID
        sleep 1
        if ps -p $OLD_PID > /dev/null; then
            kill -9 $OLD_PID
        fi
        rm -f auto_sltp_manager.pid
    fi
fi

# Khởi động SL/TP with Telegram Integration trong nền với wrapper script
log_message "Bắt đầu khởi động SL/TP with Telegram Integration..."

# Tạo watchdog wrapper để giữ tiến trình luôn chạy
cat > sltp_watchdog.sh << 'EOL'
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
EOL

# Cấp quyền thực thi cho watchdog
chmod +x sltp_watchdog.sh

# Khởi động sltp_telegram_integration trực tiếp
log_message "Khởi động sltp_telegram_integration trực tiếp..."
python sltp_telegram_integration.py --testnet --interval 60 >> $LOG_FILE 2>&1 &
SLTP_PID=$!

# Lưu PID
echo $SLTP_PID > $PID_FILE
log_message "SL/TP with Telegram Integration đã được khởi động với PID $SLTP_PID"

# Kiểm tra trạng thái sau 5 giây
sleep 5
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        log_message "SL/TP with Telegram Integration đang chạy bình thường với watchdog."
        echo "SL/TP with Telegram Integration đang chạy bình thường với watchdog."
        echo "Sử dụng 'tail -f $LOG_FILE' để theo dõi log."
    else
        log_message "SL/TP with Telegram Integration khởi động thất bại."
        echo "SL/TP with Telegram Integration khởi động thất bại."
        rm -f $PID_FILE
        exit 1
    fi
else
    log_message "Không tìm thấy PID file. Khởi động thất bại."
    echo "Không tìm thấy PID file. Khởi động thất bại."
    exit 1
fi
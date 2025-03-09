#!/bin/bash

# Script tự động chạy kiểm tra SL/TP định kỳ
# Version 1.0 - 2025-03-09

LOG_FILE="sltp_checks.log"
DATE_FORMAT="+%Y-%m-%d %H:%M:%S"
CHECK_INTERVAL=300  # Kiểm tra mỗi 5 phút (300 giây)

# Hàm ghi log
log_message() {
    local message="$1"
    local timestamp=$(date "$DATE_FORMAT")
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

# Kiểm tra và cài đặt cài đặt ban đầu
mkdir -p logs

# Kiểm tra xem file check_sltp_status.py có tồn tại không
if [ ! -f "check_sltp_status.py" ]; then
    log_message "CẢNH BÁO: Không tìm thấy file check_sltp_status.py"
    exit 1
fi

# Cấp quyền thực thi
chmod +x check_sltp_status.py

log_message "Bắt đầu lịch trình kiểm tra SL/TP định kỳ (interval = $CHECK_INTERVAL giây)"

while true; do
    # Thực hiện kiểm tra SL/TP
    log_message "Đang chạy kiểm tra SL/TP định kỳ..."
    
    # Chạy với testnet flag
    python check_sltp_status.py --testnet | tee -a "check_sltp_detail.log"
    
    # Kiểm tra nếu có vấn đề, sẽ tự động reset
    if grep -q "Số vị thế cần thiết lập lại SL/TP:" "check_sltp_detail.log" | tail -1 | grep -q -v "0"; then
        log_message "Phát hiện vị thế cần thiết lập lại SL/TP, tiến hành reset tự động..."
        python check_sltp_status.py --testnet --reset | tee -a "reset_sltp_detail.log"
        
        # Gửi thông báo tới Telegram
        if [ -f "telegram_position_notifier.py" ]; then
            log_message "Gửi thông báo reset SL/TP qua Telegram..."
            python telegram_position_notifier.py --message "⚠️ ĐÃ PHÁT HIỆN VÀ RESET SL/TP: Hệ thống phát hiện lệnh SL/TP bị thiếu và đã thực hiện thiết lập lại tự động. Kiểm tra log để biết thêm chi tiết." --testnet
        fi
    else
        log_message "Tất cả vị thế đều có SL/TP đầy đủ ✅"
    fi
    
    log_message "Kiểm tra hoàn tất, chờ $CHECK_INTERVAL giây cho lần kiểm tra tiếp theo..."
    sleep $CHECK_INTERVAL
done
#!/bin/bash

# Script cài đặt các gói phụ thuộc cần thiết
# V1.0 - 2025-03-09

LOG_FILE="dependencies_installation.log"
DATE_FORMAT="+%Y-%m-%d %H:%M:%S"

# Hàm ghi log
log_message() {
    local message="$1"
    local timestamp=$(date "$DATE_FORMAT")
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

echo "===================================================="
echo "  CÀI ĐẶT GÓI PHỤ THUỘC HỆ THỐNG SLTP TELEGRAM  "
echo "===================================================="
echo ""

log_message "Bắt đầu cài đặt các gói phụ thuộc..."

# Cài đặt setproctitle
log_message "Cài đặt gói setproctitle cho quản lý tên tiến trình..."
pip install setproctitle
if [ $? -ne 0 ]; then
    log_message "Không thể cài đặt setproctitle, thử dùng pip3..."
    pip3 install setproctitle
fi

# Cài đặt các gói phụ thuộc khác
log_message "Cài đặt các gói phụ thuộc khác..."
pip install python-binance ccxt pandas tqdm schedule websocket-client requests python-telegram-bot python-dotenv tabulate
if [ $? -ne 0 ]; then
    log_message "Lỗi khi cài đặt một số gói, thử lại với pip3..."
    pip3 install python-binance ccxt pandas tqdm schedule websocket-client requests python-telegram-bot python-dotenv tabulate
fi

# Kiểm tra cấp quyền thực thi cho các scripts
log_message "Cấp quyền thực thi cho các scripts..."
chmod +x *.sh
chmod +x *.py

log_message "Hoàn tất cài đặt gói phụ thuộc."
echo ""
echo "===================================================="
echo "  CÀI ĐẶT HOÀN TẤT  "
echo "===================================================="
echo ""
echo "Để chạy hệ thống, thực hiện các bước sau:"
echo "1. Khởi động hệ thống: ./auto_start_sltp_telegram.sh"
echo "2. Thiết lập cronjob:  ./auto_setup_cron_restart.sh"
echo ""
echo "Log file: $LOG_FILE"
echo "===================================================="

exit 0
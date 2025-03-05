#!/bin/bash
# Script chạy tự động khi Replit khởi động
# Đặt script này vào file .replit trong phần "onBoot"

# Đường dẫn đến log
LOG_FILE="startup.log"

# Hàm ghi log
log() {
    echo "$(date) - $1" >> $LOG_FILE
    echo "$1"
}

# Ghi log bắt đầu
log "===== KHỞI ĐỘNG HỆ THỐNG ====="

# Đảm bảo quyền thực thi cho các script
chmod +x auto_recovery.sh
chmod +x watchdog.sh
chmod +x watchdog_runner.sh
chmod +x auto_start_market_updater.sh
chmod +x telegram_watchdog.py

# Chạy auto_recovery để thiết lập hệ thống
log "Chạy Auto Recovery..."
./auto_recovery.sh

# Thiết lập script chạy nền để giám sát liên tục
log "Khởi động giám sát liên tục..."
nohup python3 telegram_watchdog.py > telegram_watchdog_output.log 2>&1 &

log "Hệ thống đã được khởi động thành công"
#!/bin/bash

# Script thiết lập cronjob để tự động khởi động lại
# hệ thống SLTP-Telegram theo lịch trình
# V1.0 - 2025-03-09

LOG_FILE="crontab_setup.log"
DATE_FORMAT="+%Y-%m-%d %H:%M:%S"

# Hàm ghi log
log_message() {
    local message="$1"
    local timestamp=$(date "$DATE_FORMAT")
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

# Cấp quyền thực thi cho các scripts
log_message "Đảm bảo tất cả các scripts có quyền thực thi..."
chmod +x auto_start_sltp_telegram.sh
chmod +x sltp_watchdog.sh
chmod +x sltp_system_monitor.sh

# Lấy thông tin đường dẫn thư mục hiện tại
CURRENT_DIR=$(pwd)
log_message "Thư mục hiện tại: $CURRENT_DIR"

# Thiết lập cronjob để chạy monitor script mỗi 15 phút
log_message "Thiết lập cronjob để giám sát hệ thống mỗi 15 phút..."
(crontab -l 2>/dev/null | grep -v "sltp_system_monitor.sh"; echo "*/15 * * * * cd $CURRENT_DIR && bash ./sltp_system_monitor.sh >> sltp_cron_monitor.log 2>&1") | crontab -

# Thiết lập cronjob để khởi động lại hệ thống mỗi 12 giờ
log_message "Thiết lập cronjob để khởi động lại hệ thống mỗi 12 giờ..."
(crontab -l 2>/dev/null | grep -v "auto_start_sltp_telegram.sh"; echo "0 */12 * * * cd $CURRENT_DIR && bash ./auto_start_sltp_telegram.sh >> sltp_cron_restart.log 2>&1") | crontab -

# Hiển thị các cronjob đã được thiết lập
log_message "Các cronjob đã được thiết lập:"
crontab -l | grep -E "sltp_system_monitor.sh|auto_start_sltp_telegram.sh" | tee -a "$LOG_FILE"

echo "-------------------------------------"
echo "Thiết lập cronjob thành công!"
echo "Hệ thống sẽ được:"
echo "- Giám sát mỗi 15 phút"
echo "- Khởi động lại tự động mỗi 12 giờ"
echo "-------------------------------------"
echo "Bạn có thể xem log tại:"
echo "- $LOG_FILE (thiết lập crontab)"
echo "- sltp_cron_monitor.log (log giám sát)"
echo "- sltp_cron_restart.log (log khởi động lại tự động)"
echo "-------------------------------------"

exit 0
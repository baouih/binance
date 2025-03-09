#!/bin/bash
# Script cài đặt các tác vụ cron để tự động khởi động dịch vụ

# Đường dẫn tới thư mục hiện tại
CURRENT_DIR=$(pwd)
LOG_FILE="crontab_setup.log"

# Ghi log
log() {
    echo "[$(date)] $1" | tee -a "$LOG_FILE"
}

# Bắt đầu quá trình cài đặt
log "===== Bắt đầu cài đặt tự động khởi động ====="
log "Thư mục hiện tại: $CURRENT_DIR"

# Đảm bảo tất cả script có quyền thực thi
log "Cấp quyền thực thi cho tất cả script..."
chmod +x *.sh *.py
log "Đã cấp quyền thực thi"

# Tạo task cron
log "Tạo các tác vụ cron..."

# Lấy danh sách cron hiện tại
crontab -l > mycron 2>/dev/null || echo "# Crontab for trading system" > mycron

# Kiểm tra và thêm các tác vụ nếu chưa có
if ! grep -q "auto_startup_services.sh" mycron; then
    log "Thêm tác vụ khởi động dịch vụ 5 phút một lần..."
    # Mỗi 5 phút kiểm tra và khởi động lại dịch vụ nếu cần
    echo "*/5 * * * * cd $CURRENT_DIR && ./auto_startup_services.sh >> $CURRENT_DIR/system_check.log 2>&1" >> mycron
fi

if ! grep -q "fix_trailing_stop.sh" mycron; then
    log "Thêm tác vụ kiểm tra Trailing Stop hàng giờ..."
    # Mỗi giờ đảm bảo dịch vụ Trailing Stop đang chạy
    echo "0 * * * * cd $CURRENT_DIR && ./fix_trailing_stop.sh >> $CURRENT_DIR/trailing_stop_monitor.log 2>&1" >> mycron
fi

if ! grep -q "headless_start_sltp_manager.sh" mycron; then
    log "Thêm tác vụ kiểm tra SLTP Manager hàng giờ..."
    # Mỗi giờ đảm bảo dịch vụ Auto SLTP Manager đang chạy
    echo "15 * * * * cd $CURRENT_DIR && ./headless_start_sltp_manager.sh >> $CURRENT_DIR/sltp_monitor.log 2>&1" >> mycron
fi

# Cài đặt cron mới
crontab mycron
log "Đã cài đặt các tác vụ cron"

# Xóa file tạm
rm mycron

# Kiểm tra kết quả
log "Kiểm tra cài đặt cron..."
crontab -l

log "===== Hoàn thành cài đặt tự động khởi động ====="
log "Các dịch vụ sẽ được tự động kiểm tra và khởi động lại nếu cần"

echo
echo "===== CÀI ĐẶT TỰ ĐỘNG KHỞI ĐỘNG DỊCH VỤ ====="
echo "✅ Đã cài đặt tác vụ kiểm tra dịch vụ mỗi 5 phút"
echo "✅ Đã cài đặt tác vụ kiểm tra Trailing Stop hàng giờ"
echo "✅ Đã cài đặt tác vụ kiểm tra SLTP Manager hàng giờ"
echo 
echo "Các dịch vụ sẽ được tự động khởi động lại nếu bị dừng"
echo "Xem log trong file: $LOG_FILE"
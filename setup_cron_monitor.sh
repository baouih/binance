#!/bin/bash
# Script cài đặt lịch kiểm tra sức khỏe tự động

echo "===== CÀI ĐẶT KIỂM TRA SỨC KHỎE TỰ ĐỘNG ====="
echo "Script này sẽ cài đặt lịch kiểm tra sức khỏe tự động mỗi 30 phút"

# Kiểm tra quyền thực thi của các script
if [ ! -x "health_check.sh" ]; then
    chmod +x health_check.sh
    echo "✅ Đã cấp quyền thực thi cho health_check.sh"
fi

if [ ! -x "monitor_system.sh" ]; then
    chmod +x monitor_system.sh
    echo "✅ Đã cấp quyền thực thi cho monitor_system.sh"
fi

# Tạo cron job
CURRENT_DIR=$(pwd)
CRON_JOB="*/30 * * * * cd $CURRENT_DIR && ./health_check.sh > /dev/null 2>&1"

# Kiểm tra xem cron job đã tồn tại chưa
EXISTING_CRON=$(crontab -l 2>/dev/null | grep "health_check.sh")

if [ -z "$EXISTING_CRON" ]; then
    # Thêm cron job mới
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Đã cài đặt lịch kiểm tra sức khỏe tự động mỗi 30 phút"
else
    echo "ℹ️ Lịch kiểm tra sức khỏe tự động đã được cài đặt trước đó"
fi

# Hiển thị cron jobs đã cài đặt
echo
echo "Danh sách cron jobs hiện tại:"
crontab -l
echo

echo "✅ Quá trình cài đặt hoàn tất!"
echo "⏱️ Hệ thống sẽ được kiểm tra sức khỏe tự động mỗi 30 phút"
echo "📝 Log được lưu tại: health_check.log"
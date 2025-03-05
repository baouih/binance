#!/bin/bash
# Script giám sát trạng thái của bot và xử lý sự cố

# Đường dẫn đến file log
LOG_FILE="watchdog.log"

# Hàm ghi log
log_message() {
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" >> "$LOG_FILE"
}

# Hàm kiểm tra xem bot có đang chạy không
check_bot_running() {
  # Kiểm tra workflow có đang chạy không
  if curl -s http://localhost:5000/ > /dev/null; then
    return 0  # Bot đang chạy
  else
    return 1  # Bot không chạy
  fi
}

# Hàm kiểm tra thời gian cập nhật cuối cùng
check_update_time() {
  # Đọc last_update từ bot_status.json
  LAST_UPDATE=$(grep -o '"last_update": "[^"]*"' bot_status.json | cut -d'"' -f4)
  
  # Chuyển đổi thành timestamp
  LAST_UPDATE_TS=$(date -d "$LAST_UPDATE" +%s)
  CURRENT_TS=$(date +%s)
  
  # Tính thời gian trôi qua (giây)
  ELAPSED_TIME=$((CURRENT_TS - LAST_UPDATE_TS))
  
  # Nếu thời gian trôi qua lớn hơn 5 phút (300 giây), coi như bot bị treo
  if [ $ELAPSED_TIME -gt 300 ]; then
    return 1  # Bot bị treo
  else
    return 0  # Bot hoạt động bình thường
  fi
}

# Hàm gửi thông báo
send_notification() {
  MESSAGE="$1"
  log_message "$MESSAGE"
  
  # Thêm mã gửi thông báo qua telegram_watchdog nếu cần
  # python3 telegram_watchdog.py "$MESSAGE" &
}

# Hàm khởi động lại bot
restart_bot() {
  log_message "Đang khởi động lại bot..."
  
  # Kiểm tra xem có tiến trình auto_recovery.sh đang chạy không
  if pgrep -f "auto_recovery.sh" > /dev/null; then
    log_message "auto_recovery.sh đang chạy, giao việc khôi phục cho nó"
  else
    log_message "auto_recovery.sh không chạy, khởi động lại nó"
    ./auto_recovery.sh > /dev/null 2>&1 &
  fi
  
  # Đợi auto_recovery khôi phục 
  sleep 60
  
  # Kiểm tra lại
  if check_bot_running; then
    log_message "Bot đã được khôi phục thành công sau 60 giây"
    send_notification "✅ Bot đã được watchdog khôi phục thành công!"
  else
    log_message "Bot vẫn không hoạt động sau khi thử khôi phục, cần can thiệp thủ công"
    send_notification "❌ Bot không thể tự động khôi phục, cần can thiệp thủ công!"
  fi
}

# Bắt đầu giám sát
log_message "Bắt đầu script watchdog"
send_notification "🔍 Watchdog đã được kích hoạt và đang giám sát bot"

while true; do
  # Kiểm tra xem bot có đang chạy không
  if ! check_bot_running; then
    log_message "CẢNH BÁO: Bot không phản hồi!"
    send_notification "⚠️ Bot không phản hồi, đang thử khởi động lại..."
    restart_bot
  elif ! check_update_time; then
    log_message "CẢNH BÁO: Bot không cập nhật trạng thái trong 5 phút qua!"
    send_notification "⚠️ Bot có vẻ bị treo (không cập nhật trong 5 phút), đang thử khởi động lại..."
    restart_bot
  else
    log_message "Bot đang hoạt động bình thường, cập nhật gần nhất: $(grep -o '"last_update": "[^"]*"' bot_status.json | cut -d'"' -f4)"
  fi
  
  # Kiểm tra mỗi 3 phút
  sleep 180
done
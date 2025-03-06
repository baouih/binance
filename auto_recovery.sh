#!/bin/bash
# Script auto-recovery tự động khôi phục hoạt động của bot khi bị dừng

# Đường dẫn đến file log
LOG_FILE="auto_recovery.log"

# Hàm ghi log
log_message() {
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" >> "$LOG_FILE"
}

# Hàm kiểm tra trạng thái bot
check_bot_status() {
  # Kiểm tra xem workflow đang chạy hay không
  if [[ $(curl -s http://localhost:5000/api/status | grep -c "\"running\":true") -eq 0 ]]; then
    return 1  # Bot không chạy
  else
    return 0  # Bot đang chạy
  fi
}

# Hàm gửi thông báo Telegram
send_telegram_notification() {
  local MESSAGE="$1"
  # Thêm mã để gửi thông báo qua Telegram nếu cần
  # Ví dụ: curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" -d chat_id=$CHAT_ID -d text="$MESSAGE"
  log_message "Đã gửi thông báo: $MESSAGE"
}

# Hàm khởi động lại bot
restart_bot() {
  log_message "Đang khởi động lại bot..."
  
  # Kiểm tra xem workflow đã tồn tại chưa
  if [[ $(replit workflow list | grep -c "Start application") -gt 0 ]]; then
    # Khởi động lại workflow
    replit workflow restart "Start application"
    log_message "Đã khởi động lại workflow 'Start application'"
  else
    # Tạo mới workflow nếu chưa tồn tại
    log_message "Workflow 'Start application' không tồn tại, đang khởi động thủ công"
    gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app &
    log_message "Đã khởi động thủ công gunicorn process"
  fi
  
  # Khởi động lại các script giám sát
  if pgrep -f "telegram_watchdog.py" > /dev/null; then
    log_message "Telegram watchdog đã chạy, bỏ qua"
  else
    python3 telegram_watchdog.py &
    log_message "Đã khởi động lại telegram_watchdog.py"
  fi
  
  # Đảm bảo script cập nhật trạng thái và vị thế đang chạy
  if pgrep -f "update_status.sh" > /dev/null; then
    log_message "Script update_status.sh đã chạy, bỏ qua"
  else
    bash -c 'while true; do ./update_status.sh > /dev/null 2>&1; sleep 60; done &'
    log_message "Đã khởi động lại update_status.sh mỗi phút"
  fi
  
  if pgrep -f "update_positions.sh" > /dev/null; then
    log_message "Script update_positions.sh đã chạy, bỏ qua"
  else
    bash -c 'while true; do ./update_positions.sh > /dev/null 2>&1; sleep 300; done &'
    log_message "Đã khởi động lại update_positions.sh mỗi 5 phút"
  fi
  
  # Gửi thông báo
  send_telegram_notification "🤖 Bot đã được khôi phục tự động và đang chạy lại!"
}

# Vòng lặp chính
log_message "Bắt đầu auto-recovery service"
while true; do
  if ! check_bot_status; then
    log_message "Phát hiện bot không hoạt động!"
    send_telegram_notification "⚠️ Bot đã dừng hoạt động, đang khôi phục..."
    restart_bot
    
    # Chờ một lúc để bot khởi động
    sleep 30
    
    # Kiểm tra lại
    if check_bot_status; then
      log_message "Bot đã được khôi phục thành công!"
    else
      log_message "Không thể khôi phục bot sau lần thử đầu tiên, thử lại sau 5 phút"
      sleep 300
    fi
  else
    log_message "Bot đang hoạt động bình thường, kiểm tra tiếp theo sau 3 phút"
  fi
  
  # Kiểm tra mỗi 3 phút
  sleep 180
done
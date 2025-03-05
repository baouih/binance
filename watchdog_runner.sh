#!/bin/bash
# Script giám sát các watchdog chính - đảm bảo hệ thống giám sát luôn hoạt động

# Đường dẫn đến file log
LOG_FILE="watchdog_runner.log"

# Hàm ghi log
log_message() {
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" >> "$LOG_FILE"
}

# Hàm kiểm tra và khởi động lại các watchdog
ensure_watchdogs_running() {
  # Kiểm tra auto_recovery.sh
  if ! pgrep -f "auto_recovery.sh" > /dev/null; then
    log_message "auto_recovery.sh không chạy, đang khởi động lại..."
    ./auto_recovery.sh > /dev/null 2>&1 &
    sleep 2
    if pgrep -f "auto_recovery.sh" > /dev/null; then
      log_message "auto_recovery.sh đã được khởi động lại thành công"
    else
      log_message "KHÔNG THỂ khởi động lại auto_recovery.sh"
    fi
  else
    log_message "auto_recovery.sh đang chạy bình thường"
  fi
  
  # Kiểm tra watchdog.sh
  if ! pgrep -f "watchdog.sh" > /dev/null; then
    log_message "watchdog.sh không chạy, đang khởi động lại..."
    ./watchdog.sh > /dev/null 2>&1 &
    sleep 2
    if pgrep -f "watchdog.sh" > /dev/null; then
      log_message "watchdog.sh đã được khởi động lại thành công"
    else
      log_message "KHÔNG THỂ khởi động lại watchdog.sh"
    fi
  else
    log_message "watchdog.sh đang chạy bình thường"
  fi
  
  # Kiểm tra telegram_watchdog.py
  if ! pgrep -f "telegram_watchdog.py" > /dev/null; then
    log_message "telegram_watchdog.py không chạy, đang khởi động lại..."
    python3 telegram_watchdog.py "⚠️ Telegram Watchdog đã được tự động khởi động lại bởi watchdog_runner.sh" &
    sleep 2
    if pgrep -f "telegram_watchdog.py" > /dev/null; then
      log_message "telegram_watchdog.py đã được khởi động lại thành công"
    else
      log_message "KHÔNG THỂ khởi động lại telegram_watchdog.py"
    fi
  else
    log_message "telegram_watchdog.py đang chạy bình thường"
  fi
  
  # Kiểm tra update_status.sh (chạy dưới dạng vòng lặp)
  if ! pgrep -f "update_status.sh" > /dev/null; then
    log_message "update_status.sh không chạy, đang khởi động lại..."
    bash -c 'while true; do ./update_status.sh > /dev/null 2>&1; sleep 60; done &'
    sleep 2
    if pgrep -f "update_status.sh" > /dev/null; then
      log_message "update_status.sh đã được khởi động lại thành công"
    else
      log_message "KHÔNG THỂ khởi động lại update_status.sh"
    fi
  else
    log_message "update_status.sh đang chạy bình thường"
  fi
  
  # Kiểm tra update_positions.sh (chạy dưới dạng vòng lặp)
  if ! pgrep -f "update_positions.sh" > /dev/null; then
    log_message "update_positions.sh không chạy, đang khởi động lại..."
    bash -c 'while true; do ./update_positions.sh > /dev/null 2>&1; sleep 300; done &'
    sleep 2
    if pgrep -f "update_positions.sh" > /dev/null; then
      log_message "update_positions.sh đã được khởi động lại thành công"
    else
      log_message "KHÔNG THỂ khởi động lại update_positions.sh"
    fi
  else
    log_message "update_positions.sh đang chạy bình thường"
  fi
}

# Bắt đầu giám sát
log_message "Bắt đầu watchdog_runner - Master Watchdog Service"

# Đảm bảo tất cả các script được cấp quyền thực thi
chmod +x auto_recovery.sh watchdog.sh update_status.sh update_positions.sh 
chmod +x telegram_watchdog.py

# Vòng lặp chính
while true; do
  log_message "Kiểm tra trạng thái các watchdog..."
  ensure_watchdogs_running
  
  # Kiểm tra mỗi 5 phút
  sleep 300
done
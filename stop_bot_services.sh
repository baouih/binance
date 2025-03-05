#!/bin/bash
# Script dừng tất cả các dịch vụ bot
echo "Dừng tất cả dịch vụ bot..."

# Dừng dịch vụ keep-alive
if [ -f "keep_alive.pid" ]; then
  KEEP_ALIVE_PID=$(cat keep_alive.pid)
  if ps -p $KEEP_ALIVE_PID > /dev/null; then
    echo "Dừng dịch vụ keep-alive (PID: $KEEP_ALIVE_PID)..."
    kill $KEEP_ALIVE_PID
    echo "Đã dừng dịch vụ keep-alive"
  else
    echo "Dịch vụ keep-alive không hoạt động"
  fi
  rm keep_alive.pid
else
  echo "Không tìm thấy file keep_alive.pid"
fi

# Dừng dịch vụ trailing stop
if [ -f "trailing_stop.pid" ]; then
  TRAILING_STOP_PID=$(cat trailing_stop.pid)
  if ps -p $TRAILING_STOP_PID > /dev/null; then
    echo "Dừng dịch vụ trailing stop (PID: $TRAILING_STOP_PID)..."
    kill $TRAILING_STOP_PID
    echo "Đã dừng dịch vụ trailing stop"
  else
    echo "Dịch vụ trailing stop không hoạt động"
  fi
  rm trailing_stop.pid
else
  echo "Không tìm thấy file trailing_stop.pid"
fi

# Kiểm tra xem còn tiến trình nào liên quan đến bot đang chạy không
echo ""
echo "Kiểm tra các tiến trình bot còn đang chạy..."
ps aux | grep -E "setup_always_on|position_trailing_stop|auto_trade_scheduler" | grep -v grep

# Hiển thị hướng dẫn khởi động lại
echo ""
echo "Để khởi động lại các dịch vụ:"
echo "./start_bot_services.sh"
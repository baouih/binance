#!/bin/bash

# Script để khởi động bot giao dịch tự động
echo "=== Đang khởi động bot giao dịch tự động ==="
echo "Thời gian bắt đầu: $(date)"

# Kiểm tra khóa API
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
  echo "Lỗi: Không tìm thấy khóa API Binance. Vui lòng đảm bảo BINANCE_API_KEY và BINANCE_API_SECRET đã được cài đặt."
  exit 1
fi

# Khởi tạo file log
LOG_FILE="trading_bot_$(date +%Y%m%d_%H%M%S).log"
echo "Ghi log vào: $LOG_FILE"

# Chạy bot
echo "Đang khởi động bot giao dịch..."

# Chế độ giả lập
python3 run_live_trading.py 2>&1 | tee -a $LOG_FILE

# Để chạy ở chế độ thực, bỏ comment dòng dưới và comment dòng trên
# python3 run_live_trading.py --live_mode=true 2>&1 | tee -a $LOG_FILE

echo "Bot đã dừng tại: $(date)"
echo "Xem log đầy đủ trong file: $LOG_FILE"
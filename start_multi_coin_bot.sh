#!/bin/bash

# Script để khởi động bot giao dịch đa đồng tiền
# Có thể truyền các tham số tùy chọn như --live, --interval, etc.

echo "=== Đang khởi động bot giao dịch đa đồng tiền ==="
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="multi_coin_bot_${TIMESTAMP}.log"

echo "Thời gian bắt đầu: $(date)"
echo "Ghi log vào: ${LOG_FILE}"

# Kiểm tra nếu file config tồn tại
if [ ! -f "multi_coin_config.json" ]; then
    echo "Lỗi: Không tìm thấy file cấu hình multi_coin_config.json"
    exit 1
fi

# Chạy bot (bỏ comment dòng thích hợp)

# Chế độ giả lập (mặc định)
python3 multi_coin_trading.py "$@" 2>&1 | tee -a $LOG_FILE

# Chế độ thực
# python3 multi_coin_trading.py --live "$@" 2>&1 | tee -a $LOG_FILE 

echo "=== Bot giao dịch đã bắt đầu. Nhấn Ctrl+C để dừng ==="
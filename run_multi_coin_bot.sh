#!/bin/bash

# Script để khởi động bot giao dịch đa đồng tiền đơn giản hóa
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

# Kiểm tra quyền thực thi
if [ ! -x "multi_coin_bot.py" ]; then
    chmod +x multi_coin_bot.py
    echo "Đã thiết lập quyền thực thi cho multi_coin_bot.py"
fi

# Chạy bot (bỏ comment dòng thích hợp)

# Chế độ giả lập (mặc định)
python3 multi_coin_bot.py --interval 60 "$@" 2>&1 | tee -a $LOG_FILE

# Chế độ thực
# python3 multi_coin_bot.py --live --interval 60 "$@" 2>&1 | tee -a $LOG_FILE 

echo "=== Bot giao dịch đã khởi động. Nhấn Ctrl+C để dừng ==="
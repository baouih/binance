#!/bin/bash
# Script chạy direct_app.py với cấu hình phù hợp

echo "Khởi động Binance Trading Bot (direct_app)"
echo "Thời gian khởi động: $(date)"
echo "----------------------------------------"

# Kiểm tra python đã cài đặt
if ! command -v python &> /dev/null; then
    echo "Lỗi: Python không được tìm thấy"
    exit 1
fi

# Chạy ứng dụng
echo "Khởi động ứng dụng trên port 8080..."
python direct_app.py
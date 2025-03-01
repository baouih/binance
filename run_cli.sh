#!/bin/bash

# Script để khởi động phiên bản CLI của Binance Futures Trading Bot
# Tập lệnh này sẽ tự động dừng phiên bản web (nếu đang chạy)
# và khởi động phiên bản CLI

echo "====================================================="
echo "     Khởi động Binance Futures Trading Bot - CLI     "
echo "====================================================="

# Kiểm tra xem có PID của phiên bản web không
if [ -f "web_server.pid" ]; then
    WEB_PID=$(cat web_server.pid)
    if ps -p $WEB_PID > /dev/null 2>&1; then
        echo "Đang tắt phiên bản web (PID: $WEB_PID)..."
        kill $WEB_PID
        sleep 2
    fi
    rm -f web_server.pid
fi

# Kiểm tra .env
if [ ! -f ".env" ]; then
    echo "CẢNH BÁO: Không tìm thấy file .env!"
    echo "Vui lòng đảm bảo rằng các API keys được cấu hình đúng."
fi

# Kiểm tra multi_coin_config.json
if [ ! -f "multi_coin_config.json" ]; then
    echo "CẢNH BÁO: Không tìm thấy file multi_coin_config.json!"
    echo "Vui lòng tạo file cấu hình trước khi chạy bot."
fi

# Khởi động phiên bản CLI
echo ""
echo "Đang khởi động phiên bản CLI..."
echo ""

# Thực thi phiên bản CLI
python new_main.py
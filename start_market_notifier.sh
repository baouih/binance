#!/bin/bash
# Script khởi động dịch vụ thông báo thị trường tự động
# BinanceTrader Bot - Phiên bản 3.2.1

# Thư mục hiện tại
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Kiểm tra đã cài đặt Python chưa
if ! command -v python3 &> /dev/null; then
    echo "Python 3 chưa được cài đặt. Vui lòng cài đặt Python 3 trước khi sử dụng."
    exit 1
fi

# Kiểm tra môi trường
if [ ! -f .env ]; then
    echo "File .env không tồn tại. Đang tạo file mặc định..."
    touch .env
    echo "TELEGRAM_BOT_TOKEN=your_telegram_token" >> .env
    echo "TELEGRAM_CHAT_ID=your_chat_id" >> .env
    echo "BINANCE_API_KEY=your_api_key" >> .env
    echo "BINANCE_API_SECRET=your_api_secret" >> .env
    echo "API_MODE=testnet" >> .env
    echo "File .env đã được tạo. Vui lòng cập nhật thông tin API trước khi sử dụng."
fi

# Kiểm tra xem script auto_market_notifier.py đã chạy chưa
PID_FILE="market_notifier.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null; then
        echo "Dịch vụ thông báo thị trường đã đang chạy với PID $PID"
        exit 0
    else
        echo "PID cũ $PID không tồn tại. Bắt đầu một quy trình mới..."
        rm "$PID_FILE"
    fi
fi

echo "Đang khởi động dịch vụ thông báo thị trường..."

# Chạy script trong nền
nohup python3 auto_market_notifier.py > market_notifier.log 2>&1 &

# Lưu PID
echo $! > "$PID_FILE"
echo "Dịch vụ thông báo thị trường đã được khởi động với PID $(cat $PID_FILE)"

# Đợi một chút để xác nhận script đã chạy thành công
sleep 2
if ! ps -p $(cat "$PID_FILE") > /dev/null; then
    echo "Khởi động thất bại. Kiểm tra market_notifier.log để biết thêm chi tiết."
    exit 1
fi

echo "-----------------------------------"
echo "Dịch vụ thông báo thị trường đã được khởi động thành công!"
echo "Log: market_notifier.log"
echo "PID: $(cat $PID_FILE)"
echo "-----------------------------------"
exit 0
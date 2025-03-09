#!/bin/bash

# Script khởi động hệ thống giao dịch theo thời gian tối ưu
# Sử dụng với nohup để chạy trong nền

# Đường dẫn đến thư mục gốc
ROOT_DIR="$(pwd)"

# Tạo thư mục logs nếu chưa tồn tại
mkdir -p "$ROOT_DIR/logs"

# Tên file log
LOG_FILE="$ROOT_DIR/logs/time_based_trading_$(date +%Y%m%d_%H%M%S).log"

# Kiểm tra các biến môi trường
if [ -z "$BINANCE_TESTNET_API_KEY" ] || [ -z "$BINANCE_TESTNET_API_SECRET" ]; then
    echo "Không tìm thấy biến môi trường BINANCE_TESTNET_API_KEY hoặc BINANCE_TESTNET_API_SECRET"
    echo "Sử dụng cấu hình API từ file config"
    API_ARGS=""
else
    echo "Sử dụng API key và secret từ biến môi trường"
    API_ARGS="--api-key $BINANCE_TESTNET_API_KEY --api-secret $BINANCE_TESTNET_API_SECRET"
fi

# Kiểm tra file telegram_config.json
if [ ! -f "$ROOT_DIR/telegram_config.json" ]; then
    echo "Không tìm thấy file telegram_config.json, tạo file mặc định"
    echo '{
        "enabled": true,
        "bot_token": "",
        "chat_id": ""
    }' > "$ROOT_DIR/telegram_config.json"
fi

# Kiểm tra thư mục configs
if [ ! -d "$ROOT_DIR/configs" ]; then
    echo "Tạo thư mục configs"
    mkdir -p "$ROOT_DIR/configs"
fi

# Kiểm tra Python và các thư viện cần thiết
python -c "import schedule" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Cài đặt thư viện schedule"
    pip install schedule
fi

# Khởi động hệ thống
echo "Khởi động hệ thống giao dịch theo thời gian tối ưu..."
echo "Log được lưu tại: $LOG_FILE"
echo "Chạy lệnh với nohup để tiếp tục trong nền khi đóng terminal"
echo "Sử dụng: nohup ./start_time_based_trading.sh &"

# Chạy chương trình trong cửa sổ hiện tại
echo "Đang chạy hệ thống..."
python time_based_trading_system.py --testnet $API_ARGS --timezone 7 2>&1 | tee -a "$LOG_FILE"

# Kết thúc script
echo "Hệ thống đã dừng"
exit 0
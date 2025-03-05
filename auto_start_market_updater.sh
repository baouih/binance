#!/bin/bash

# Script tự động khởi động dịch vụ cập nhật dữ liệu thị trường
# Được thiết kế để chạy khi Replit khởi động

# Thư mục hiện tại
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Tên file PID
PID_FILE="market_updater.pid"

# Kiểm tra xem dịch vụ đã chạy chưa
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Dịch vụ cập nhật dữ liệu thị trường đã chạy với PID: $PID"
        exit 0
    else
        echo "Phát hiện file PID lỗi, đang xóa..."
        rm -f "$PID_FILE"
    fi
fi

# Khởi động dịch vụ trong nền
echo "Khởi động dịch vụ cập nhật dữ liệu thị trường..."
nohup python schedule_market_updates.py > market_scheduler_output.log 2>&1 &

# Lưu PID
echo $! > "$PID_FILE"
echo "Dịch vụ đã khởi động với PID: $(cat $PID_FILE)"

# Thiết lập quyền thực thi
chmod +x market_data_updater.py
chmod +x schedule_market_updates.py

# Chạy cập nhật ngay lập tức
echo "Đang chạy cập nhật dữ liệu thị trường ngay lập tức..."
python market_data_updater.py

echo "Hoàn thành khởi động dịch vụ cập nhật dữ liệu thị trường"
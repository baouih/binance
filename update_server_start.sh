#!/bin/bash
# Script khởi động máy chủ cập nhật

# Đường dẫn đến thư mục hiện tại
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Kiểm tra xem Python đã được cài đặt chưa
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 không được cài đặt. Vui lòng cài đặt Python 3.9+"
    exit 1
fi

# Kiểm tra và cài đặt Flask nếu cần
python3 -c "import flask" 2>/dev/null || {
    echo "Đang cài đặt Flask..."
    pip install flask
}

# Đảm bảo các thư mục cần thiết tồn tại
mkdir -p updates
mkdir -p client_logs

# Khởi động máy chủ cập nhật
echo "Đang khởi động máy chủ cập nhật..."
python3 update_server.py --init

# Ghi chú: Máy chủ sẽ tiếp tục chạy cho đến khi bạn nhấn Ctrl+C
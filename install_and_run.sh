#!/bin/bash

echo "===== CÀI ĐẶT VÀ CHẠY BOT GIAO DỊCH ====="
echo

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "Python chưa được cài đặt"
    echo "Vui lòng cài đặt Python 3.9+ để tiếp tục"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Cài đặt trên macOS: brew install python3"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Cài đặt trên Linux: sudo apt install python3 python3-pip python3-venv"
    fi
    
    exit 1
fi

# Kiểm tra phiên bản
echo "Kiểm tra phiên bản Python..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Phiên bản Python: $PYTHON_VERSION"

echo
echo "Cài đặt các thư viện cần thiết..."
python3 setup_dependencies.py

echo
echo "Thiết lập cấu hình rủi ro..."
python3 risk_level_manager.py --create-default

echo
echo "Khởi động giao diện đồ họa..."
echo "Nếu không hiển thị giao diện, hãy chạy lệnh: python3 bot_gui.py"
python3 bot_gui.py
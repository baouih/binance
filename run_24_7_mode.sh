#!/bin/bash

echo "===== CHẠY BOT CHẾ ĐỘ 24/7 ====="
echo

# Chọn mức rủi ro
echo "Chọn mức độ rủi ro:"
echo "[1] 10% (Thấp)"
echo "[2] 15% (Trung bình thấp)"
echo "[3] 20% (Trung bình)"
echo "[4] 30% (Cao)"
echo -n "Nhập lựa chọn (1-4): "
read choice

risk_level=10
if [ "$choice" = "1" ]; then risk_level=10; fi
if [ "$choice" = "2" ]; then risk_level=15; fi
if [ "$choice" = "3" ]; then risk_level=20; fi
if [ "$choice" = "4" ]; then risk_level=30; fi

echo
echo "Đã chọn mức rủi ro: ${risk_level}%"
echo

echo "Khởi động bot với Guardian..."
echo
echo "Bot sẽ tự động khởi động lại khi gặp lỗi."
echo
echo "Để dừng bot, đóng cửa sổ này hoặc nhấn Ctrl+C."
echo

python3 auto_restart_guardian.py --risk-level $risk_level
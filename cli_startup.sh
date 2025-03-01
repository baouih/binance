#!/bin/bash
# Script khởi động chương trình CLI thay vì sử dụng giao diện web

# Hiển thị banner
echo "====================================================="
echo "          BINANCE TRADING BOT - CLI MODE             "
echo "====================================================="
echo "Chuyển đổi từ web UI sang CLI để cải thiện hiệu suất"
echo "====================================================="

# Dừng các dịch vụ web đang chạy
pkill -f "gunicorn --bind 0.0.0.0:5000"
echo "[✓] Đã dừng dịch vụ web"

# Kiểm tra tham số môi trường
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
  echo "[⚠] CẢNH BÁO: Chưa cấu hình API keys Binance"
  echo "    Vui lòng kiểm tra file .env"
else
  echo "[✓] Đã tìm thấy API keys Binance"
fi

# Kiểm tra tập tin cấu hình
if [ ! -f "multi_coin_config.json" ]; then
  echo "[⚠] CẢNH BÁO: Không tìm thấy file cấu hình multi_coin_config.json"
else
  echo "[✓] Đã tìm thấy file cấu hình"
fi

# Kiểm tra bot có đang chạy không
if pgrep -f "python multi_coin_bot.py" > /dev/null; then
  echo "[✓] Bot đang chạy"
else
  echo "[i] Bot hiện không chạy"
fi

echo "====================================================="
echo "Khởi động CLI..."
echo "====================================================="

# Chạy CLI interface
python new_main.py
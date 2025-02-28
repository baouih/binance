#!/bin/bash

# Kiểm tra và khởi tạo biến môi trường
if [ ! -f .env ]; then
  echo "Tạo file .env với API keys từ biến môi trường"
  echo "BINANCE_API_KEY=$BINANCE_API_KEY" > .env
  echo "BINANCE_API_SECRET=$BINANCE_API_SECRET" >> .env
fi

# Kiểm tra và tạo thư mục logs
mkdir -p logs

# Dừng tất cả các bot đang chạy (nếu có)
pkill -f "python run_24h_live_bot.py" || true

# Chạy bot trong nohup để bot tiếp tục chạy ngay cả khi terminal đóng
nohup python run_24h_live_bot.py > logs/live_bot_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Lấy PID của tiến trình bot
BOT_PID=$!
echo "Bot giao dịch đã được khởi động với PID: $BOT_PID"
echo "Bot đang chạy trong chế độ nền và sẽ tự động huấn luyện qua đêm"
echo "Logs đang được lưu trong thư mục logs/"
echo ""
echo "Để dừng bot, chạy lệnh: kill $BOT_PID"
echo "Để xem logs theo thời gian thực, chạy lệnh: tail -f logs/live_bot_*.log"
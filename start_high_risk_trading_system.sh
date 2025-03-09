#!/bin/bash

# Script tự động khởi động hệ thống giao dịch rủi ro cao
# Bao gồm bot chính và các dịch vụ hỗ trợ
# Ngày: 9/3/2025

echo "==== BẮT ĐẦU KHỞI ĐỘNG HỆ THỐNG GIAO DỊCH RỦI RO CAO ===="
echo "$(date) - Đang khởi động hệ thống giao dịch rủi ro cao..." >> high_risk_system.log

# Kiểm tra và chuẩn bị thư mục logs nếu chưa tồn tại
mkdir -p logs

# Dừng các tiến trình đang chạy (nếu có)
echo "Đang dừng các tiến trình giao dịch trước đó (nếu có)..."
pkill -f "python run_high_risk_trading_bot.py" || true
pkill -f "python trailing_stop_scheduler.py" || true
pkill -f "python auto_sltp_manager.py" || true
pkill -f "python time_optimized_strategy.py" || true
sleep 2

# Cập nhật cấu hình tiếp theo
echo "Đang đồng bộ cấu hình tiếp theo..."
python update_risk_config.py || echo "Không thể cập nhật cấu hình"

# Khởi động trình quản lý stop loss và take profit
echo "Đang khởi động Auto SLTP Manager..."
nohup python auto_sltp_manager.py > logs/auto_sltp_manager.log 2>&1 &
echo "Auto SLTP Manager PID: $!" >> high_risk_system.log

# Khởi động trình quản lý trailing stop
echo "Đang khởi động Trailing Stop Scheduler..."
nohup python trailing_stop_scheduler.py > logs/trailing_stop_scheduler.log 2>&1 &
echo "Trailing Stop Scheduler PID: $!" >> high_risk_system.log

# Khởi động chiến lược theo thời gian
echo "Đang khởi động Time Optimized Strategy..."
nohup python time_optimized_strategy.py > logs/time_optimized_strategy.log 2>&1 &
echo "Time Optimized Strategy PID: $!" >> high_risk_system.log

# Chờ các dịch vụ khởi động
echo "Đợi 5 giây cho các dịch vụ khởi động..."
sleep 5

# Khởi động bot giao dịch rủi ro cao
echo "Đang khởi động High Risk Trading Bot..."
nohup python run_high_risk_trading_bot.py > logs/high_risk_trading_bot.log 2>&1 &
BOT_PID=$!
echo "High Risk Trading Bot PID: $BOT_PID" >> high_risk_system.log

echo "Toàn bộ hệ thống đã được khởi động!"
echo "Sử dụng 'tail -f logs/high_risk_trading_bot.log' để xem trạng thái bot"

# Ghi thông tin vào log
echo "$(date) - Hệ thống giao dịch rủi ro cao đã được khởi động với PID chính: $BOT_PID" >> high_risk_system.log
echo "==== HOÀN THÀNH KHỞI ĐỘNG HỆ THỐNG GIAO DỊCH RỦI RO CAO ===="

# Tạo một file chứa PID của tiến trình chính để dễ dàng quản lý sau này
echo $BOT_PID > high_risk_bot.pid
#!/bin/bash
# Auto-start script cho hệ thống trailing stop và take profit
# Script này sẽ được chạy tự động khi hệ thống khởi động 
# để đảm bảo các biện pháp bảo vệ luôn hoạt động

LOG_FILE="logs/auto_start_tp_protection.log"

# Đảm bảo thư mục logs tồn tại
mkdir -p logs

echo "$(date) - Bắt đầu khởi động hệ thống bảo vệ trailing stop + TP" >> $LOG_FILE

# Đảm bảo tất cả các scripts có quyền thực thi
chmod +x position_trailing_stop.py
chmod +x add_trailing_stop_to_positions.py
chmod +x trailing_stop_scheduler.py
chmod +x create_test_order_with_trailing_stop.py

# 1. Thêm trailing stop cho các vị thế hiện có (để đảm bảo không bỏ sót)
echo "$(date) - Thêm trailing stop cho các vị thế hiện có" >> $LOG_FILE
python add_trailing_stop_to_positions.py >> $LOG_FILE 2>&1

# 2. Chờ 5 giây
sleep 5

# 3. Khởi động trailing stop scheduler (quản lý và điều phối các thành phần)
echo "$(date) - Khởi động hệ thống điều phối trailing stop" >> $LOG_FILE
nohup python trailing_stop_scheduler.py schedule --schedule-interval 3600 > logs/scheduler.log 2>&1 &

# 4. Chờ 5 giây và kiểm tra trạng thái
sleep 5
echo "$(date) - Kiểm tra trạng thái hệ thống" >> $LOG_FILE
python trailing_stop_scheduler.py status >> $LOG_FILE 2>&1

echo "$(date) - Hoàn tất khởi động hệ thống bảo vệ trailing stop + TP" >> $LOG_FILE
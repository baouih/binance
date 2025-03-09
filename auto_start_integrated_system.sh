#!/bin/bash
# Script tự động khởi động toàn bộ hệ thống, bao gồm cả trailing stop
# Được thiết kế để chạy khi khởi động bot giao dịch

LOG_FILE="logs/auto_start_integrated_system.log"

# Đảm bảo thư mục logs tồn tại
mkdir -p logs

echo "$(date) - Bắt đầu khởi động hệ thống tích hợp" >> $LOG_FILE

# 1. Cấp quyền cho các scripts
chmod +x position_trailing_stop.py
chmod +x add_trailing_stop_to_positions.py
chmod +x trailing_stop_scheduler.py
chmod +x auto_start_tp_protection.sh
chmod +x monitor_trailing_stop.sh

# 2. Khởi động dịch vụ monitor
echo "$(date) - Khởi động dịch vụ giám sát" >> $LOG_FILE
nohup ./monitor_trailing_stop.sh > logs/monitor.log 2>&1 &
monitor_pid=$!
echo "Monitor PID: $monitor_pid" >> $LOG_FILE

# 3. Khởi động trailing stop và điều chỉnh TP/SL cho các vị thế hiện có
echo "$(date) - Thêm trailing stop và điều chỉnh TP/SL cho vị thế hiện có" >> $LOG_FILE
python add_trailing_stop_to_positions.py --force-update-all >> $LOG_FILE 2>&1

# 3b. Khởi động dịch vụ giám sát TP/SL liên tục
echo "$(date) - Khởi động dịch vụ giám sát TP/SL liên tục" >> $LOG_FILE
nohup python adaptive_stop_loss_manager.py --monitor > logs/adaptive_sl_monitor.log 2>&1 &
adaptive_sl_pid=$!
echo "Adaptive SL Manager PID: $adaptive_sl_pid" >> $LOG_FILE

# 4. Chờ 2 giây
sleep 2

# 5. Khởi động scheduler service
echo "$(date) - Khởi động scheduler service" >> $LOG_FILE
nohup python trailing_stop_scheduler.py schedule --schedule-interval 3600 > logs/scheduler.log 2>&1 &
scheduler_pid=$!
echo "Scheduler PID: $scheduler_pid" >> $LOG_FILE

# 6. Chờ 2 giây
sleep 2

# 7. Khởi động dịch vụ trailing stop
echo "$(date) - Khởi động dịch vụ trailing stop" >> $LOG_FILE
nohup python trailing_stop_scheduler.py start --interval 60 > logs/trailing_service.log 2>&1 &
service_start_pid=$!
echo "Service starter PID: $service_start_pid" >> $LOG_FILE

# 8. Ghi PID vào file để có thể dễ dàng dừng sau này
echo "$monitor_pid,$scheduler_pid,$service_start_pid,$adaptive_sl_pid" > integrated_system.pid
echo "$(date) - Đã lưu PID vào integrated_system.pid" >> $LOG_FILE

# 9. Kiểm tra trạng thái hệ thống
sleep 5
echo "$(date) - Kiểm tra trạng thái hệ thống" >> $LOG_FILE
python trailing_stop_scheduler.py status >> $LOG_FILE 2>&1

echo "$(date) - Đã hoàn tất khởi động hệ thống tích hợp" >> $LOG_FILE
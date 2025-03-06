#!/bin/bash

# Script khởi động hệ thống giao dịch tối ưu hóa cho tài khoản nhỏ
# Cập nhật: 2025-03-06

LOG_DIR="logs"
DATE=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/small_account_$DATE.log"

# Tạo thư mục logs nếu chưa tồn tại
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
fi

echo "===== Khởi động hệ thống tài khoản nhỏ - $(date) =====" | tee -a "$LOG_FILE"

# Kiểm tra cài đặt đòn bẩy
echo "1. Kiểm tra cài đặt đòn bẩy cho các cặp tiền ưu tiên..." | tee -a "$LOG_FILE"
python3 -c "
from small_account_monitor import SmallAccountMonitor
monitor = SmallAccountMonitor(testnet=True)
results = monitor.check_leverage_settings()
print(f'Kết quả: {results}')
" 2>&1 | tee -a "$LOG_FILE"

# Thiết lập SL/TP cho các vị thế hiện có
echo "2. Thiết lập SL/TP cho các vị thế đang mở..." | tee -a "$LOG_FILE"
python3 auto_setup_sltp.py --testnet 2>&1 | tee -a "$LOG_FILE"

# Bắt đầu giám sát tài khoản nhỏ
echo "3. Bắt đầu giám sát tài khoản nhỏ..." | tee -a "$LOG_FILE"
nohup python3 small_account_monitor.py --interval 300 --testnet > "$LOG_DIR/small_account_monitor_$DATE.log" 2>&1 &
MONITOR_PID=$!
echo "   Đã khởi động giám sát với PID: $MONITOR_PID" | tee -a "$LOG_FILE"

# Lưu PID để có thể dừng sau này
echo $MONITOR_PID > small_account_monitor.pid

echo "4. Khởi động hệ thống trailing stop..." | tee -a "$LOG_FILE"
nohup ./auto_start_trailing_stop.sh > "$LOG_DIR/trailing_stop_$DATE.log" 2>&1 &
TS_PID=$!
echo "   Đã khởi động trailing stop với PID: $TS_PID" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "===== Hệ thống tài khoản nhỏ đã khởi động xong! =====" | tee -a "$LOG_FILE"
echo "Để kiểm tra logs:" | tee -a "$LOG_FILE"
echo "- Giám sát tài khoản: tail -f $LOG_DIR/small_account_monitor_$DATE.log" | tee -a "$LOG_FILE"
echo "- Trailing stop: tail -f $LOG_DIR/trailing_stop_$DATE.log" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Để dừng hệ thống: kill \$(cat small_account_monitor.pid)" | tee -a "$LOG_FILE"

# Đặt quyền thực thi
chmod +x auto_start_trailing_stop.sh
chmod +x auto_setup_sltp.py
#!/bin/bash
# Script khởi động dịch vụ trailing stop

echo "Đang khởi động dịch vụ Trailing Stop..."

# Kiểm tra xem dịch vụ đã chạy chưa
pid=$(ps aux | grep "python position_trailing_stop.py --mode service" | grep -v grep | awk '{print $2}')

if [ ! -z "$pid" ]; then
    echo "Dịch vụ Trailing Stop đã đang chạy với PID $pid"
    exit 0
fi

# Khởi động dịch vụ
nohup python position_trailing_stop.py --mode service --interval 30 > trailing_stop_service.log 2>&1 &
new_pid=$!

echo "Đã khởi động dịch vụ Trailing Stop với PID $new_pid"
echo $new_pid > trailing_stop.pid

# Kiểm tra xem dịch vụ đã khởi động thành công chưa
sleep 2
if ps -p $new_pid > /dev/null; then
    echo "Dịch vụ đang chạy."
    echo "Log được lưu tại: trailing_stop_service.log"
else
    echo "Không thể khởi động dịch vụ. Vui lòng kiểm tra log để biết thêm chi tiết."
    exit 1
fi
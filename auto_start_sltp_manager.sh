#!/bin/bash

# Auto start SL/TP Manager - Script tự động khởi động hệ thống quản lý SL/TP

LOG_FILE="auto_sltp_manager.log"
PID_FILE="auto_sltp_manager.pid"

# Kiểm tra xem tiến trình đã chạy chưa
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        echo "Auto SL/TP Manager đã đang chạy với PID $PID"
        exit 1
    else
        echo "PID file tồn tại nhưng tiến trình không chạy. Xóa PID file cũ."
        rm $PID_FILE
    fi
fi

# Khởi động Auto SL/TP Manager trong nền
echo "Bắt đầu khởi động Auto SL/TP Manager..."
nohup python auto_sltp_manager.py --testnet --interval 60 > $LOG_FILE 2>&1 &

# Lưu PID
echo $! > $PID_FILE
echo "Auto SL/TP Manager đã được khởi động với PID $!"

# Kiểm tra trạng thái sau 5 giây
sleep 5
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        echo "Auto SL/TP Manager đang chạy bình thường."
        echo "Sử dụng 'tail -f $LOG_FILE' để theo dõi log."
    else
        echo "Auto SL/TP Manager khởi động thất bại."
        rm $PID_FILE
        exit 1
    fi
else
    echo "Không tìm thấy PID file. Khởi động thất bại."
    exit 1
fi
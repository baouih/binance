#!/bin/bash

# Script tự động theo dõi và thiết lập SL/TP cho tất cả các vị thế

# Thiết lập logging
LOG_FILE="monitor_all_positions.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "[$TIMESTAMP] Bắt đầu script theo dõi vị thế" | tee -a $LOG_FILE

# Kiểm tra lệnh BTC (chạy ngay lập tức)
echo "[$TIMESTAMP] Kiểm tra và thiết lập SL/TP cho BTC" | tee -a $LOG_FILE
python auto_btc_sltp.py --testnet

# Kiểm tra tất cả các vị thế đang mở
echo "[$TIMESTAMP] Kiểm tra và thiết lập SL/TP cho tất cả vị thế" | tee -a $LOG_FILE
python auto_setup_sltp.py --testnet

# Theo dõi các vị thế thủ công
echo "[$TIMESTAMP] Theo dõi và thiết lập SL/TP cho các vị thế thủ công" | tee -a $LOG_FILE
python auto_setup_sltp.py --testnet --track-manual

# Thiết lập cron job để chạy mỗi 5 phút nếu chưa có
if ! crontab -l | grep -q "auto_btc_sltp.py"; then
    (crontab -l 2>/dev/null; echo "*/5 * * * * cd $(pwd) && python auto_btc_sltp.py --testnet >> $LOG_FILE 2>&1") | crontab -
    echo "[$TIMESTAMP] Đã thêm cron job kiểm tra BTC mỗi 5 phút" | tee -a $LOG_FILE
fi

if ! crontab -l | grep -q "auto_setup_sltp.py"; then
    (crontab -l 2>/dev/null; echo "*/15 * * * * cd $(pwd) && python auto_setup_sltp.py --testnet >> $LOG_FILE 2>&1") | crontab -
    (crontab -l 2>/dev/null; echo "*/30 * * * * cd $(pwd) && python auto_setup_sltp.py --testnet --track-manual >> $LOG_FILE 2>&1") | crontab -
    echo "[$TIMESTAMP] Đã thêm cron job kiểm tra tất cả vị thế và vị thế thủ công" | tee -a $LOG_FILE
fi

echo "[$TIMESTAMP] Thiết lập hoàn tất. Xem log tại $LOG_FILE" | tee -a $LOG_FILE

# Khởi chạy giám sát tài khoản nhỏ
echo "[$TIMESTAMP] Khởi động giám sát tài khoản nhỏ" | tee -a $LOG_FILE
python small_account_monitor.py --testnet &
echo "[$TIMESTAMP] Đã khởi động giám sát tài khoản nhỏ" | tee -a $LOG_FILE

echo "[$TIMESTAMP] Hoàn tất thiết lập theo dõi" | tee -a $LOG_FILE
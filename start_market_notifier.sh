#!/bin/bash
# Script để khởi động dịch vụ thông báo thị trường tự động
# Tác giả: BinanceTrader Bot

# Đường dẫn tới file log
LOG_FILE="market_notifier.log"

# Kiểm tra xem dịch vụ đã chạy chưa
if [ -f "market_notifier.pid" ]; then
    PID=$(cat market_notifier.pid)
    if ps -p $PID > /dev/null; then
        echo "Dịch vụ thông báo thị trường đã đang chạy với PID $PID"
        exit 1
    else
        echo "Tìm thấy file PID nhưng process không tồn tại, xóa file PID cũ..."
        rm market_notifier.pid
    fi
fi

# Tạo file log mới nếu chưa tồn tại
if [ ! -f "$LOG_FILE" ]; then
    touch "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Tạo file log mới" >> "$LOG_FILE"
fi

# Khởi động dịch vụ trong background
echo "Đang khởi động dịch vụ thông báo thị trường..."
nohup python -c "
import time
import logging
import auto_market_notifier

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='market_notifier.log')
logger = logging.getLogger('market_notifier_starter')

try:
    # Ghi PID vào file
    import os
    with open('market_notifier.pid', 'w') as f:
        f.write(str(os.getpid()))
    
    # Khởi động dịch vụ
    logger.info('Đang khởi động dịch vụ thông báo thị trường tự động')
    notifier = auto_market_notifier.AutoMarketNotifier()
    notifier.start()
    
    # Giữ tiến trình chạy liên tục
    while True:
        time.sleep(10)
except Exception as e:
    logger.error(f'Lỗi khi chạy dịch vụ thông báo thị trường: {str(e)}')
" >> "$LOG_FILE" 2>&1 &

# Đợi một chút và kiểm tra xem dịch vụ đã chạy chưa
sleep 2
if [ -f "market_notifier.pid" ]; then
    PID=$(cat market_notifier.pid)
    if ps -p $PID > /dev/null; then
        echo "Dịch vụ thông báo thị trường đã được khởi động thành công với PID $PID"
        exit 0
    fi
fi

echo "Không thể khởi động dịch vụ thông báo thị trường, kiểm tra file log để biết chi tiết"
exit 1
#!/bin/bash

# Script tự động khởi động dịch vụ cập nhật dữ liệu thị trường
# Được chạy khi Replit khởi động và định kỳ để đảm bảo dịch vụ luôn hoạt động

# Thiết lập môi trường
export PATH=$PATH:/home/runner/.local/bin

# Đường dẫn đến log
LOG_FILE="auto_start_market_updater.log"

# Đường dẫn đến file PID
PID_FILE="market_updater.pid"
FLASK_PID_FILE="flask_app.pid"
WORKFLOW_STATUS_FILE=".replit/.workflow_running"

# Hàm kiểm tra trạng thái workflow
check_workflow() {
    if [ -f "$WORKFLOW_STATUS_FILE" ]; then
        echo "Workflow đang chạy"
        return 0
    else
        echo "Workflow không chạy"
        return 1
    fi
}

# Hàm khởi động dịch vụ
start_service() {
    echo "$(date) - Khởi động dịch vụ cập nhật dữ liệu thị trường" >> $LOG_FILE
    nohup python3 start_market_updater.py > market_updater_nohup.log 2>&1 &
    echo $! > $PID_FILE
    echo "$(date) - Dịch vụ đã được khởi động với PID $!" >> $LOG_FILE
    
    # Khởi động lại Flask app nếu không chạy
    if ! check_workflow; then
        echo "$(date) - Khởi động lại Flask app vì workflow đã dừng" >> $LOG_FILE
        nohup gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app > flask_app.log 2>&1 &
        echo $! > $FLASK_PID_FILE
        echo "$(date) - Flask app đã được khởi động với PID $!" >> $LOG_FILE
    fi
}

# Ghi log
echo "$(date) - Bắt đầu kiểm tra và khởi động dịch vụ cập nhật dữ liệu thị trường" >> $LOG_FILE

# Kiểm tra xem dịch vụ đã chạy chưa
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if kill -0 $PID 2>/dev/null; then
        echo "$(date) - Dịch vụ đã đang chạy với PID $PID" >> $LOG_FILE
        
        # Vẫn kiểm tra workflow
        if ! check_workflow; then
            echo "$(date) - Phát hiện workflow đã dừng, khởi động lại Flask app" >> $LOG_FILE
            nohup gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app > flask_app.log 2>&1 &
            echo $! > $FLASK_PID_FILE
            echo "$(date) - Flask app đã được khởi động với PID $!" >> $LOG_FILE
        fi
    else
        echo "$(date) - PID file tồn tại nhưng dịch vụ không chạy, khởi động lại dịch vụ" >> $LOG_FILE
        rm -f $PID_FILE
        start_service
    fi
else
    # Khởi động dịch vụ vì chưa chạy
    start_service
fi

# Thêm script này vào crontab để chạy định kỳ
if ! crontab -l | grep -q "auto_start_market_updater.sh"; then
    (crontab -l 2>/dev/null; echo "*/5 * * * * $(pwd)/auto_start_market_updater.sh") | crontab -
    echo "$(date) - Đã thêm script vào crontab để chạy mỗi 5 phút" >> $LOG_FILE
fi

# Thông báo ra màn hình console
echo "Dịch vụ cập nhật dữ liệu thị trường đã được khởi động và được cấu hình tự kiểm tra định kỳ."
echo "Log: tail -f market_updater_nohup.log"
echo "Flask Log: tail -f flask_app.log"
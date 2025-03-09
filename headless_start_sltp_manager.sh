#!/bin/bash
# Script khởi động headless dịch vụ Auto SLTP Manager (không yêu cầu tương tác người dùng)

LOG_FILE="auto_sltp_manager.log"
PID_FILE="auto_sltp_manager.pid"
PYTHON_SCRIPT="auto_sltp_manager.py"

# Ghi log
log() {
    echo "[$(date)] $1" >> $LOG_FILE
    echo "$1"
}

# Kiểm tra xem dịch vụ đã chạy chưa và tự động dừng nếu cần
if pgrep -f "python $PYTHON_SCRIPT" > /dev/null; then
    existing_pid=$(pgrep -f "python $PYTHON_SCRIPT")
    log "⚠️ Dịch vụ Auto SLTP Manager đã đang chạy với PID $existing_pid. Tự động dừng..."
    kill $existing_pid
    sleep 2
    
    # Kiểm tra lại và buộc dừng nếu cần
    if pgrep -f "python $PYTHON_SCRIPT" > /dev/null; then
        log "⚠️ Không thể dừng dịch vụ bình thường. Buộc dừng..."
        pkill -9 -f "python $PYTHON_SCRIPT"
        sleep 1
    fi
fi

# Kiểm tra file Python
if [ ! -f "$PYTHON_SCRIPT" ]; then
    log "❌ Không tìm thấy file $PYTHON_SCRIPT"
    exit 1
fi

# Đảm bảo file có quyền thực thi
chmod +x $PYTHON_SCRIPT

# Khởi động dịch vụ
log "🚀 Đang khởi động dịch vụ Auto SLTP Manager (chế độ headless)..."
nohup python $PYTHON_SCRIPT > $LOG_FILE 2>&1 &
new_pid=$!

# Lưu PID
echo $new_pid > $PID_FILE
log "✅ Dịch vụ Auto SLTP Manager đã được khởi động với PID $new_pid"

# Kiểm tra sau khi khởi động
sleep 2
if pgrep -f "python $PYTHON_SCRIPT" > /dev/null; then
    log "✅ Dịch vụ Auto SLTP Manager đang chạy bình thường"
    exit 0
else
    log "❌ Không thể khởi động dịch vụ Auto SLTP Manager"
    exit 1
fi
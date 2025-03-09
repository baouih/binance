#!/bin/bash
# Script khởi động dịch vụ Trailing Stop

LOG_FILE="trailing_stop_service.log"
PID_FILE="trailing_stop_service.pid"
PYTHON_SCRIPT="position_trailing_stop.py"

# Ghi log
log() {
    echo "[$(date)] $1" >> $LOG_FILE
    echo "$1"
}

# Kiểm tra xem dịch vụ đã chạy chưa
if pgrep -f "python $PYTHON_SCRIPT" > /dev/null; then
    existing_pid=$(pgrep -f "python $PYTHON_SCRIPT")
    log "⚠️ Dịch vụ Trailing Stop đã đang chạy với PID $existing_pid"
    read -p "Bạn có muốn dừng và khởi động lại dịch vụ không? (y/n): " restart
    if [ "$restart" != "y" ]; then
        log "❌ Hủy bỏ khởi động Trailing Stop"
        exit 1
    fi
    
    log "🔄 Dừng dịch vụ Trailing Stop hiện tại (PID: $existing_pid)..."
    kill $existing_pid
    sleep 2
    
    # Kiểm tra lại
    if pgrep -f "python $PYTHON_SCRIPT" > /dev/null; then
        log "⚠️ Không thể dừng dịch vụ. Thử buộc dừng..."
        kill -9 $existing_pid
        sleep 1
    fi
fi

# Kiểm tra file Python
if [ ! -f "$PYTHON_SCRIPT" ]; then
    log "❌ Không tìm thấy file $PYTHON_SCRIPT"
    exit 1
fi

# Khởi động dịch vụ
log "🚀 Đang khởi động dịch vụ Trailing Stop..."
nohup python $PYTHON_SCRIPT > $LOG_FILE 2>&1 &
new_pid=$!

# Lưu PID
echo $new_pid > $PID_FILE
log "✅ Dịch vụ Trailing Stop đã được khởi động với PID $new_pid"

# Kiểm tra sau khi khởi động
sleep 2
if pgrep -f "python $PYTHON_SCRIPT" > /dev/null; then
    log "✅ Dịch vụ Trailing Stop đang chạy bình thường"
    
    # Hiển thị cấu hình trailing stop
    echo "THÔNG TIN CẤU HÌNH:"
    python -c "
import json
try:
    with open('trailing_stop_config.json', 'r') as f:
        config = json.load(f)
    print(f\"  Kích hoạt khi: Lợi nhuận đạt {config.get('activation_percent', 'N/A')}%\")
    print(f\"  Callback: {config.get('callback_percent', 'N/A')}%\")
    print(f\"  Chu kỳ kiểm tra: {config.get('check_interval', 'N/A')} giây\")
    print(f\"  Sử dụng callback động: {'✅' if config.get('use_dynamic_activation', False) else '❌'}\")
except Exception as e:
    print(f'  Lỗi khi đọc cấu hình trailing stop: {e}')
"
else
    log "❌ Không thể khởi động dịch vụ Trailing Stop"
    exit 1
fi

# Thông báo theo dõi log
echo
echo "📝 Để theo dõi log, sử dụng lệnh:"
echo "tail -f $LOG_FILE"
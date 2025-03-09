#!/bin/bash
# Script để sửa và khởi động lại dịch vụ Trailing Stop

LOG_FILE="trailing_stop_service.log"
PID_FILE="trailing_stop_service.pid"
PYTHON_SCRIPT="position_trailing_stop.py"

# Ghi log
log() {
    echo "[$(date)] $1" >> $LOG_FILE
    echo "$1"
}

# Đảm bảo tất cả các script có quyền thực thi
log "🔧 Đang cấp quyền thực thi cho tất cả các script..."
chmod +x *.sh *.py

# Kiểm tra các tiến trình đang chạy
log "🔍 Kiểm tra và dừng các tiến trình trailing stop đang chạy..."
pkill -f "python $PYTHON_SCRIPT" || true
sleep 2

# Xóa PID file cũ nếu có
if [ -f "$PID_FILE" ]; then
    log "🗑️ Xóa PID file cũ..."
    rm -f "$PID_FILE"
fi

# Khởi tạo log file mới
log "📝 Khởi tạo log file mới..."
echo "===== $(date) - KHỞI ĐỘNG DỊCH VỤ TRAILING STOP MỚI =====" > $LOG_FILE

# Khởi động dịch vụ với mode service
log "🚀 Đang khởi động dịch vụ Trailing Stop..."
nohup python $PYTHON_SCRIPT --mode service --interval 60 >> $LOG_FILE 2>&1 &
new_pid=$!

# Lưu PID
echo $new_pid > $PID_FILE
log "✅ Dịch vụ Trailing Stop đã được khởi động với PID $new_pid"

# Kiểm tra sau khi khởi động
sleep 2
if pgrep -f "python $PYTHON_SCRIPT" > /dev/null; then
    log "✅ Dịch vụ Trailing Stop đang chạy bình thường"
    
    # Hiển thị vị thế hiện tại
    echo
    echo "VỊ THẾ ĐANG MỞ:"
    python -c "
import json
try:
    with open('active_positions.json', 'r') as f:
        positions = json.load(f)
    if positions:
        for symbol, pos in positions.items():
            print(f\"  {symbol}: {pos.get('side')} @ {pos.get('entry_price', 0):.2f}\")
            print(f\"     SL: {pos.get('stop_loss', 'N/A'):.2f}, TP: {pos.get('take_profit', 'N/A'):.2f}\")
            trailing_status = 'Đã kích hoạt' if pos.get('trailing_activated', False) else 'Chưa kích hoạt'
            print(f\"     Trailing Stop: {trailing_status}\")
    else:
        print('  Không có vị thế nào đang mở')
except Exception as e:
    print(f'  Lỗi khi đọc vị thế: {e}')
"
else
    log "❌ Không thể khởi động dịch vụ Trailing Stop"
    
    # In thông tin lỗi từ log
    echo
    echo "LỖI CUỐI CÙNG TRONG LOG:"
    tail -n 10 $LOG_FILE
    
    exit 1
fi

# Thông báo theo dõi log
echo
echo "📝 Để theo dõi log, sử dụng lệnh:"
echo "tail -f $LOG_FILE"
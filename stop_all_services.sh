#!/bin/bash
# Script dừng tất cả các dịch vụ hệ thống giao dịch

LOG_FILE="stop_services.log"

# Ghi log
log() {
    echo "[$(date)] $1" | tee -a "$LOG_FILE"
    echo "$1"
}

# Bắt đầu quá trình dừng dịch vụ
log "===== ĐANG DỪNG TẤT CẢ DỊCH VỤ ====="

# Dừng dịch vụ giao dịch chính
log "Dừng dịch vụ giao dịch chính..."
if pgrep -f "python main.py" > /dev/null; then
    pkill -f "python main.py"
    sleep 1
    if pgrep -f "python main.py" > /dev/null; then
        log "Buộc dừng dịch vụ giao dịch chính..."
        pkill -9 -f "python main.py"
    fi
    log "✅ Đã dừng dịch vụ giao dịch chính"
else
    log "✅ Dịch vụ giao dịch chính không đang chạy"
fi

# Dừng Auto SLTP Manager
log "Dừng Auto SLTP Manager..."
if pgrep -f "python auto_sltp_manager.py" > /dev/null; then
    pkill -f "python auto_sltp_manager.py"
    sleep 1
    if pgrep -f "python auto_sltp_manager.py" > /dev/null; then
        log "Buộc dừng Auto SLTP Manager..."
        pkill -9 -f "python auto_sltp_manager.py"
    fi
    log "✅ Đã dừng Auto SLTP Manager"
else
    log "✅ Auto SLTP Manager không đang chạy"
fi

# Dừng Trailing Stop Service
log "Dừng Trailing Stop Service..."
if pgrep -f "python position_trailing_stop.py" > /dev/null; then
    pkill -f "python position_trailing_stop.py"
    sleep 1
    if pgrep -f "python position_trailing_stop.py" > /dev/null; then
        log "Buộc dừng Trailing Stop Service..."
        pkill -9 -f "python position_trailing_stop.py"
    fi
    log "✅ Đã dừng Trailing Stop Service"
else
    log "✅ Trailing Stop Service không đang chạy"
fi

# Xóa các file PID nếu còn tồn tại
log "Dọn dẹp các file PID..."
rm -f auto_sltp_manager.pid trailing_stop_service.pid 2>/dev/null

# Kiểm tra lại
log "Kiểm tra lại trạng thái dịch vụ..."
if pgrep -f "python (position_trailing_stop.py|auto_sltp_manager.py|main.py)" > /dev/null; then
    log "⚠️ Một số dịch vụ vẫn đang chạy!"
    ps aux | grep -E "python (position_trailing_stop.py|auto_sltp_manager.py|main.py)" | grep -v grep
else
    log "✅ Tất cả dịch vụ đã dừng thành công"
fi

log "===== KẾT THÚC QUÁ TRÌNH DỪNG DỊCH VỤ ====="

echo
echo "===== TRẠNG THÁI DỊCH VỤ ====="
if pgrep -f "python main.py" > /dev/null; then
    echo "❌ Dịch vụ giao dịch chính: VẪN ĐANG CHẠY"
else
    echo "✅ Dịch vụ giao dịch chính: ĐÃ DỪNG"
fi

if pgrep -f "python auto_sltp_manager.py" > /dev/null; then
    echo "❌ Auto SLTP Manager: VẪN ĐANG CHẠY"
else
    echo "✅ Auto SLTP Manager: ĐÃ DỪNG"
fi

if pgrep -f "python position_trailing_stop.py" > /dev/null; then
    echo "❌ Trailing Stop Service: VẪN ĐANG CHẠY"
else
    echo "✅ Trailing Stop Service: ĐÃ DỪNG"
fi
echo
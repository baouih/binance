#!/bin/bash
# Script khởi động tự động các dịch vụ cần thiết
# Sử dụng cho môi trường server tự động khởi động

LOG_FILE="auto_startup_services.log"
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")

# Hàm ghi log
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a $LOG_FILE
}

# Bắt đầu ghi log
log "===== BẮT ĐẦU KHỞI ĐỘNG TỰ ĐỘNG DỊCH VỤ ====="
log "Thời gian bắt đầu: $START_TIME"

# Đảm bảo tất cả script có quyền thực thi
log "Đang cấp quyền thực thi cho tất cả script..."
chmod +x *.sh *.py
log "Đã cấp quyền thành công"

# 1. Kiểm tra và khởi động dịch vụ giao dịch chính
log "Kiểm tra và khởi động dịch vụ giao dịch chính..."
if pgrep -f "python main.py" > /dev/null; then
    log "✓ Dịch vụ giao dịch chính đã đang chạy"
else
    log "Khởi động dịch vụ giao dịch chính..."
    nohup python main.py > trading_service.log 2>&1 &
    sleep 3
    if pgrep -f "python main.py" > /dev/null; then
        log "✓ Dịch vụ giao dịch chính đã khởi động thành công"
    else
        log "✗ Không thể khởi động dịch vụ giao dịch chính"
    fi
fi

# 2. Kiểm tra và khởi động Auto SLTP Manager
log "Kiểm tra và khởi động Auto SLTP Manager..."
if pgrep -f "python auto_sltp_manager.py" > /dev/null; then
    log "✓ Auto SLTP Manager đã đang chạy"
else
    log "Khởi động Auto SLTP Manager..."
    ./headless_start_sltp_manager.sh
    sleep 3
    if pgrep -f "python auto_sltp_manager.py" > /dev/null; then
        log "✓ Auto SLTP Manager đã khởi động thành công"
    else
        log "✗ Không thể khởi động Auto SLTP Manager. Thử một lần nữa..."
        nohup python auto_sltp_manager.py > auto_sltp_manager.log 2>&1 &
        sleep 2
        if pgrep -f "python auto_sltp_manager.py" > /dev/null; then
            log "✓ Auto SLTP Manager đã khởi động thành công (lần thử thứ 2)"
        else
            log "✗ Không thể khởi động Auto SLTP Manager sau 2 lần thử"
        fi
    fi
fi

# 3. Kiểm tra và khởi động Trailing Stop
log "Kiểm tra và khởi động Trailing Stop Service..."
if pgrep -f "python position_trailing_stop.py" > /dev/null; then
    log "✓ Trailing Stop Service đã đang chạy"
else
    log "Khởi động Trailing Stop Service..."
    ./headless_trailing_stop.sh
    sleep 3
    if pgrep -f "python position_trailing_stop.py" > /dev/null; then
        log "✓ Trailing Stop Service đã khởi động thành công"
    else
        log "✗ Không thể khởi động Trailing Stop Service. Thử một lần nữa..."
        nohup python position_trailing_stop.py --mode service --interval 60 > trailing_stop_service.log 2>&1 &
        sleep 2
        if pgrep -f "python position_trailing_stop.py" > /dev/null; then
            log "✓ Trailing Stop Service đã khởi động thành công (lần thử thứ 2)"
        else
            log "✗ Không thể khởi động Trailing Stop Service sau 2 lần thử"
        fi
    fi
fi

# Tóm tắt trạng thái các dịch vụ
log "===== TRẠNG THÁI DỊCH VỤ ====="
LOG_TRADING=$(pgrep -f "python main.py" > /dev/null && echo "✓ Đang chạy" || echo "✗ Không chạy")
LOG_SLTP=$(pgrep -f "python auto_sltp_manager.py" > /dev/null && echo "✓ Đang chạy" || echo "✗ Không chạy")
LOG_TRAILING=$(pgrep -f "python position_trailing_stop.py" > /dev/null && echo "✓ Đang chạy" || echo "✗ Không chạy")

log "Dịch vụ giao dịch chính: $LOG_TRADING"
log "Auto SLTP Manager: $LOG_SLTP"
log "Trailing Stop Service: $LOG_TRAILING"

END_TIME=$(date +"%Y-%m-%d %H:%M:%S")
log "===== KẾT THÚC KHỞI ĐỘNG TỰ ĐỘNG ====="
log "Thời gian kết thúc: $END_TIME"

# In thông tin cho người dùng
echo
echo "===== THÔNG TIN TRẠNG THÁI DỊCH VỤ ====="
echo "Dịch vụ giao dịch chính: $LOG_TRADING"
echo "Auto SLTP Manager: $LOG_SLTP"
echo "Trailing Stop Service: $LOG_TRAILING"
echo
echo "Các dịch vụ đã được khởi động. Xem log chi tiết trong file: $LOG_FILE"
echo
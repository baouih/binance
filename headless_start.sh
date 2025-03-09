#!/bin/bash
# Script khởi động hệ thống giao dịch không cần giao diện người dùng (headless)
# Lý tưởng cho môi trường máy chủ

LOG_FILE="headless_start.log"

# Ghi log
log() {
    echo "[$(date)] $1" | tee -a $LOG_FILE
}

log "===== KHỞI ĐỘNG HỆ THỐNG GIAO DỊCH TỰ ĐỘNG ====="

# Kiểm tra xem python đã được cài đặt chưa
if ! command -v python &> /dev/null; then
    log "❌ Python chưa được cài đặt. Vui lòng cài đặt Python trước khi tiếp tục."
    exit 1
fi

# Kiểm tra file cấu hình
if [ ! -f "account_config.json" ]; then
    log "❌ Không tìm thấy file cấu hình account_config.json."
    exit 1
fi

# Kiểm tra API keys
if ! grep -q "BINANCE_TESTNET_API_KEY" .env 2>/dev/null || ! grep -q "BINANCE_TESTNET_API_SECRET" .env 2>/dev/null; then
    log "⚠️ Không tìm thấy API key hoặc Secret trong file .env!"
fi

log "✅ Kiểm tra cấu hình hoàn tất"

# Kiểm tra kết nối Binance API
log "🔍 Kiểm tra kết nối Binance API..."
API_TEST=$(python -c "
import requests
try:
    response = requests.get('https://testnet.binancefuture.com/fapi/v1/ping')
    if response.status_code == 200:
        print('success')
    else:
        print('fail')
except Exception as e:
    print('fail')
")

if [ "$API_TEST" != "success" ]; then
    log "❌ Kiểm tra kết nối Binance API thất bại. Vui lòng kiểm tra kết nối internet và API."
    exit 1
else
    log "✅ Kết nối Binance API OK"
fi

# Dừng các dịch vụ đang chạy (nếu có)
log "🔄 Tự động dừng các dịch vụ đang chạy (nếu có)..."

sltp_pid=$(pgrep -f "python auto_sltp_manager.py")
if [ ! -z "$sltp_pid" ]; then
    log "Dừng Auto SLTP Manager (PID: $sltp_pid)..."
    kill $sltp_pid 2>/dev/null
    sleep 1
fi

trailing_pid=$(pgrep -f "python position_trailing_stop.py")
if [ ! -z "$trailing_pid" ]; then
    log "Dừng Trailing Stop Service (PID: $trailing_pid)..."
    kill $trailing_pid 2>/dev/null
    sleep 1
fi

# Khởi động Auto SLTP Manager
log "🚀 Khởi động Auto SLTP Manager..."
nohup python auto_sltp_manager.py > auto_sltp_manager.log 2>&1 &
sltp_pid=$!
echo $sltp_pid > auto_sltp_manager.pid
log "✅ Auto SLTP Manager đã khởi động với PID $sltp_pid"

# Khởi động Trailing Stop Service
log "🚀 Khởi động Trailing Stop Service..."
nohup python position_trailing_stop.py > trailing_stop_service.log 2>&1 &
trailing_pid=$!
echo $trailing_pid > trailing_stop_service.pid
log "✅ Trailing Stop Service đã khởi động với PID $trailing_pid"

# Kiểm tra trạng thái sau 3 giây
sleep 3
sltp_running=$(pgrep -f "python auto_sltp_manager.py")
trailing_running=$(pgrep -f "python position_trailing_stop.py")
log "Auto SLTP Manager: $([ ! -z "$sltp_running" ] && echo "🟢 Đang chạy" || echo "🔴 Không chạy")"
log "Trailing Stop:     $([ ! -z "$trailing_running" ] && echo "🟢 Đang chạy" || echo "🔴 Không chạy")"

# Thông báo kết quả
log
log "=== TRẠNG THÁI KHỞI ĐỘNG ==="
if [ ! -z "$sltp_running" ] && [ ! -z "$trailing_running" ]; then
    log "✅ Tất cả dịch vụ đã khởi động thành công"
    
    # Cài đặt cron job kiểm tra sức khỏe nếu chưa có
    CURRENT_DIR=$(pwd)
    CRON_JOB="*/30 * * * * cd $CURRENT_DIR && ./health_check.sh > /dev/null 2>&1"
    EXISTING_CRON=$(crontab -l 2>/dev/null | grep "health_check.sh")
    if [ -z "$EXISTING_CRON" ]; then
        # Thêm cron job mới
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        log "✅ Đã cài đặt lịch kiểm tra sức khỏe tự động mỗi 30 phút"
    fi
else
    log "⚠️ Một số dịch vụ không khởi động đúng cách. Vui lòng kiểm tra logs."
fi

log
log "📊 Vị thế hiện tại:"
python -c "
import json
try:
    with open('active_positions.json', 'r') as f:
        positions = json.load(f)
    if positions:
        for symbol, pos in positions.items():
            print(f\"  {symbol}: {pos.get('side')} @ {pos.get('entry_price', 0):.2f}, SL: {pos.get('stop_loss', 'N/A'):.2f}, TP: {pos.get('take_profit', 'N/A'):.2f}\")
    else:
        print('  Không có vị thế nào đang mở')
except Exception as e:
    print(f'  Lỗi khi đọc vị thế: {e}')
" | tee -a $LOG_FILE

log
log "===== HOÀN TẤT KHỞI ĐỘNG KHÔNG GIAO DIỆN ====="
log "Vui lòng kiểm tra logs để theo dõi trạng thái hệ thống."
log "  Auto SLTP Manager: tail -f auto_sltp_manager.log"
log "  Trailing Stop:     tail -f trailing_stop_service.log"
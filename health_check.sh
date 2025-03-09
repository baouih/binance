#!/bin/bash
# Script kiểm tra sức khỏe và tự động khôi phục hệ thống giao dịch

LOG_FILE="health_check.log"
MAX_RESTARTS=5
RESTART_COUNT_FILE="restart_count.txt"

# Ghi log
log() {
    echo "[$(date)] $1" >> $LOG_FILE
    echo "$1"
}

# Khởi tạo file đếm số lần khởi động lại
if [ ! -f "$RESTART_COUNT_FILE" ]; then
    echo "0" > $RESTART_COUNT_FILE
fi

# Đọc số lần đã khởi động lại
restart_count=$(cat $RESTART_COUNT_FILE)

check_service() {
    service_name=$1
    process_pattern=$2
    start_script=$3
    
    pid=$(pgrep -f "$process_pattern")
    
    if [ -z "$pid" ]; then
        log "⚠️ $service_name không chạy. Đang khởi động lại..."
        
        if [ "$restart_count" -lt "$MAX_RESTARTS" ]; then
            bash $start_script
            sleep 3
            
            # Kiểm tra lại sau khi khởi động
            new_pid=$(pgrep -f "$process_pattern")
            if [ -z "$new_pid" ]; then
                log "❌ Không thể khởi động lại $service_name!"
            else
                log "✅ Đã khởi động lại $service_name thành công (PID: $new_pid)"
                restart_count=$((restart_count + 1))
                echo $restart_count > $RESTART_COUNT_FILE
            fi
        else
            log "❌ Đã đạt đến giới hạn khởi động lại ($MAX_RESTARTS lần). Vui lòng kiểm tra hệ thống thủ công!"
        fi
    else
        log "✅ $service_name đang hoạt động bình thường (PID: $pid)"
    fi
}

log "===== BẮT ĐẦU KIỂM TRA SỨC KHỎE HỆ THỐNG ====="

# Kiểm tra dịch vụ Auto SLTP Manager
check_service "Auto SLTP Manager" "python auto_sltp_manager.py" "auto_start_sltp_manager.sh"

# Kiểm tra dịch vụ Trailing Stop
check_service "Trailing Stop Service" "python position_trailing_stop.py" "start_trailing_stop.sh"

# Kiểm tra dịch vụ chính
main_pid=$(pgrep -f "gunicorn --bind 0.0.0.0:5000")
if [ -z "$main_pid" ]; then
    log "⚠️ Dịch vụ chính không chạy. Vui lòng khởi động lại Workflow 'Start application' trên Replit."
else
    log "✅ Dịch vụ chính đang hoạt động bình thường (PID: $main_pid)"
fi

# Kiểm tra kết nối Binance API
log "Kiểm tra kết nối Binance API..."
python -c "
import requests
try:
    response = requests.get('https://testnet.binancefuture.com/fapi/v1/ping')
    if response.status_code == 200:
        print('✅ Kết nối đến Binance API thành công')
    else:
        print('❌ Kết nối đến Binance API thất bại: Mã trạng thái ' + str(response.status_code))
except Exception as e:
    print('❌ Không thể kết nối đến Binance API: ' + str(e))
" >> $LOG_FILE

# Kiểm tra tình trạng hệ thống
log "Kiểm tra tài nguyên hệ thống..."
echo "CPU:" >> $LOG_FILE
top -b -n 1 | head -5 >> $LOG_FILE
echo "Bộ nhớ:" >> $LOG_FILE
free -h >> $LOG_FILE
echo "Dung lượng ổ đĩa:" >> $LOG_FILE
df -h . >> $LOG_FILE

log "===== KẾT THÚC KIỂM TRA SỨC KHỎE HỆ THỐNG ====="

# Thông báo kết quả
echo
echo "Quá trình kiểm tra sức khỏe đã hoàn tất. Số lần khởi động lại: $restart_count/$MAX_RESTARTS"
echo "Chi tiết log được lưu tại: $LOG_FILE"
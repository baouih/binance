#!/bin/bash
# Script khởi động dịch vụ Auto SLTP Manager

LOG_FILE="auto_sltp_manager.log"
PID_FILE="auto_sltp_manager.pid"
PYTHON_SCRIPT="auto_sltp_manager.py"

# Ghi log
log() {
    echo "[$(date)] $1" >> $LOG_FILE
    echo "$1"
}

# Kiểm tra xem dịch vụ đã chạy chưa
if pgrep -f "python $PYTHON_SCRIPT" > /dev/null; then
    existing_pid=$(pgrep -f "python $PYTHON_SCRIPT")
    log "⚠️ Dịch vụ Auto SLTP Manager đã đang chạy với PID $existing_pid"
    read -p "Bạn có muốn dừng và khởi động lại dịch vụ không? (y/n): " restart
    if [ "$restart" != "y" ]; then
        log "❌ Hủy bỏ khởi động Auto SLTP Manager"
        exit 1
    fi
    
    log "🔄 Dừng dịch vụ Auto SLTP Manager hiện tại (PID: $existing_pid)..."
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

# Khởi động dịch vụ
log "🚀 Đang khởi động dịch vụ Auto SLTP Manager..."
nohup python $PYTHON_SCRIPT > /dev/null 2>> $LOG_FILE &
new_pid=$!

# Lưu PID
echo $new_pid > $PID_FILE
log "✅ Dịch vụ Auto SLTP Manager đã được khởi động với PID $new_pid"

# Kiểm tra sau khi khởi động
sleep 2
if pgrep -f "python $PYTHON_SCRIPT" > /dev/null; then
    log "✅ Dịch vụ Auto SLTP Manager đang chạy bình thường"
    
    # Hiển thị cấu hình hiện tại
    echo "THÔNG TIN CẤU HÌNH:"
    python -c "
import json
try:
    with open('account_config.json', 'r') as f:
        config = json.load(f)
    print(f\"  Chế độ giao dịch: {config.get('trading_mode', 'N/A')}\")
    print(f\"  Stop Loss mặc định: {config.get('default_stop_loss_percent', 'N/A')}%\")
    print(f\"  Take Profit mặc định: {config.get('default_take_profit_percent', 'N/A')}%\")
    print(f\"  Chế độ đòn bẩy: {config.get('leverage_mode', 'N/A')}\")
    print(f\"  Đòn bẩy mặc định: {config.get('default_leverage', 'N/A')}x\")
except Exception as e:
    print(f'  Lỗi khi đọc cấu hình tài khoản: {e}')
"
else
    log "❌ Không thể khởi động dịch vụ Auto SLTP Manager"
    exit 1
fi

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
    else:
        print('  Không có vị thế nào đang mở')
except Exception as e:
    print(f'  Lỗi khi đọc vị thế: {e}')
"

# Thông báo theo dõi log
echo
echo "📝 Để theo dõi log, sử dụng lệnh:"
echo "tail -f $LOG_FILE"
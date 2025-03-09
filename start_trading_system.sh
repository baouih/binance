#!/bin/bash
# Script khởi động tối ưu cho hệ thống giao dịch

echo "===== HỆ THỐNG GIAO DỊCH TIỀN ĐIỆN TỬ ====="
echo "Thời gian: $(date)"
echo "========================================"

# Kiểm tra xem python đã được cài đặt chưa
if ! command -v python &> /dev/null; then
    echo "❌ Python chưa được cài đặt. Vui lòng cài đặt Python trước khi tiếp tục."
    exit 1
fi

# Kiểm tra file cấu hình
if [ ! -f "account_config.json" ]; then
    echo "❌ Không tìm thấy file cấu hình account_config.json."
    exit 1
fi

# Kiểm tra API key và Secret
if ! grep -q "BINANCE_TESTNET_API_KEY" .env 2>/dev/null || ! grep -q "BINANCE_TESTNET_API_SECRET" .env 2>/dev/null; then
    echo "⚠️ Không tìm thấy API key hoặc Secret trong file .env. Hệ thống có thể không hoạt động đúng."
fi

echo "✅ Kiểm tra hoàn tất."

# Kiểm tra các dịch vụ đang chạy
echo "🔍 Kiểm tra dịch vụ đang chạy..."

main_pid=$(pgrep -f "gunicorn --bind 0.0.0.0:5000")
sltp_pid=$(pgrep -f "python auto_sltp_manager.py")
trailing_pid=$(pgrep -f "python position_trailing_stop.py")

if [ ! -z "$main_pid" ]; then
    echo "✅ Dịch vụ chính đang chạy với PID $main_pid"
else
    echo "❌ Dịch vụ chính không chạy. Hãy bắt đầu workflow 'Start application'."
fi

# Khởi động dịch vụ Auto SLTP Manager nếu chưa chạy
if [ -z "$sltp_pid" ]; then
    echo "🚀 Khởi động Auto SLTP Manager..."
    bash auto_start_sltp_manager.sh
else
    echo "✅ Auto SLTP Manager đã đang chạy với PID $sltp_pid"
fi

# Khởi động dịch vụ Trailing Stop nếu chưa chạy
if [ -z "$trailing_pid" ]; then
    echo "🚀 Khởi động Trailing Stop Service..."
    bash start_trailing_stop.sh
else
    echo "✅ Trailing Stop Service đã đang chạy với PID $trailing_pid"
fi

sleep 2

echo
echo "===== TRẠNG THÁI HỆ THỐNG ====="

# Kiểm tra lại sau khi khởi động
main_pid=$(pgrep -f "gunicorn --bind 0.0.0.0:5000")
sltp_pid=$(pgrep -f "python auto_sltp_manager.py")
trailing_pid=$(pgrep -f "python position_trailing_stop.py")

echo "Dịch vụ chính:       $([ ! -z "$main_pid" ] && echo "🟢 Đang chạy" || echo "🔴 Không chạy")"
echo "Auto SLTP Manager:   $([ ! -z "$sltp_pid" ] && echo "🟢 Đang chạy" || echo "🔴 Không chạy")"
echo "Trailing Stop:       $([ ! -z "$trailing_pid" ] && echo "🟢 Đang chạy" || echo "🔴 Không chạy")"

echo
echo "📊 Vị thế hiện tại:"
python -c "
import json
try:
    with open('active_positions.json', 'r') as f:
        positions = json.load(f)
    if positions:
        for symbol, pos in positions.items():
            print(f\"  {symbol}: {pos.get('side')} @ {pos.get('entry_price'):.2f}, SL: {pos.get('stop_loss'):.2f}, TP: {pos.get('take_profit'):.2f}\")
    else:
        print('  Không có vị thế nào đang mở')
except Exception as e:
    print(f'  Lỗi khi đọc vị thế: {e}')
"

echo
echo "🔍 Để kiểm tra logs:"
echo "  Dịch vụ chính:     tail -f auto_trade.log"
echo "  Auto SLTP Manager: tail -f auto_sltp_manager.log" 
echo "  Trailing Stop:     tail -f trailing_stop_service.log"
echo

echo "✅ Hoàn tất kiểm tra hệ thống!"
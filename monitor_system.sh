#!/bin/bash
# Script giám sát hệ thống giao dịch

clear
echo "===== GIÁM SÁT HỆ THỐNG GIAO DỊCH ====="
echo "Thời gian cập nhật: $(date)"
echo "========================================"

# Kiểm tra các dịch vụ đang chạy
main_pid=$(pgrep -f "gunicorn --bind 0.0.0.0:5000")
sltp_pid=$(pgrep -f "python auto_sltp_manager.py")
trailing_pid=$(pgrep -f "python position_trailing_stop.py")

echo "TRẠNG THÁI DỊCH VỤ:"
echo "-------------------"
echo "Dịch vụ chính:       $([ ! -z "$main_pid" ] && echo "🟢 Đang chạy (PID: $main_pid)" || echo "🔴 Không chạy")"
echo "Auto SLTP Manager:   $([ ! -z "$sltp_pid" ] && echo "🟢 Đang chạy (PID: $sltp_pid)" || echo "🔴 Không chạy")"
echo "Trailing Stop:       $([ ! -z "$trailing_pid" ] && echo "🟢 Đang chạy (PID: $trailing_pid)" || echo "🔴 Không chạy")"

# Kiểm tra số dư tài khoản
echo
echo "SỐ DƯ TÀI KHOẢN:"
echo "---------------"
python -c "
import json
try:
    with open('account_balance.json', 'r') as f:
        data = json.load(f)
    print(f\"  Số dư: {data.get('balance', 'N/A')} USDT\")
    print(f\"  Lợi nhuận hôm nay: {data.get('profit_today', 'N/A')} USDT\")
except Exception as e:
    print(f'  Không thể đọc dữ liệu tài khoản: {e}')
"

# Hiển thị vị thế hiện tại
echo
echo "VỊ THẾ ĐANG MỞ:"
echo "---------------"
python -c "
import json
try:
    with open('active_positions.json', 'r') as f:
        positions = json.load(f)
    if positions:
        count = 0
        for symbol, pos in positions.items():
            count += 1
            entry = pos.get('entry_price', 0)
            current = pos.get('current_price', 0)
            profit = pos.get('profit_percent', 0)
            
            # Biểu tượng tương ứng với lợi nhuận
            icon = '🟢' if profit > 0 else '🔴' if profit < 0 else '⚪'
            
            print(f\"  {icon} {symbol}: {pos.get('side')} @ {entry:.2f}, Hiện tại: {current:.2f}\")
            print(f\"     SL: {pos.get('stop_loss', 'N/A'):.2f}, TP: {pos.get('take_profit', 'N/A'):.2f}, Lợi nhuận: {profit:.2f}%\")
            print(f\"     Trailing kích hoạt: {'✅' if pos.get('trailing_activated', False) else '❌'}\")
            
        if count == 0:
            print('  Không có vị thế nào đang mở')
    else:
        print('  Không có vị thế nào đang mở')
except Exception as e:
    print(f'  Lỗi khi đọc vị thế: {e}')
"

# Kiểm tra thông tin trailing stop
echo
echo "THÔNG TIN TRAILING STOP:"
echo "------------------------"
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

# Hiển thị thông tin giao dịch gần đây
echo
echo "GIAO DỊCH GẦN ĐÂY:"
echo "-----------------"
python -c "
import json, datetime
try:
    with open('trading_history.json', 'r') as f:
        history = json.load(f)
    
    # Giới hạn hiển thị 5 giao dịch gần nhất
    count = 0
    for trade in sorted(history, key=lambda x: x.get('exit_time', ''), reverse=True):
        if count >= 5:
            break
        
        symbol = trade.get('symbol', 'N/A')
        side = trade.get('side', 'N/A')
        profit = trade.get('profit_percent', 0)
        exit_time = trade.get('exit_time', 'N/A')
        
        # Biểu tượng tương ứng với lợi nhuận
        icon = '🟢' if profit > 0 else '🔴' if profit < 0 else '⚪'
        
        print(f\"  {icon} {symbol}: {side}, Lợi nhuận: {profit:.2f}%, Đóng lúc: {exit_time}\")
        count += 1
    
    if count == 0:
        print('  Không có dữ liệu giao dịch gần đây')
except Exception as e:
    print(f'  Không thể đọc lịch sử giao dịch: {e}')
"

echo
echo "MENU THAO TÁC:"
echo "-------------"
echo "1. Khởi động lại Auto SLTP Manager"
echo "2. Khởi động lại Trailing Stop Service"
echo "3. Theo dõi log Auto SLTP Manager"
echo "4. Theo dõi log Trailing Stop"
echo "5. Kiểm tra sức khỏe hệ thống"
echo "6. Cập nhật thông tin"
echo "7. Thoát"
echo

# Hiển thị thông tin thêm
echo "BÁO CÁO HOẠT ĐỘNG:"
echo "-----------------"
echo "Auto SLTP Manager: $([ -f "auto_sltp_manager.log" ] && tail -n 1 auto_sltp_manager.log || echo "Không có log")"
echo "Trailing Stop: $([ -f "trailing_stop_service.log" ] && tail -n 1 trailing_stop_service.log || echo "Không có log")"
echo

read -p "Chọn hành động (1-7): " choice

case $choice in
    1)
        echo "Đang khởi động lại Auto SLTP Manager..."
        bash auto_start_sltp_manager.sh
        ;;
    2)
        echo "Đang khởi động lại Trailing Stop Service..."
        bash start_trailing_stop.sh
        ;;
    3)
        echo "Đang theo dõi log Auto SLTP Manager (Ctrl+C để thoát)..."
        tail -f auto_sltp_manager.log
        ;;
    4)
        echo "Đang theo dõi log Trailing Stop (Ctrl+C để thoát)..."
        tail -f trailing_stop_service.log
        ;;
    5)
        echo "Kiểm tra sức khỏe hệ thống..."
        echo "CPU:"
        top -b -n 1 | grep -E 'python|gunicorn' | head -5
        echo "Bộ nhớ:"
        free -h
        echo "Dung lượng ổ đĩa:"
        df -h .
        ;;
    6)
        echo "Đang cập nhật lại thông tin..."
        bash monitor_system.sh
        exit 0
        ;;
    7)
        echo "Thoát khỏi giám sát."
        exit 0
        ;;
    *)
        echo "Lựa chọn không hợp lệ."
        ;;
esac
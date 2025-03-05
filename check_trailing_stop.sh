#!/bin/bash
# Script kiểm tra thủ công trạng thái trailing stop

echo "=== KIỂM TRA DỊCH VỤ TRAILING STOP ==="
echo "Thời gian: $(date)"
echo "---------------------------------------"

# Kiểm tra xem dịch vụ có đang chạy không
pid=$(ps aux | grep "python position_trailing_stop.py --mode service" | grep -v grep | awk '{print $2}')

if [ -z "$pid" ]; then
    echo "CẢNH BÁO: Dịch vụ Trailing Stop KHÔNG ĐANG CHẠY!"
    echo "Gõ lệnh sau để khởi động dịch vụ:"
    echo "  ./start_trailing_stop.sh"
else
    echo "Dịch vụ Trailing Stop đang chạy với PID $pid"
    
    # Hiển thị 10 dòng log gần nhất
    echo ""
    echo "=== LOG GẦN ĐÂY ==="
    tail -n 10 trailing_stop_service.log
fi

echo ""
echo "=== VỊ THẾ ĐANG THEO DÕI ==="
python position_trailing_stop.py --mode check

echo ""
echo "=== TRẠNG THÁI DỊCH VỤ GIÁM SÁT ==="
if ps aux | grep -q "monitor_trailing_stop.sh"; then
    echo "Dịch vụ giám sát đang hoạt động"
    tail -n 5 trailing_stop_monitor.log
else
    echo "CẢNH BÁO: Dịch vụ giám sát KHÔNG ĐANG CHẠY!"
    echo "Gõ lệnh sau để khởi động dịch vụ giám sát:"
    echo "  nohup ./monitor_trailing_stop.sh > monitor.log 2>&1 &"
fi
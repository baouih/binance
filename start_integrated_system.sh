#!/bin/bash
# Script khởi động hệ thống tích hợp quản lý rủi ro và trailing stop

LOG_FILE="integrated_system.log"

echo "Đang khởi động hệ thống tích hợp quản lý rủi ro và trailing stop..."

# Tắt các dịch vụ cũ nếu đang chạy
echo "Kiểm tra và tắt các dịch vụ cũ..."
pid_trailing=$(ps aux | grep "python position_trailing_stop.py --mode service" | grep -v grep | awk '{print $2}')
if [ ! -z "$pid_trailing" ]; then
    echo "Tắt dịch vụ trailing stop cũ (PID: $pid_trailing)..."
    kill -9 $pid_trailing
    sleep 2
fi

# Kiểm tra các module cần thiết
if [ ! -f "integrated_risk_trailing_system.py" ]; then
    echo "CẢNH BÁO: Không tìm thấy file integrated_risk_trailing_system.py"
    exit 1
fi

# Đồng bộ hóa với Binance trước khi khởi động
echo "Đồng bộ hóa SL/TP với Binance trước khi khởi động dịch vụ..."
python integrated_risk_trailing_system.py --mode sync

# Kiểm tra kết quả đồng bộ
if [ $? -eq 0 ]; then
    echo "✅ Đồng bộ SL/TP với Binance thành công!"
else
    echo "⚠️ Cảnh báo: Có lỗi khi đồng bộ SL/TP với Binance, nhưng tiếp tục khởi động dịch vụ..."
fi

# Khởi động hệ thống tích hợp
echo "Khởi động hệ thống tích hợp..."
nohup python integrated_risk_trailing_system.py --mode service --interval 30 > $LOG_FILE 2>&1 &
pid_integrated=$!

sleep 2

# Kiểm tra xem đã khởi động thành công chưa
if ps -p $pid_integrated > /dev/null; then
    echo "Đã khởi động hệ thống tích hợp với PID $pid_integrated"
    echo "Dịch vụ đang chạy."
    echo "Log được lưu tại: $LOG_FILE"
else
    echo "CẢNH BÁO: Không thể khởi động hệ thống tích hợp!"
    exit 1
fi
#!/bin/bash
# Script khởi động tất cả các dịch vụ bot
echo "Khởi động tất cả dịch vụ bot..."

# Kiểm tra và tạo thư mục logs nếu chưa tồn tại
if [ ! -d "logs" ]; then
  mkdir -p logs
  echo "Đã tạo thư mục logs"
fi

# Khởi động dịch vụ keep-alive
echo "Khởi động dịch vụ keep-alive..."
nohup python setup_always_on.py > logs/keep_alive.log 2>&1 &
KEEP_ALIVE_PID=$!
echo "Dịch vụ keep-alive đã khởi động với PID: $KEEP_ALIVE_PID"
echo $KEEP_ALIVE_PID > keep_alive.pid

# Đợi 3 giây để dịch vụ khởi động
sleep 3

# Kiểm tra xem dịch vụ có đang chạy không
if curl -s http://localhost:8080/status > /dev/null; then
  echo "Dịch vụ keep-alive đang hoạt động bình thường trên cổng 8080"
else
  echo "Không thể kết nối đến dịch vụ keep-alive. Vui lòng kiểm tra logs/keep_alive.log"
fi

# Khởi động dịch vụ trailing stop
echo "Khởi động dịch vụ trailing stop..."
nohup python position_trailing_stop.py --mode service --interval 60 > logs/trailing_stop.log 2>&1 &
TRAILING_STOP_PID=$!
echo "Dịch vụ trailing stop đã khởi động với PID: $TRAILING_STOP_PID"
echo $TRAILING_STOP_PID > trailing_stop.pid

# Hiển thị trạng thái các dịch vụ đang chạy
echo ""
echo "Các dịch vụ đang chạy:"
echo "- Keep-alive: PID $KEEP_ALIVE_PID, cổng 8080"
echo "- Trailing stop: PID $TRAILING_STOP_PID"
echo ""
echo "Để theo dõi logs:"
echo "- Keep-alive: tail -f logs/keep_alive.log"
echo "- Trailing stop: tail -f logs/trailing_stop.log"
echo ""
echo "Để kiểm tra trạng thái vị thế hiện tại:"
echo "python position_trailing_stop.py --mode check"
echo ""
echo "Để dừng các dịch vụ:"
echo "./stop_bot_services.sh"

# Kiểm tra trạng thái vị thế hiện tại để xác nhận hệ thống hoạt động
echo ""
echo "Kiểm tra trạng thái vị thế hiện tại..."
python position_trailing_stop.py --mode check
#!/bin/bash
# Script khởi động dịch vụ thông báo thị trường
# Sử dụng: ./start_market_notifier.sh

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Dòng tiêu đề
echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}    Khởi động Thông báo Thị trường    ${NC}"
echo -e "${BLUE}=======================================${NC}"

# Kiểm tra xem dịch vụ đã chạy chưa
if [ -f "market_notifier.pid" ]; then
    PID=$(cat market_notifier.pid)
    if ps -p $PID > /dev/null; then
        echo -e "${YELLOW}[CẢNH BÁO] Dịch vụ thông báo thị trường đã đang chạy với PID ${PID}${NC}"
        echo -e "${YELLOW}Sử dụng './stop_market_notifier.sh' để dừng dịch vụ hiện tại trước khi khởi động lại${NC}"
        exit 1
    else
        echo -e "${YELLOW}[CẢNH BÁO] Phát hiện file PID cũ, nhưng process không còn chạy${NC}"
        echo -e "${YELLOW}Đang xóa file PID cũ...${NC}"
        rm market_notifier.pid
    fi
fi

# Kiểm tra xem file Python đã tồn tại chưa
if [ ! -f "auto_market_notifier.py" ]; then
    echo -e "${RED}[LỖI] Không tìm thấy file auto_market_notifier.py${NC}"
    echo -e "${RED}Vui lòng kiểm tra đường dẫn và đảm bảo file tồn tại${NC}"
    exit 1
fi

# Khởi động dịch vụ
echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] Đang khởi động dịch vụ thông báo thị trường...${NC}"

# Chạy script Python trong nền
nohup python auto_market_notifier.py > market_notifier.log 2>&1 &
PID=$!

# Ghi PID vào file
echo $PID > market_notifier.pid
echo -e "${GREEN}[THÀNH CÔNG] Dịch vụ thông báo thị trường đã được khởi động với PID ${PID}${NC}"
echo -e "${BLUE}Nhật ký dịch vụ được ghi vào file market_notifier.log${NC}"
echo -e "${YELLOW}Sử dụng './monitor_service_continuity.sh' để giám sát dịch vụ tự động${NC}"
echo -e "${BLUE}---------------------------------------${NC}"
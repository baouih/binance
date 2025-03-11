#!/bin/bash
# Script khởi động dịch vụ giao dịch hợp nhất
# Giảm tải hệ thống bằng cách chạy một process duy nhất thay vì nhiều dịch vụ riêng biệt

LOG_FILE="unified_service.log"
SCRIPT="unified_trading_service.py"
PID_FILE="unified_trading_service.pid"

# Màu sắc cho terminal
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Đang khởi động Dịch vụ Giao dịch Hợp nhất...${NC}"

# Kiểm tra xem script tồn tại không
if [ ! -f "$SCRIPT" ]; then
    echo -e "${RED}❌ Không tìm thấy script $SCRIPT${NC}"
    exit 1
fi

# Đảm bảo script có quyền thực thi
chmod +x $SCRIPT

# Kiểm tra xem dịch vụ đã chạy chưa
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        echo -e "${YELLOW}⚠️ Dịch vụ đã đang chạy với PID $PID${NC}"
        echo -e "${YELLOW}Đang dừng dịch vụ hiện tại...${NC}"
        kill $PID
        sleep 3
    else
        echo -e "${YELLOW}⚠️ Tìm thấy PID file cũ, nhưng process không còn chạy.${NC}"
        echo -e "${YELLOW}Đang xóa PID file cũ...${NC}"
    fi
    rm -f $PID_FILE
fi

# Khởi động dịch vụ hợp nhất
echo -e "${GREEN}Khởi động dịch vụ mới...${NC}"
nohup python $SCRIPT > $LOG_FILE 2>&1 &

# Kiểm tra xem đã khởi động thành công chưa
sleep 3
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        echo -e "${GREEN}✅ Dịch vụ Giao dịch Hợp nhất đã khởi động thành công với PID $PID${NC}"
        echo -e "${GREEN}Log file: $LOG_FILE${NC}"
        echo -e "${YELLOW}Sử dụng lệnh sau để theo dõi log:${NC}"
        echo -e "${YELLOW}  tail -f $LOG_FILE${NC}"
        exit 0
    fi
fi

echo -e "${RED}❌ Không thể khởi động dịch vụ hoặc lấy PID${NC}"
echo -e "${YELLOW}Vui lòng kiểm tra $LOG_FILE để biết thêm chi tiết${NC}"
exit 1
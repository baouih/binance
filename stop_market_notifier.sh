#!/bin/bash
# Script dừng dịch vụ thông báo thị trường
# Sử dụng: ./stop_market_notifier.sh

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Dòng tiêu đề
echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}    Dừng Dịch vụ Thông báo Thị trường    ${NC}"
echo -e "${BLUE}=======================================${NC}"

# Kiểm tra xem file PID có tồn tại không
if [ ! -f "market_notifier.pid" ]; then
    echo -e "${YELLOW}[CẢNH BÁO] Không tìm thấy file PID của dịch vụ thông báo thị trường${NC}"
    
    # Kiểm tra xem có process đang chạy không
    PROCESS_PID=$(ps aux | grep "python auto_market_notifier.py" | grep -v grep | awk '{print $2}')
    
    if [ -n "$PROCESS_PID" ]; then
        echo -e "${YELLOW}Tìm thấy process dịch vụ thông báo thị trường đang chạy với PID ${PROCESS_PID}${NC}"
        
        # Thử dừng process
        kill $PROCESS_PID
        echo -e "${GREEN}Đã gửi tín hiệu dừng đến process PID ${PROCESS_PID}${NC}"
        
        # Đợi và kiểm tra lại
        sleep 2
        if ps -p $PROCESS_PID > /dev/null; then
            echo -e "${YELLOW}Process vẫn đang chạy, thử dừng mạnh...${NC}"
            kill -9 $PROCESS_PID
            echo -e "${GREEN}Đã gửi tín hiệu dừng mạnh đến process PID ${PROCESS_PID}${NC}"
        else
            echo -e "${GREEN}[THÀNH CÔNG] Process đã được dừng thành công${NC}"
        fi
    else
        echo -e "${RED}Không tìm thấy process dịch vụ thông báo thị trường đang chạy${NC}"
        exit 1
    fi
else
    # Đọc PID từ file
    PID=$(cat market_notifier.pid)
    
    # Kiểm tra xem process có đang chạy không
    if ps -p $PID > /dev/null; then
        echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] Đang dừng dịch vụ thông báo thị trường với PID ${PID}...${NC}"
        
        # Gửi tín hiệu dừng
        kill $PID
        
        # Đợi và kiểm tra lại
        sleep 2
        if ps -p $PID > /dev/null; then
            echo -e "${YELLOW}Process vẫn đang chạy, thử dừng mạnh...${NC}"
            kill -9 $PID
            sleep 1
        fi
        
        # Kiểm tra lại lần cuối
        if ! ps -p $PID > /dev/null; then
            echo -e "${GREEN}[THÀNH CÔNG] Dịch vụ thông báo thị trường đã được dừng thành công${NC}"
        else
            echo -e "${RED}[LỖI] Không thể dừng dịch vụ thông báo thị trường${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}[CẢNH BÁO] Process với PID ${PID} không còn chạy${NC}"
    fi
    
    # Xóa file PID
    rm market_notifier.pid
    echo -e "${BLUE}Đã xóa file PID${NC}"
fi

echo -e "${BLUE}---------------------------------------${NC}"
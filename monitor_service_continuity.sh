#!/bin/bash
# Script để giám sát và duy trì liên tục các dịch vụ
# Sử dụng: ./monitor_service_continuity.sh

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Dòng tiêu đề
echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}       Giám sát Liên tục Dịch vụ       ${NC}"
echo -e "${BLUE}=======================================${NC}"

# Kiểm tra dịch vụ thông báo thị trường
check_market_notifier() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] Kiểm tra dịch vụ thông báo thị trường...${NC}"
    
    # Thực hiện kiểm tra thông qua script Python kiểm tra
    NOTIFIER_STATUS=$(python check_market_notifier.py | grep -o '"running": true' || echo "")
    
    if [ -z "$NOTIFIER_STATUS" ]; then
        echo -e "${RED}[CẢNH BÁO] Dịch vụ thông báo thị trường không hoạt động!${NC}"
        
        # Kiểm tra file PID
        if [ -f "market_notifier.pid" ]; then
            PID=$(cat market_notifier.pid)
            if ps -p $PID > /dev/null; then
                echo -e "${YELLOW}Dịch vụ có PID $PID nhưng không phản hồi, thử dừng...${NC}"
                kill $PID
                sleep 2
                if ps -p $PID > /dev/null; then
                    echo -e "${RED}Không thể dừng process, thử kill -9...${NC}"
                    kill -9 $PID
                    sleep 1
                fi
            fi
            rm market_notifier.pid
        fi
        
        # Khởi động lại dịch vụ
        echo -e "${YELLOW}Khởi động lại dịch vụ thông báo thị trường...${NC}"
        ./start_market_notifier.sh
        echo -e "${GREEN}Dịch vụ thông báo thị trường đã được khởi động lại${NC}"
    else
        echo -e "${GREEN}Dịch vụ thông báo thị trường đang hoạt động bình thường${NC}"
    fi
}

# Kiểm tra dịch vụ hợp nhất
check_unified_service() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] Kiểm tra dịch vụ hợp nhất...${NC}"
    
    # Kiểm tra file PID
    if [ -f "unified_trading_service.pid" ]; then
        PID=$(cat unified_trading_service.pid)
        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}Dịch vụ hợp nhất đang hoạt động bình thường (PID: $PID)${NC}"
        else
            echo -e "${RED}[CẢNH BÁO] Dịch vụ hợp nhất có PID $PID nhưng không còn chạy!${NC}"
            rm unified_trading_service.pid
            
            # Khởi động lại dịch vụ
            echo -e "${YELLOW}Khởi động lại dịch vụ hợp nhất...${NC}"
            ./start_unified_service.sh
            echo -e "${GREEN}Dịch vụ hợp nhất đã được khởi động lại${NC}"
        fi
    else
        echo -e "${RED}[CẢNH BÁO] Không tìm thấy file PID của dịch vụ hợp nhất!${NC}"
        
        # Kiểm tra xem có process đang chạy không
        PID=$(ps aux | grep "[u]nified_trading_service.py" | awk '{print $2}')
        if [ -n "$PID" ]; then
            echo -e "${YELLOW}Tìm thấy process dịch vụ hợp nhất đang chạy với PID $PID nhưng không có file PID${NC}"
            echo $PID > unified_trading_service.pid
            echo -e "${GREEN}Đã tạo file PID mới${NC}"
        else
            # Khởi động dịch vụ
            echo -e "${YELLOW}Khởi động dịch vụ hợp nhất...${NC}"
            ./start_unified_service.sh
            echo -e "${GREEN}Dịch vụ hợp nhất đã được khởi động${NC}"
        fi
    fi
}

# Ghi log
log_status() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Kiểm tra dịch vụ thực hiện: status thông báo thị trường=$1, status dịch vụ hợp nhất=$2" >> service_monitor.log
}

# Chạy vòng lặp chính để giám sát dịch vụ
echo -e "${GREEN}[THÔNG BÁO] Bắt đầu giám sát dịch vụ...${NC}"
echo -e "${GREEN}[THÔNG BÁO] Nhấn Ctrl+C để dừng${NC}"

while true; do
    # Kiểm tra các dịch vụ
    MARKET_NOTIFIER_OK=0
    UNIFIED_SERVICE_OK=0
    
    # Kiểm tra dịch vụ thông báo thị trường
    if python check_market_notifier.py | grep -q '"running": true'; then
        MARKET_NOTIFIER_OK=1
    else
        check_market_notifier
    fi
    
    # Kiểm tra dịch vụ hợp nhất
    if [ -f "unified_trading_service.pid" ]; then
        PID=$(cat unified_trading_service.pid)
        if ps -p $PID > /dev/null; then
            UNIFIED_SERVICE_OK=1
        else
            check_unified_service
        fi
    else
        check_unified_service
    fi
    
    # Ghi log
    log_status $MARKET_NOTIFIER_OK $UNIFIED_SERVICE_OK
    
    # Hiển thị phần tách
    echo -e "${BLUE}---------------------------------------${NC}"
    
    # Chờ 60 giây trước khi kiểm tra lại
    sleep 60
done
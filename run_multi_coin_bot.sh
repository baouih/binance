#!/bin/bash

# Script để khởi chạy bot giao dịch đa đồng tiền với CLI Controller

# Màu sắc cho đầu ra
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # Không màu

# Hiển thị tiêu đề
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}    BINANCE FUTURES TRADING BOT      ${NC}"
echo -e "${BLUE}======================================${NC}"
echo -e "${CYAN}    Multi-Coin Bot CLI Controller    ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Kiểm tra xem CLI Controller đã cài đặt chưa
if [ ! -f "cli_controller.py" ]; then
    echo -e "${RED}CLI Controller chưa được cài đặt. Vui lòng tải về và cài đặt trước.${NC}"
    exit 1
fi

# Kiểm tra quyền thực thi
if [ ! -x "cli_controller.py" ]; then
    echo -e "${YELLOW}Thiết lập quyền thực thi cho CLI Controller...${NC}"
    chmod +x cli_controller.py
fi

# Kiểm tra xem Python đã được cài đặt chưa
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Lỗi: Python3 chưa được cài đặt.${NC}"
    exit 1
fi

# Chức năng để khởi động CLI Controller
start_cli_controller() {
    echo -e "${GREEN}Khởi động CLI Controller...${NC}"
    ./cli_controller.py
}

# Chức năng để khởi động bot trực tiếp
start_bot_directly() {
    echo -e "${GREEN}Khởi động bot trực tiếp...${NC}"
    python3 multi_coin_bot.py
}

# Hiển thị menu
show_menu() {
    echo -e "\n${CYAN}Chọn hành động:${NC}"
    echo -e "${CYAN}1. Khởi động CLI Controller (Khuyến nghị)${NC}"
    echo -e "${CYAN}2. Khởi động bot trực tiếp${NC}"
    echo -e "${CYAN}3. Xem hướng dẫn sử dụng${NC}"
    echo -e "${CYAN}4. Thoát${NC}"
    echo -e "\n${CYAN}Nhập lựa chọn của bạn:${NC} \c"
}

# Hiển thị hướng dẫn
show_help() {
    echo -e "\n${BLUE}==== HƯỚNG DẪN SỬ DỤNG BOT TRADING ====${NC}"
    echo -e "\n${CYAN}CLI Controller là giao diện dòng lệnh để điều khiển bot.${NC}"
    echo -e "${CYAN}Với CLI Controller, bạn có thể:${NC}"
    echo -e "  ${GREEN}- Khởi động/dừng/khởi động lại bot${NC}"
    echo -e "  ${GREEN}- Xem trạng thái hệ thống${NC}"
    echo -e "  ${GREEN}- Xem cấu hình hiện tại${NC}"
    echo -e "  ${GREEN}- Xem giao dịch gần đây${NC}"
    echo -e "  ${GREEN}- Xem log gần đây${NC}"
    
    echo -e "\n${CYAN}Cấu hình bot nằm trong file:${NC}"
    echo -e "  ${GREEN}- multi_coin_config.json${NC} - Cấu hình cặp giao dịch, chiến lược, timeframe"
    echo -e "  ${GREEN}- .env${NC} - Cấu hình API key, thông báo, và các biến môi trường"
    
    echo -e "\n${CYAN}File log quan trọng:${NC}"
    echo -e "  ${GREEN}- trading_bot.log${NC} - Log hoạt động của bot"
    echo -e "  ${GREEN}- cli_controller.log${NC} - Log của CLI Controller"
    
    echo -e "\n${CYAN}Biến môi trường quan trọng trong .env:${NC}"
    echo -e "  ${GREEN}- AUTO_START_BOT=true/false${NC} - Tự động khởi động bot khi chạy"
    echo -e "  ${GREEN}- AUTO_RESTART_BOT=true/false${NC} - Tự động khởi động lại bot khi gặp lỗi"
    echo -e "  ${GREEN}- TELEGRAM_BOT_TOKEN=${NC} - Token của bot Telegram"
    echo -e "  ${GREEN}- TELEGRAM_CHAT_ID=${NC} - ID chat Telegram để nhận thông báo"
    
    echo -e "\n${YELLOW}Lưu ý: Môi trường thử nghiệm không khởi động bot tự động.${NC}"
    echo -e "${YELLOW}Chỉ bật AUTO_START_BOT=true khi triển khai thực tế.${NC}\n"
}

# Vòng lặp chính
while true; do
    show_menu
    read choice
    
    case $choice in
        1) 
            start_cli_controller
            exit 0
            ;;
        2) 
            start_bot_directly
            exit 0
            ;;
        3)
            show_help
            ;;
        4) 
            echo -e "${GREEN}Tạm biệt!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Lựa chọn không hợp lệ. Vui lòng thử lại.${NC}"
            ;;
    esac
done
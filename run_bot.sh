#!/bin/bash

# Script để khởi chạy trading bot với các cấu hình khác nhau

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
echo -e "${YELLOW}Chú ý: Sử dụng CLI Controller cho giao diện điều khiển ổn định hơn.${NC}"
echo -e "${YELLOW}Nhập lệnh ./cli_controller.py hoặc python cli_controller.py${NC}"

# Kiểm tra xem Python đã được cài đặt chưa
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Lỗi: Python3 chưa được cài đặt.${NC}"
    exit 1
fi

# Kiểm tra tệp .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}Cảnh báo: Tệp .env không tồn tại. Tạo tệp .env mới.${NC}"
    touch .env
    echo "# API keys cho Binance" >> .env
    echo "BINANCE_API_KEY=" >> .env
    echo "BINANCE_API_SECRET=" >> .env
    echo -e "${YELLOW}Vui lòng chỉnh sửa tệp .env và thêm API keys (nếu cần).${NC}"
fi

# Kiểm tra thư mục models
if [ ! -d "models" ]; then
    echo -e "${YELLOW}Thư mục models không tồn tại. Tạo thư mục...${NC}"
    mkdir -p models
fi

# Hiển thị menu
show_menu() {
    echo -e "\n${CYAN}Chọn chế độ chạy:${NC}"
    echo -e "${CYAN}1. Chạy bot với chiến lược Auto (mặc định)${NC}"
    echo -e "${CYAN}2. Chạy bot với chiến lược ML${NC}"
    echo -e "${CYAN}3. Chạy bot với chiến lược Advanced ML${NC}"
    echo -e "${CYAN}4. Chạy bot với cấu hình từ tệp${NC}"
    echo -e "${CYAN}5. Huấn luyện mô hình ML${NC}"
    echo -e "${CYAN}6. Chạy test Advanced ML${NC}"
    echo -e "${CYAN}7. Chạy Web UI${NC}"
    echo -e "${CYAN}8. Thoát${NC}"
    echo -e "\n${CYAN}Nhập lựa chọn của bạn:${NC} \c"
}

# Chạy bot với chiến lược Auto
run_auto_strategy() {
    symbol="BTCUSDT"
    interval="1h"
    
    echo -e "${GREEN}Nhập cặp giao dịch (mặc định: BTCUSDT):${NC} \c"
    read input_symbol
    if [ ! -z "$input_symbol" ]; then
        symbol=$input_symbol
    fi
    
    echo -e "${GREEN}Nhập khung thời gian (mặc định: 1h):${NC} \c"
    read input_interval
    if [ ! -z "$input_interval" ]; then
        interval=$input_interval
    fi
    
    echo -e "${YELLOW}Chạy bot với chiến lược Auto cho cặp $symbol, khung thời gian $interval...${NC}"
    python3 trading_bot_run.py --symbol $symbol --interval $interval --strategy auto
}

# Chạy bot với chiến lược ML
run_ml_strategy() {
    symbol="BTCUSDT"
    interval="1h"
    
    echo -e "${GREEN}Nhập cặp giao dịch (mặc định: BTCUSDT):${NC} \c"
    read input_symbol
    if [ ! -z "$input_symbol" ]; then
        symbol=$input_symbol
    fi
    
    echo -e "${GREEN}Nhập khung thời gian (mặc định: 1h):${NC} \c"
    read input_interval
    if [ ! -z "$input_interval" ]; then
        interval=$input_interval
    fi
    
    echo -e "${YELLOW}Chạy bot với chiến lược ML cho cặp $symbol, khung thời gian $interval...${NC}"
    python3 trading_bot_run.py --symbol $symbol --interval $interval --strategy ml
}

# Chạy bot với chiến lược Advanced ML
run_advanced_ml_strategy() {
    symbol="BTCUSDT"
    interval="1h"
    
    echo -e "${GREEN}Nhập cặp giao dịch (mặc định: BTCUSDT):${NC} \c"
    read input_symbol
    if [ ! -z "$input_symbol" ]; then
        symbol=$input_symbol
    fi
    
    echo -e "${GREEN}Nhập khung thời gian (mặc định: 1h):${NC} \c"
    read input_interval
    if [ ! -z "$input_interval" ]; then
        interval=$input_interval
    fi
    
    echo -e "${YELLOW}Chạy bot với chiến lược Advanced ML cho cặp $symbol, khung thời gian $interval...${NC}"
    python3 trading_bot_run.py --symbol $symbol --interval $interval --strategy advanced_ml
}

# Chạy bot với cấu hình từ tệp
run_with_config() {
    symbol="BTCUSDT"
    interval="1h"
    config_file="advanced_ml_config.json"
    
    echo -e "${GREEN}Nhập cặp giao dịch (mặc định: BTCUSDT):${NC} \c"
    read input_symbol
    if [ ! -z "$input_symbol" ]; then
        symbol=$input_symbol
    fi
    
    echo -e "${GREEN}Nhập khung thời gian (mặc định: 1h):${NC} \c"
    read input_interval
    if [ ! -z "$input_interval" ]; then
        interval=$input_interval
    fi
    
    echo -e "${GREEN}Nhập tệp cấu hình (mặc định: advanced_ml_config.json):${NC} \c"
    read input_config
    if [ ! -z "$input_config" ]; then
        config_file=$input_config
    fi
    
    if [ ! -f "$config_file" ]; then
        echo -e "${RED}Lỗi: Tệp cấu hình $config_file không tồn tại.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Chạy bot với cấu hình từ tệp $config_file cho cặp $symbol, khung thời gian $interval...${NC}"
    python3 trading_bot_run.py --symbol $symbol --interval $interval --config $config_file
}

# Huấn luyện mô hình ML
train_ml_model() {
    symbol="BTCUSDT"
    interval="1h"
    days=90
    
    echo -e "${GREEN}Nhập cặp giao dịch (mặc định: BTCUSDT):${NC} \c"
    read input_symbol
    if [ ! -z "$input_symbol" ]; then
        symbol=$input_symbol
    fi
    
    echo -e "${GREEN}Nhập khung thời gian (mặc định: 1h):${NC} \c"
    read input_interval
    if [ ! -z "$input_interval" ]; then
        interval=$input_interval
    fi
    
    echo -e "${GREEN}Nhập số ngày dữ liệu lịch sử (mặc định: 90):${NC} \c"
    read input_days
    if [ ! -z "$input_days" ]; then
        days=$input_days
    fi
    
    echo -e "${YELLOW}Huấn luyện mô hình ML cho cặp $symbol, khung thời gian $interval, với $days ngày dữ liệu lịch sử...${NC}"
    python3 train_ml_models.py --symbol $symbol --interval $interval --days $days
}

# Chạy test Advanced ML
run_test_advanced_ml() {
    echo -e "${YELLOW}Chạy test Advanced ML...${NC}"
    python3 test_advanced_ml.py
}

# Chạy Web UI
run_web_ui() {
    echo -e "${YELLOW}Chạy Web UI...${NC}"
    python3 main.py
}

# Vòng lặp chính
while true; do
    show_menu
    read choice
    
    case $choice in
        1) run_auto_strategy ;;
        2) run_ml_strategy ;;
        3) run_advanced_ml_strategy ;;
        4) run_with_config ;;
        5) train_ml_model ;;
        6) run_test_advanced_ml ;;
        7) run_web_ui ;;
        8) 
            echo -e "${GREEN}Tạm biệt!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Lựa chọn không hợp lệ. Vui lòng thử lại.${NC}"
            ;;
    esac
done
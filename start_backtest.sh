#!/bin/bash

# Script khởi động và quản lý quá trình backtest
# Sử dụng comprehensive_backtest.py và gửi thông báo qua Telegram

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Thiết lập cho Telegram
TELEGRAM_ENABLED=true
TELEGRAM_SCRIPT="python telegram_send_message.py"

# Hàm hiển thị thông báo
message() {
    echo -e "${BLUE}[INFO]${NC} $1"
    if [ "$TELEGRAM_ENABLED" = true ]; then
        $TELEGRAM_SCRIPT "info" "[BACKTEST] $1" &> /dev/null
    fi
}

warning() {
    echo -e "${YELLOW}[CẢNH BÁO]${NC} $1"
    if [ "$TELEGRAM_ENABLED" = true ]; then
        $TELEGRAM_SCRIPT "warning" "[BACKTEST CẢNH BÁO] $1" &> /dev/null
    fi
}

error() {
    echo -e "${RED}[LỖI]${NC} $1"
    if [ "$TELEGRAM_ENABLED" = true ]; then
        $TELEGRAM_SCRIPT "error" "[BACKTEST LỖI] $1" &> /dev/null
    fi
}

success() {
    echo -e "${GREEN}[THÀNH CÔNG]${NC} $1"
    if [ "$TELEGRAM_ENABLED" = true ]; then
        $TELEGRAM_SCRIPT "success" "[BACKTEST THÀNH CÔNG] $1" &> /dev/null
    fi
}

# Tạo script telegram_send_message.py nếu chưa tồn tại
create_telegram_script() {
    if [ ! -f "telegram_send_message.py" ]; then
        cat > telegram_send_message.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

# Đọc token bot từ biến môi trường hoặc file cấu hình
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Nếu không có trong biến môi trường, thử đọc từ file cấu hình
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    try:
        with open('bot_config.json', 'r') as f:
            config = json.load(f)
            if not TELEGRAM_BOT_TOKEN:
                TELEGRAM_BOT_TOKEN = config.get('telegram_bot_token')
            if not TELEGRAM_CHAT_ID:
                TELEGRAM_CHAT_ID = config.get('telegram_chat_id')
    except (FileNotFoundError, json.JSONDecodeError):
        pass

def send_telegram_message(message_type, message_content):
    """
    Gửi thông báo qua Telegram
    
    Args:
        message_type (str): Loại thông báo ('info', 'warning', 'success', 'error')
        message_content (str): Nội dung thông báo
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Thiếu thông tin cấu hình Telegram")
        return False
    
    # Thêm emoji tương ứng với loại thông báo
    emoji_map = {
        'info': 'ℹ️',
        'warning': '⚠️',
        'success': '✅',
        'error': '❌'
    }
    
    emoji = emoji_map.get(message_type.lower(), 'ℹ️')
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    # Chuẩn bị tin nhắn
    formatted_message = f"{emoji} *{message_type.upper()}* [{timestamp}]\n{message_content}"
    
    # Gửi tin nhắn thông qua API Telegram
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": formatted_message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(api_url, data=data)
        result = response.json()
        
        if result.get("ok"):
            return True
        else:
            print(f"Lỗi API Telegram: {result.get('description')}")
            return False
    except Exception as e:
        print(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
        return False

if __name__ == "__main__":
    # Kiểm tra tham số
    if len(sys.argv) < 3:
        print("Sử dụng: python telegram_send_message.py <message_type> <message_content>")
        sys.exit(1)
    
    message_type = sys.argv[1]
    message_content = sys.argv[2]
    
    # Gửi tin nhắn
    result = send_telegram_message(message_type, message_content)
    
    if result:
        print(f"Đã gửi thông báo {message_type} thành công")
    else:
        print(f"Không thể gửi thông báo {message_type}")
EOF
        chmod +x telegram_send_message.py
        message "Đã tạo script gửi thông báo Telegram"
    fi
}

# Kiểm tra các tiến trình backtest hiện tại
check_running_process() {
    if [ -f "backtest.pid" ]; then
        pid=$(cat backtest.pid)
        if ps -p $pid > /dev/null; then
            error "Tiến trình backtest đang chạy với PID $pid. Không thể khởi động backtest mới."
            error "Sử dụng 'bash stop_backtest.sh' để dừng tiến trình hiện tại trước khi bắt đầu tiến trình mới."
            return 1
        else
            message "PID cũ ($pid) không còn hoạt động. Xóa file backtest.pid cũ."
            rm -f backtest.pid
        fi
    fi
    return 0
}

# Kiểm tra xem có cấu hình backtest không
check_backtest_config() {
    if [ ! -f "backtest_master_config.json" ]; then
        error "Không tìm thấy file cấu hình backtest_master_config.json"
        error "Vui lòng tạo file cấu hình trước khi chạy backtest."
        return 1
    fi
    
    # Kiểm tra cấu hình có hợp lệ không
    if ! jq empty backtest_master_config.json 2>/dev/null; then
        error "File cấu hình backtest_master_config.json không phải là JSON hợp lệ."
        return 1
    fi
    
    # Kiểm tra các trường bắt buộc
    if ! jq -e '.symbols' backtest_master_config.json >/dev/null 2>&1 || \
       ! jq -e '.timeframes' backtest_master_config.json >/dev/null 2>&1 || \
       ! jq -e '.phases' backtest_master_config.json >/dev/null 2>&1; then
        error "File cấu hình thiếu các trường bắt buộc (symbols, timeframes, phases)."
        return 1
    fi
    
    message "Đã xác nhận file cấu hình backtest hợp lệ."
    return 0
}

# Kiểm tra dữ liệu cần thiết
check_data_available() {
    symbols=$(jq -r '.symbols[]' backtest_master_config.json)
    timeframes=$(jq -r '.timeframes[]' backtest_master_config.json)
    
    missing_data=false
    
    for symbol in $symbols; do
        for timeframe in $timeframes; do
            found=false
            
            # Kiểm tra trong thư mục chính
            if [ -f "test_data/${symbol}_${timeframe}.csv" ]; then
                found=true
            fi
            
            # Kiểm tra trong thư mục con của test_data
            for dir in test_data/*/; do
                if [ -f "${dir}${symbol}_${timeframe}.csv" ]; then
                    found=true
                    break
                fi
            done
            
            if [ "$found" = false ]; then
                warning "Không tìm thấy dữ liệu cho ${symbol} ${timeframe}"
                missing_data=true
            fi
        done
    done
    
    if [ "$missing_data" = true ]; then
        warning "Một số dữ liệu cần thiết không tìm thấy"
        read -p "Bạn có muốn tải dữ liệu bây giờ? (y/n): " download_data
        
        if [ "$download_data" = "y" ]; then
            message "Bắt đầu tải dữ liệu..."
            bash download_backtest_data.sh
        else
            warning "Tiếp tục backtest mà không tải dữ liệu. Có thể gặp lỗi nếu thiếu dữ liệu."
        fi
    else
        success "Tất cả dữ liệu cần thiết đã có sẵn."
    fi
    
    return 0
}

# Hàm khởi động backtest
start_backtest() {
    message "Đang bắt đầu quy trình backtest..."
    
    # Tạo command để chạy backtest
    backtest_cmd="python comprehensive_backtest.py"
    
    # Kiểm tra tham số đầu vào
    if [ -n "$1" ]; then
        backtest_cmd="$backtest_cmd --config $1"
    fi
    
    # Chạy backtest trong background và lưu PID
    message "Chạy lệnh: $backtest_cmd > backtest_output.log 2>&1 &"
    
    # Lưu thời gian bắt đầu
    echo "$(date +%s)" > bot_start_time.txt
    
    # Khởi động trong background
    eval "$backtest_cmd > backtest_output.log 2>&1 &"
    backtest_pid=$!
    
    # Lưu PID vào file
    echo $backtest_pid > backtest.pid
    
    success "Backtest đã được khởi động với PID: $backtest_pid"
    message "Output được lưu tại: backtest_output.log"
    message "Sử dụng 'tail -f backtest_output.log' để theo dõi output"
    
    # Thông báo khởi động qua Telegram
    if [ "$TELEGRAM_ENABLED" = true ]; then
        config_name=$(jq -r '.name // "Default"' backtest_master_config.json)
        symbols_count=$(jq '.symbols | length' backtest_master_config.json)
        timeframes_count=$(jq '.timeframes | length' backtest_master_config.json)
        phases_count=$(jq '.phases | length' backtest_master_config.json)
        
        # Tạo thông báo Telegram
        telegram_msg="🚀 *Backtest đã bắt đầu*\n"
        telegram_msg+="Cấu hình: $config_name\n"
        telegram_msg+="Cặp tiền: $symbols_count cặp\n"
        telegram_msg+="Khung thời gian: $timeframes_count khung\n"
        telegram_msg+="Số giai đoạn: $phases_count giai đoạn\n"
        telegram_msg+="PID: $backtest_pid"
        
        $TELEGRAM_SCRIPT "info" "$telegram_msg"
    fi
    
    # Chờ một chút để kiểm tra quy trình có khởi động thành công không
    sleep 3
    if ! ps -p $backtest_pid > /dev/null; then
        error "Backtest không thể khởi động hoặc đã kết thúc sớm!"
        error "Kiểm tra lỗi trong backtest_output.log:"
        tail -n 10 backtest_output.log
        return 1
    fi
    
    message "Backtest đang chạy. Theo dõi tiến trình trong log."
    return 0
}

# Hàm kiểm tra tiến trình
monitor_backtest() {
    if [ ! -f "backtest.pid" ]; then
        error "Không tìm thấy file backtest.pid. Backtest có thể chưa được khởi động."
        return 1
    fi
    
    pid=$(cat backtest.pid)
    if ! ps -p $pid > /dev/null; then
        warning "Tiến trình backtest với PID $pid không còn hoạt động."
        
        # Kiểm tra exit code nếu có
        if [ -f "backtest_exit_code.txt" ]; then
            exit_code=$(cat backtest_exit_code.txt)
            if [ "$exit_code" = "0" ]; then
                success "Backtest đã hoàn thành thành công."
            else
                error "Backtest đã kết thúc với mã lỗi $exit_code."
            fi
        else
            warning "Không thể xác định trạng thái backtest."
        fi
    else
        message "Tiến trình backtest (PID: $pid) đang hoạt động."
        
        # Hiển thị thông tin từ file trạng thái nếu có
        if [ -f "backtest_status.json" ]; then
            echo -e "\n${PURPLE}===== TRẠNG THÁI BACKTEST =====${NC}"
            
            # Hiển thị thông tin từ file json
            current_phase=$(jq -r '.current_phase // "N/A"' backtest_status.json)
            total_symbols=$(jq -r '.total_symbols // 0' backtest_status.json)
            completed_symbols=$(jq -r '.completed_symbols // 0' backtest_status.json)
            progress_percent=$(jq -r '.progress_percent // 0' backtest_status.json)
            estimated_time=$(jq -r '.estimated_completion // "N/A"' backtest_status.json)
            
            echo -e "${CYAN}Giai đoạn hiện tại:${NC} $current_phase"
            echo -e "${CYAN}Tiến độ:${NC} $completed_symbols/$total_symbols cặp ($progress_percent%)"
            echo -e "${CYAN}Thời gian hoàn thành dự kiến:${NC} $estimated_time"
            
            # Hiển thị biểu đồ tiến độ đơn giản
            progress_bar="["
            bar_width=50
            completed_width=$(( $bar_width * $progress_percent / 100 ))
            
            for ((i=0; i<$completed_width; i++)); do
                progress_bar+="#"
            done
            
            for ((i=$completed_width; i<$bar_width; i++)); do
                progress_bar+="-"
            done
            
            progress_bar+="]"
            
            echo -e "${GREEN}$progress_bar${NC}"
        else
            echo -e "\n${YELLOW}File trạng thái chưa được tạo.${NC}"
        fi
        
        # Hiển thị một phần log gần đây
        echo -e "\n${PURPLE}===== LOG GẦN ĐÂY =====${NC}"
        tail -n 10 backtest_output.log
    fi
}

# Hàm chính
main() {
    clear
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}                  QUẢN LÝ BACKTEST CRYPTO BOT                   ${NC}"
    echo -e "${BLUE}================================================================${NC}"
    
    # Tạo script Telegram nếu cần
    create_telegram_script
    
    # Kiểm tra các tiến trình đang chạy
    check_running_process
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Kiểm tra file cấu hình
    check_backtest_config
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Kiểm tra dữ liệu
    check_data_available
    
    # Xác nhận bắt đầu backtest
    echo ""
    read -p "Bạn có muốn bắt đầu backtest? (y/n): " start_confirm
    
    if [ "$start_confirm" = "y" ]; then
        start_backtest
        if [ $? -eq 0 ]; then
            # Sau khi khởi động, hiển thị menu giám sát
            echo ""
            echo -e "${BLUE}===== MENU GIÁM SÁT BACKTEST =====${NC}"
            echo "1. Hiển thị trạng thái hiện tại"
            echo "2. Xem log backtest"
            echo "3. Gửi thông báo test tới Telegram"
            echo "4. Thoát menu giám sát"
            
            read -p "Lựa chọn của bạn (1-4): " monitor_choice
            
            case $monitor_choice in
                1)
                    monitor_backtest
                    ;;
                2)
                    tail -f backtest_output.log
                    ;;
                3)
                    $TELEGRAM_SCRIPT "info" "Test thông báo từ hệ thống backtest"
                    success "Đã gửi thông báo test"
                    ;;
                *)
                    message "Thoát menu giám sát."
                    ;;
            esac
        fi
    else
        message "Đã hủy khởi động backtest."
    fi
    
    echo ""
    success "Quá trình xử lý đã hoàn tất!"
    message "Sử dụng 'bash stop_backtest.sh' để dừng backtest nếu cần."
}

# Chạy hàm chính
main "$@"
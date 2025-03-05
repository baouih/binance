#!/bin/bash

# Script dừng quá trình backtest và gửi thông báo qua Telegram

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Thiết lập cho Telegram
TELEGRAM_ENABLED=true
TELEGRAM_SCRIPT="python telegram_send_message.py"

# Hàm hiển thị thông báo
message() {
    echo -e "${BLUE}[INFO]${NC} $1"
    if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "info" "[BACKTEST] $1" &> /dev/null
    fi
}

warning() {
    echo -e "${YELLOW}[CẢNH BÁO]${NC} $1"
    if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "warning" "[BACKTEST CẢNH BÁO] $1" &> /dev/null
    fi
}

error() {
    echo -e "${RED}[LỖI]${NC} $1"
    if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "error" "[BACKTEST LỖI] $1" &> /dev/null
    fi
}

success() {
    echo -e "${GREEN}[THÀNH CÔNG]${NC} $1"
    if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "success" "[BACKTEST THÀNH CÔNG] $1" &> /dev/null
    fi
}

# Kiểm tra xem tiến trình backtest có đang chạy không
check_backtest_process() {
    if [ ! -f "backtest.pid" ]; then
        error "Không tìm thấy file backtest.pid. Backtest có thể chưa được khởi động."
        return 1
    fi
    
    pid=$(cat backtest.pid)
    if ! ps -p $pid > /dev/null; then
        warning "Tiến trình backtest với PID $pid không còn hoạt động."
        rm -f backtest.pid
        return 1
    fi
    
    message "Đã tìm thấy tiến trình backtest (PID: $pid)"
    return 0
}

# Dừng tiến trình backtest và các tiến trình con
stop_backtest() {
    local pid=$1
    local force=$2
    
    # Lưu trạng thái hiện tại nếu có
    if [ -f "backtest_status.json" ]; then
        cp backtest_status.json backtest_status_backup.json
        message "Đã sao lưu trạng thái backtest hiện tại"
    fi
    
    message "Đang dừng tiến trình backtest (PID: $pid)..."
    
    # Tìm tất cả các tiến trình con
    local child_pids=$(pgrep -P $pid)
    
    if [ "$force" = "force" ]; then
        # Dừng tiến trình bằng SIGKILL (buộc dừng)
        kill -9 $pid 2>/dev/null
        message "Đã gửi tín hiệu SIGKILL đến tiến trình chính"
        
        for child_pid in $child_pids; do
            kill -9 $child_pid 2>/dev/null
            message "Đã gửi tín hiệu SIGKILL đến tiến trình con (PID: $child_pid)"
        done
    else
        # Dừng tiến trình bằng SIGTERM (yêu cầu dừng)
        kill -15 $pid 2>/dev/null
        message "Đã gửi tín hiệu SIGTERM đến tiến trình chính"
        
        # Chờ 5 giây
        message "Chờ tiến trình kết thúc..."
        sleep 5
        
        # Kiểm tra xem tiến trình đã kết thúc chưa
        if ps -p $pid > /dev/null; then
            warning "Tiến trình không phản hồi với SIGTERM. Sử dụng SIGKILL để buộc dừng."
            kill -9 $pid 2>/dev/null
            
            for child_pid in $child_pids; do
                kill -9 $child_pid 2>/dev/null
                message "Đã buộc dừng tiến trình con (PID: $child_pid)"
            done
        fi
    fi
    
    # Kiểm tra lại sau khi dừng
    if ps -p $pid > /dev/null; then
        error "Không thể dừng tiến trình backtest (PID: $pid)"
        return 1
    else
        success "Đã dừng thành công tiến trình backtest"
        # Xóa file PID
        rm -f backtest.pid
        
        # Ghi log thông tin
        echo "Dừng backtest: $(date)" >> backtest_controller.log
        
        # Gửi thông báo Telegram
        if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
            $TELEGRAM_SCRIPT "warning" "🛑 *BACKTEST ĐÃ DỪNG*\nBacktest đã được dừng theo yêu cầu. Xem chi tiết trong log."
        fi
        
        return 0
    fi
}

# Trích xuất và hiển thị báo cáo ngắn từ log backtest
extract_summary() {
    if [ ! -f "backtest_output.log" ]; then
        warning "Không tìm thấy file log backtest_output.log"
        return 1
    fi
    
    echo -e "\n${BLUE}===== TÓM TẮT BACKTEST =====${NC}"
    
    # Tìm thông tin trong log
    echo -e "${YELLOW}Thời gian chạy:${NC}"
    grep -E "Backtest started|Backtest completed" backtest_output.log | tail -2
    
    echo -e "\n${YELLOW}Kết quả chung:${NC}"
    grep -E "Total profit|Win rate|Sharpe ratio|Max drawdown" backtest_output.log | tail -4
    
    echo -e "\n${YELLOW}Thông tin mô hình:${NC}"
    grep -E "Best model|Accuracy|Precision|F1 score" backtest_output.log | tail -4
    
    echo -e "\n${YELLOW}10 dòng log cuối:${NC}"
    tail -10 backtest_output.log
    
    return 0
}

# Hàm chính
main() {
    clear
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}                DỪNG BACKTEST CRYPTO BOT                        ${NC}"
    echo -e "${BLUE}================================================================${NC}"
    
    # Kiểm tra tiến trình backtest
    check_backtest_process
    if [ $? -ne 0 ]; then
        read -p "Tiến trình backtest không tìm thấy. Bạn có muốn kiểm tra tóm tắt backtest không? (y/n): " check_summary
        if [ "$check_summary" = "y" ]; then
            extract_summary
        fi
        return 1
    fi
    
    # Hiển thị menu
    echo -e "\n${BLUE}===== TÙY CHỌN DỪNG BACKTEST =====${NC}"
    echo "1. Dừng backtest một cách an toàn (đợi hoàn thành tác vụ hiện tại)"
    echo "2. Buộc dừng backtest ngay lập tức"
    echo "3. Chỉ hiển thị tóm tắt backtest (không dừng)"
    echo "4. Thoát (không làm gì)"
    
    read -p "Lựa chọn của bạn (1-4): " stop_choice
    
    pid=$(cat backtest.pid)
    
    case $stop_choice in
        1)
            stop_backtest $pid
            if [ $? -eq 0 ]; then
                extract_summary
            fi
            ;;
        2)
            stop_backtest $pid "force"
            if [ $? -eq 0 ]; then
                extract_summary
            fi
            ;;
        3)
            extract_summary
            ;;
        *)
            message "Đã hủy thao tác dừng backtest."
            ;;
    esac
    
    echo ""
    message "Xử lý hoàn tất."
}

# Chạy hàm chính
main "$@"
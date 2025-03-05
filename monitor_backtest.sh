#!/bin/bash

# Script giám sát quá trình backtest với giao diện UI trong terminal
# Hiển thị trạng thái, tiến độ, sử dụng tài nguyên và log gần đây

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Thiết lập cho Telegram
TELEGRAM_ENABLED=true
TELEGRAM_SCRIPT="python telegram_send_message.py"

# Thiết lập các tham số
REFRESH_INTERVAL=5  # Làm mới màn hình mỗi 5 giây
LOG_LINES=10        # Số dòng log hiển thị
QUIET_MODE=false    # Chế độ yên lặng (không gửi Telegram)
MONITOR_LOG="backtest_monitor.log"  # File log cho trình giám sát

# Hàm hiển thị thông báo
message() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[INFO] $1" >> $MONITOR_LOG
    if [ "$TELEGRAM_ENABLED" = true ] && [ "$QUIET_MODE" = false ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "info" "[BACKTEST MONITOR] $1" &> /dev/null
    fi
}

warning() {
    echo -e "${YELLOW}[CẢNH BÁO]${NC} $1"
    echo "[WARNING] $1" >> $MONITOR_LOG
    if [ "$TELEGRAM_ENABLED" = true ] && [ "$QUIET_MODE" = false ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "warning" "[BACKTEST MONITOR] $1" &> /dev/null
    fi
}

error() {
    echo -e "${RED}[LỖI]${NC} $1"
    echo "[ERROR] $1" >> $MONITOR_LOG
    if [ "$TELEGRAM_ENABLED" = true ] && [ "$QUIET_MODE" = false ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "error" "[BACKTEST MONITOR] $1" &> /dev/null
    fi
}

success() {
    echo -e "${GREEN}[THÀNH CÔNG]${NC} $1"
    echo "[SUCCESS] $1" >> $MONITOR_LOG
    if [ "$TELEGRAM_ENABLED" = true ] && [ "$QUIET_MODE" = false ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "success" "[BACKTEST MONITOR] $1" &> /dev/null
    fi
}

# Hàm tính thời gian chạy
calculate_runtime() {
    if [ -f "bot_start_time.txt" ]; then
        start_time=$(cat bot_start_time.txt)
        current_time=$(date +%s)
        runtime=$((current_time - start_time))
        
        # Định dạng thời gian
        days=$((runtime / 86400))
        hours=$(( (runtime % 86400) / 3600 ))
        minutes=$(( (runtime % 3600) / 60 ))
        seconds=$((runtime % 60))
        
        if [ $days -gt 0 ]; then
            echo "${days}d ${hours}h ${minutes}m ${seconds}s"
        elif [ $hours -gt 0 ]; then
            echo "${hours}h ${minutes}m ${seconds}s"
        elif [ $minutes -gt 0 ]; then
            echo "${minutes}m ${seconds}s"
        else
            echo "${seconds}s"
        fi
    else
        echo "Không xác định"
    fi
}

# Hàm vẽ thanh tiến trình
draw_progress_bar() {
    local progress=$1
    local width=$2
    local bar_char="#"
    local empty_char="-"
    
    # Chuyển đổi phần trăm thành số kí tự đã hoàn thành
    local completed_width=$(( $width * $progress / 100 ))
    
    # Tạo thanh tiến trình
    progress_bar="["
    for ((i=0; i<$completed_width; i++)); do
        progress_bar+="$bar_char"
    done
    
    for ((i=$completed_width; i<$width; i++)); do
        progress_bar+="$empty_char"
    done
    
    progress_bar+="] ${progress}%"
    
    echo -e "${GREEN}$progress_bar${NC}"
}

# Giám sát một tiến trình backtest đang chạy
monitor_running_process() {
    local pid=$1
    local show_log=$2
    
    # Hiển thị thông tin tiến trình
    echo -e "${PURPLE}${BOLD}===== THÔNG TIN TIẾN TRÌNH =====${NC}"
    echo -e "${CYAN}PID:${NC} $pid"
    echo -e "${CYAN}Lệnh:${NC} $(ps -p $pid -o args= | sed 's/^python //')"
    echo -e "${CYAN}Thời gian chạy:${NC} $(calculate_runtime)"
    
    # Hiển thị thông tin sử dụng tài nguyên
    echo -e "\n${PURPLE}${BOLD}===== SỬ DỤNG TÀI NGUYÊN =====${NC}"
    echo -e "${CYAN}CPU:${NC} $(ps -p $pid -o %cpu= | tr -d ' ')%"
    echo -e "${CYAN}Bộ nhớ:${NC} $(ps -p $pid -o %mem= | tr -d ' ')%"
    
    # Hiển thị thông tin trạng thái nếu có
    if [ -f "backtest_status.json" ]; then
        echo -e "\n${PURPLE}${BOLD}===== TRẠNG THÁI BACKTEST =====${NC}"
        
        # Đọc và hiển thị thông tin từ file json
        current_phase=$(jq -r '.current_phase // "N/A"' backtest_status.json)
        strategy=$(jq -r '.strategy // "N/A"' backtest_status.json)
        symbol=$(jq -r '.current_symbol // "N/A"' backtest_status.json)
        timeframe=$(jq -r '.current_timeframe // "N/A"' backtest_status.json)
        total_symbols=$(jq -r '.total_symbols // 0' backtest_status.json)
        completed_symbols=$(jq -r '.completed_symbols // 0' backtest_status.json)
        progress_percent=$(jq -r '.progress_percent // 0' backtest_status.json)
        estimated_time=$(jq -r '.estimated_completion // "N/A"' backtest_status.json)
        
        echo -e "${CYAN}Giai đoạn:${NC} $current_phase"
        echo -e "${CYAN}Chiến lược:${NC} $strategy"
        echo -e "${CYAN}Symbol hiện tại:${NC} $symbol $timeframe"
        echo -e "${CYAN}Tiến độ:${NC} $completed_symbols/$total_symbols symbol"
        echo -e "${CYAN}Thời gian hoàn thành dự kiến:${NC} $estimated_time"
        
        # Hiển thị thanh tiến trình
        draw_progress_bar $progress_percent 50
    else
        echo -e "\n${YELLOW}File trạng thái backtest_status.json chưa được tạo.${NC}"
    fi
    
    # Hiển thị log gần đây nếu được yêu cầu
    if [ "$show_log" = true ] && [ -f "backtest_output.log" ]; then
        echo -e "\n${PURPLE}${BOLD}===== LOG GẦN ĐÂY =====${NC}"
        tail -n $LOG_LINES backtest_output.log
    fi
}

# Phân tích file log để hiển thị tóm tắt
show_log_summary() {
    if [ ! -f "backtest_output.log" ]; then
        warning "Không tìm thấy file log backtest_output.log"
        return
    fi
    
    echo -e "\n${PURPLE}${BOLD}===== TÓM TẮT LOG =====${NC}"
    
    # Tìm các thông báo lỗi
    error_count=$(grep -c -i "error\|exception\|failed" backtest_output.log)
    echo -e "${CYAN}Số lỗi phát hiện:${NC} $error_count"
    
    # Hiển thị các lỗi gần đây nếu có
    if [ $error_count -gt 0 ]; then
        echo -e "\n${YELLOW}Các lỗi gần đây:${NC}"
        grep -i "error\|exception\|failed" backtest_output.log | tail -5
    fi
    
    # Hiển thị thống kê
    echo -e "\n${CYAN}Kích thước log:${NC} $(du -h backtest_output.log | cut -f1)"
    echo -e "${CYAN}Số dòng log:${NC} $(wc -l < backtest_output.log)"
    echo -e "${CYAN}Dòng log cuối:${NC} $(tail -1 backtest_output.log)"
}

# Kiểm tra tiến trình backtest
check_backtest_process() {
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
            warning "Không thể xác định trạng thái backtest kết thúc."
        fi
        
        return 1
    fi
    
    message "Tiến trình backtest (PID: $pid) đang hoạt động."
    return 0
}

# Hàm trình giám sát liên tục
monitor_continuously() {
    local show_log=$1
    
    clear
    message "Bắt đầu giám sát backtest. Nhấn Ctrl+C để dừng."
    
    while true; do
        # Xóa màn hình trước mỗi lần làm mới
        clear
        
        # Tiêu đề
        echo -e "${BLUE}================================================================${NC}"
        echo -e "${BLUE}${BOLD}                 GIÁM SÁT BACKTEST CRYPTO BOT                 ${NC}"
        echo -e "${BLUE}================================================================${NC}"
        echo -e "${YELLOW}Thời gian:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
        
        # Kiểm tra tiến trình
        check_backtest_process
        if [ $? -eq 0 ]; then
            pid=$(cat backtest.pid)
            monitor_running_process $pid $show_log
        else
            # Nếu tiến trình đã kết thúc, hiển thị tóm tắt log
            show_log_summary
            echo -e "\n${YELLOW}Tiến trình backtest đã kết thúc. Dừng giám sát.${NC}"
            break
        fi
        
        # Hiển thị hướng dẫn ở dưới cùng
        echo -e "\n${BLUE}================================================================${NC}"
        echo -e "${YELLOW}Đang làm mới mỗi ${REFRESH_INTERVAL} giây. Nhấn Ctrl+C để dừng.${NC}"
        
        # Đợi đến chu kỳ làm mới tiếp theo
        sleep $REFRESH_INTERVAL
    done
}

# Hàm xử lý tham số dòng lệnh
process_args() {
    # Xử lý các tham số
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-log)
                SHOW_LOG=false
                shift
                ;;
            --interval)
                REFRESH_INTERVAL="$2"
                shift 2
                ;;
            --lines)
                LOG_LINES="$2"
                shift 2
                ;;
            --quiet)
                QUIET_MODE=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                error "Tham số không hợp lệ: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Hàm hiển thị hướng dẫn sử dụng
show_usage() {
    echo -e "${BLUE}CÁCH SỬ DỤNG:${NC}"
    echo -e "  bash $0 [--no-log] [--interval N] [--lines N] [--quiet] [--help]"
    echo -e "\n${BLUE}TÙY CHỌN:${NC}"
    echo -e "  --no-log    Không hiển thị log"
    echo -e "  --interval N  Làm mới màn hình mỗi N giây (mặc định: 5)"
    echo -e "  --lines N   Số dòng log hiển thị (mặc định: 10)"
    echo -e "  --quiet     Chế độ yên lặng (không gửi thông báo Telegram)"
    echo -e "  --help      Hiển thị hướng dẫn này"
}

# Hàm chính
main() {
    # Khởi tạo log file
    echo "===== BACKTEST MONITOR LOG =====" > $MONITOR_LOG
    echo "Thời gian bắt đầu: $(date)" >> $MONITOR_LOG
    echo "----------------------------------------" >> $MONITOR_LOG
    
    # Mặc định hiển thị log
    SHOW_LOG=true
    
    # Xử lý tham số
    process_args "$@"
    
    # Kiểm tra tiến trình backtest
    check_backtest_process
    if [ $? -ne 0 ]; then
        # Nếu không có tiến trình đang chạy, hiển thị menu tùy chọn
        echo -e "\n${BLUE}===== TÙY CHỌN GIÁM SÁT =====${NC}"
        echo "1. Hiển thị tóm tắt backtest log"
        echo "2. Xem log backtest đầy đủ"
        echo "3. Thoát"
        
        read -p "Lựa chọn của bạn (1-3): " monitor_choice
        
        case $monitor_choice in
            1)
                show_log_summary
                ;;
            2)
                if [ -f "backtest_output.log" ]; then
                    less backtest_output.log
                else
                    error "Không tìm thấy file log backtest_output.log"
                fi
                ;;
            *)
                message "Thoát giám sát."
                ;;
        esac
    else
        # Nếu có tiến trình đang chạy, bắt đầu giám sát liên tục
        monitor_continuously $SHOW_LOG
    fi
}

# Chạy hàm chính với tham số được cung cấp
main "$@"
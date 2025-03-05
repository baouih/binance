#!/bin/bash

# Script tự động phục hồi backtest khi bị crash
# Giám sát tiến trình backtest và khởi động lại nó nếu bị crash

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Thiết lập cho Telegram
TELEGRAM_ENABLED=true
TELEGRAM_SCRIPT="python telegram_send_message.py"

# Thiết lập các tham số
CHECK_INTERVAL=60  # Kiểm tra mỗi 60 giây
MAX_RESTARTS=3     # Số lần khởi động lại tối đa
WAIT_BEFORE_RESTART=10  # Đợi 10 giây trước khi khởi động lại

# Biến toàn cục
restart_count=0
recovery_log="backtest_recovery.log"

# Hàm hiển thị thông báo
message() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[INFO] $1" >> $recovery_log
    if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "info" "[BACKTEST RECOVERY] $1" &> /dev/null
    fi
}

warning() {
    echo -e "${YELLOW}[CẢNH BÁO]${NC} $1"
    echo "[WARNING] $1" >> $recovery_log
    if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "warning" "[BACKTEST RECOVERY] $1" &> /dev/null
    fi
}

error() {
    echo -e "${RED}[LỖI]${NC} $1"
    echo "[ERROR] $1" >> $recovery_log
    if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "error" "[BACKTEST RECOVERY] $1" &> /dev/null
    fi
}

success() {
    echo -e "${GREEN}[THÀNH CÔNG]${NC} $1"
    echo "[SUCCESS] $1" >> $recovery_log
    if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        $TELEGRAM_SCRIPT "success" "[BACKTEST RECOVERY] $1" &> /dev/null
    fi
}

# Kiểm tra tiến trình backtest
check_backtest_process() {
    if [ ! -f "backtest.pid" ]; then
        error "Không tìm thấy file backtest.pid. Backtest có thể chưa được khởi động."
        return 1
    fi
    
    pid=$(cat backtest.pid)
    if ! ps -p $pid > /dev/null; then
        warning "Tiến trình backtest với PID $pid không còn hoạt động!"
        
        # Kiểm tra exit code nếu có
        if [ -f "backtest_exit_code.txt" ]; then
            exit_code=$(cat backtest_exit_code.txt)
            if [ "$exit_code" = "0" ]; then
                success "Backtest đã hoàn thành thành công. Không cần phục hồi."
                return 0
            else
                warning "Backtest đã kết thúc với mã lỗi $exit_code. Cần phục hồi."
                return 2
            fi
        else
            warning "Backtest đã crash nhưng không tìm thấy exit code. Cần phục hồi."
            return 2
        fi
    fi
    
    message "Tiến trình backtest (PID: $pid) đang hoạt động bình thường."
    return 0
}

# Lưu lại trạng thái hiện tại để phục hồi sau này
backup_current_state() {
    # Tạo thư mục cho backup nếu chưa tồn tại
    backup_dir="backtest_recovery_backups"
    mkdir -p $backup_dir
    
    # Tạo tên backup dựa trên timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="$backup_dir/backtest_backup_$timestamp.tar.gz"
    
    # Danh sách các file cần backup
    files_to_backup="backtest_status.json backtest_results backtest_charts"
    
    # Thêm vào các file khác nếu chúng tồn tại
    [ -f "backtest_controller.log" ] && files_to_backup="$files_to_backup backtest_controller.log"
    [ -f "backtest_output.log" ] && files_to_backup="$files_to_backup backtest_output.log"
    
    # Tạo file backup
    tar -czf $backup_file $files_to_backup 2>/dev/null
    
    # Kiểm tra kết quả
    if [ $? -eq 0 ]; then
        message "Đã sao lưu trạng thái hiện tại vào $backup_file"
        return 0
    else
        warning "Không thể sao lưu trạng thái hiện tại"
        return 1
    fi
}

# Khởi động lại backtest
restart_backtest() {
    # Sao lưu trạng thái hiện tại
    backup_current_state
    
    # Đợi một chút trước khi khởi động lại
    message "Đợi $WAIT_BEFORE_RESTART giây trước khi khởi động lại..."
    sleep $WAIT_BEFORE_RESTART
    
    # Tăng biến đếm khởi động lại
    restart_count=$((restart_count + 1))
    message "Đang thực hiện lần khởi động lại thứ $restart_count/$MAX_RESTARTS..."
    
    # Xóa file PID cũ
    rm -f backtest.pid
    
    # Tạo command để chạy backtest
    backtest_cmd="python comprehensive_backtest.py --resume"
    
    # Ghi thông tin vào log
    message "Khởi động lại backtest với lệnh: $backtest_cmd"
    
    # Khởi động backtest trong background
    eval "$backtest_cmd > backtest_output.log 2>&1 &"
    backtest_pid=$!
    
    # Lưu PID vào file
    echo $backtest_pid > backtest.pid
    
    # Gửi thông báo Telegram
    if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
        recover_msg="🔄 *BACKTEST ĐƯỢC KHỞI ĐỘNG LẠI*\n"
        recover_msg+="Lần khởi động lại: $restart_count/$MAX_RESTARTS\n"
        recover_msg+="PID mới: $backtest_pid\n"
        recover_msg+="Thời gian: $(date)"
        
        $TELEGRAM_SCRIPT "warning" "$recover_msg"
    fi
    
    # Chờ một chút để kiểm tra tiến trình đã khởi động thành công chưa
    sleep 5
    if ! ps -p $backtest_pid > /dev/null; then
        error "Không thể khởi động lại backtest!"
        return 1
    fi
    
    success "Đã khởi động lại backtest thành công với PID: $backtest_pid"
    return 0
}

# Hàm chính để giám sát và phục hồi
monitor_and_recover() {
    message "Bắt đầu giám sát tiến trình backtest..."
    
    while true; do
        # Kiểm tra tiến trình
        check_backtest_process
        status=$?
        
        # Xử lý theo trạng thái
        if [ $status -eq 0 ]; then
            # Tiến trình đang chạy hoặc đã hoàn thành, không cần phục hồi
            message "Kiểm tra kế tiếp sau $CHECK_INTERVAL giây..."
        elif [ $status -eq 2 ]; then
            # Tiến trình đã crash, cần phục hồi
            warning "Phát hiện backtest bị crash. Chuẩn bị khởi động lại..."
            
            # Kiểm tra số lần khởi động lại
            if [ $restart_count -lt $MAX_RESTARTS ]; then
                restart_backtest
            else
                error "Đã đạt đến số lần khởi động lại tối đa ($MAX_RESTARTS). Dừng giám sát."
                
                # Gửi thông báo Telegram
                if [ "$TELEGRAM_ENABLED" = true ] && [ -f "$TELEGRAM_SCRIPT" ]; then
                    $TELEGRAM_SCRIPT "error" "⛔ *BACKTEST RECOVERY THẤT BẠI*\nĐã đạt đến số lần khởi động lại tối đa ($MAX_RESTARTS).\nCần kiểm tra thủ công."
                fi
                
                return 1
            fi
        else
            # Không tìm thấy tiến trình, có thể chưa được khởi động
            warning "Không tìm thấy tiến trình backtest. Đợi $CHECK_INTERVAL giây..."
        fi
        
        # Đợi đến lần kiểm tra tiếp theo
        sleep $CHECK_INTERVAL
    done
}

# Hàm chạy trong chế độ daemon
run_as_daemon() {
    message "Khởi động auto_recover_backtest.sh trong chế độ daemon..."
    
    # Chạy script trong background
    nohup bash "$0" --monitor > /dev/null 2>&1 &
    daemon_pid=$!
    
    # Lưu PID của daemon
    echo $daemon_pid > backtest_recovery.pid
    
    success "Daemon đã được khởi động với PID: $daemon_pid"
    message "Nhật ký phục hồi được lưu tại: $recovery_log"
    message "Để dừng daemon, sử dụng: bash $0 --stop"
}

# Hàm dừng daemon
stop_daemon() {
    if [ ! -f "backtest_recovery.pid" ]; then
        error "Không tìm thấy file backtest_recovery.pid. Daemon có thể chưa được khởi động."
        return 1
    fi
    
    daemon_pid=$(cat backtest_recovery.pid)
    if ! ps -p $daemon_pid > /dev/null; then
        warning "Daemon với PID $daemon_pid không còn hoạt động."
        rm -f backtest_recovery.pid
        return 1
    fi
    
    # Dừng daemon
    kill -15 $daemon_pid
    
    # Đợi và kiểm tra
    sleep 2
    if ps -p $daemon_pid > /dev/null; then
        # Nếu vẫn chạy, dùng SIGKILL
        kill -9 $daemon_pid
        sleep 1
    fi
    
    # Kiểm tra lại
    if ps -p $daemon_pid > /dev/null; then
        error "Không thể dừng daemon với PID $daemon_pid"
        return 1
    else
        success "Đã dừng daemon thành công"
        rm -f backtest_recovery.pid
        return 0
    fi
}

# Hiển thị trạng thái daemon
show_daemon_status() {
    if [ ! -f "backtest_recovery.pid" ]; then
        warning "Không tìm thấy file backtest_recovery.pid. Daemon có thể chưa được khởi động."
        return 1
    fi
    
    daemon_pid=$(cat backtest_recovery.pid)
    if ! ps -p $daemon_pid > /dev/null; then
        warning "Daemon với PID $daemon_pid không còn hoạt động."
        return 1
    fi
    
    message "Daemon đang chạy với PID $daemon_pid"
    
    # Hiển thị thông tin từ log nếu có
    if [ -f "$recovery_log" ]; then
        echo -e "\n${BLUE}===== NHẬT KÝ PHỤC HỒI GẦN ĐÂY =====${NC}"
        tail -n 10 $recovery_log
    fi
    
    return 0
}

# Hàm hiển thị cách sử dụng script
show_usage() {
    echo -e "${BLUE}CÁCH SỬ DỤNG:${NC}"
    echo -e "  bash $0 [--option]"
    echo -e "\n${BLUE}CÁC TÙY CHỌN:${NC}"
    echo -e "  --start     Khởi động daemon giám sát và phục hồi"
    echo -e "  --stop      Dừng daemon"
    echo -e "  --status    Hiển thị trạng thái daemon"
    echo -e "  --monitor   Chạy trực tiếp chế độ giám sát (không phải daemon)"
    echo -e "  --help      Hiển thị trợ giúp này"
    echo -e "\n${BLUE}MÔ TẢ:${NC}"
    echo -e "  Script này giám sát tiến trình backtest và tự động khởi động lại"
    echo -e "  nếu nó bị crash. Số lần khởi động lại tối đa là $MAX_RESTARTS lần."
}

# Hàm chính
main() {
    # Khởi tạo log file nếu chưa tồn tại
    if [ ! -f "$recovery_log" ]; then
        echo "===== NHẬT KÝ PHỤC HỒI BACKTEST =====" > $recovery_log
        echo "Bắt đầu: $(date)" >> $recovery_log
        echo "----------------------------------------" >> $recovery_log
    fi
    
    # Xử lý tham số
    case "$1" in
        --start)
            run_as_daemon
            ;;
        --stop)
            stop_daemon
            ;;
        --status)
            show_daemon_status
            ;;
        --monitor)
            monitor_and_recover
            ;;
        --help)
            show_usage
            ;;
        *)
            # Nếu không có tham số, hiển thị menu
            clear
            echo -e "${BLUE}================================================================${NC}"
            echo -e "${BLUE}              PHỤC HỒI TỰ ĐỘNG BACKTEST                         ${NC}"
            echo -e "${BLUE}================================================================${NC}"
            
            echo -e "\n${BLUE}===== MENU PHỤC HỒI BACKTEST =====${NC}"
            echo "1. Bắt đầu daemon giám sát và phục hồi"
            echo "2. Dừng daemon"
            echo "3. Hiển thị trạng thái daemon"
            echo "4. Chạy chế độ giám sát trực tiếp (không phải daemon)"
            echo "5. Thoát"
            
            read -p "Lựa chọn của bạn (1-5): " menu_choice
            
            case $menu_choice in
                1)
                    run_as_daemon
                    ;;
                2)
                    stop_daemon
                    ;;
                3)
                    show_daemon_status
                    ;;
                4)
                    monitor_and_recover
                    ;;
                *)
                    message "Thoát chương trình."
                    ;;
            esac
            ;;
    esac
}

# Chạy hàm chính với tham số được cung cấp
main "$@"
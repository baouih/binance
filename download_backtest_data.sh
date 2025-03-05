#!/bin/bash

# Script tải dữ liệu cho backtest từ Binance
# Sử dụng fetch_real_data.py với các tham số phù hợp để tải dữ liệu cho các giai đoạn

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Hàm hiển thị thông báo
message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[CẢNH BÁO]${NC} $1"
}

error() {
    echo -e "${RED}[LỖI]${NC} $1"
}

success() {
    echo -e "${GREEN}[THÀNH CÔNG]${NC} $1"
}

# Kiểm tra xem Python và các thư viện cần thiết đã được cài đặt chưa
check_dependencies() {
    message "Kiểm tra các gói phụ thuộc..."
    
    # Kiểm tra Python
    if ! command -v python3 &> /dev/null; then
        error "Không tìm thấy Python. Vui lòng cài đặt Python 3.6 trở lên."
        exit 1
    fi
    
    # Kiểm tra các thư viện Python cần thiết
    python3 -c "import pandas, binance, tqdm" 2>/dev/null
    if [ $? -ne 0 ]; then
        warning "Một số thư viện Python cần thiết chưa được cài đặt."
        read -p "Bạn có muốn cài đặt chúng không? (y/n): " install_deps
        if [ "$install_deps" = "y" ]; then
            message "Đang cài đặt thư viện cần thiết..."
            pip install pandas python-binance tqdm python-dotenv
        else
            error "Không thể tiếp tục mà không có các thư viện cần thiết."
            exit 1
        fi
    else
        success "Tất cả các gói phụ thuộc đã được cài đặt."
    fi
}

# Lấy thông tin từ cấu hình backtest
parse_backtest_config() {
    message "Đọc cấu hình backtest..."
    if [ ! -f "backtest_master_config.json" ]; then
        error "Không tìm thấy file cấu hình backtest_master_config.json"
        exit 1
    fi
    
    # Lấy thông tin về symbols, timeframes và giai đoạn
    SYMBOLS=$(jq -r '.symbols | join(" ")' backtest_master_config.json)
    TIMEFRAMES=$(jq -r '.timeframes | join(" ")' backtest_master_config.json)
    
    # Lấy thông tin về các giai đoạn
    TRAINING_START=$(jq -r '.phases[0].start_date' backtest_master_config.json)
    TRAINING_END=$(jq -r '.phases[0].end_date' backtest_master_config.json)
    
    OPTIMIZATION_START=$(jq -r '.phases[1].start_date' backtest_master_config.json)
    OPTIMIZATION_END=$(jq -r '.phases[1].end_date' backtest_master_config.json)
    
    TESTING_START=$(jq -r '.phases[2].start_date' backtest_master_config.json)
    TESTING_END=$(jq -r '.phases[2].end_date' backtest_master_config.json)
    
    success "Đã đọc cấu hình backtest:"
    message "- Symbols: $SYMBOLS"
    message "- Timeframes: $TIMEFRAMES"
    message "- Giai đoạn huấn luyện: $TRAINING_START đến $TRAINING_END"
    message "- Giai đoạn tối ưu hóa: $OPTIMIZATION_START đến $OPTIMIZATION_END"
    message "- Giai đoạn kiểm thử: $TESTING_START đến $TESTING_END"
}

# Tải dữ liệu cho một giai đoạn
download_data_for_phase() {
    phase_name=$1
    start_date=$2
    end_date=$3
    output_dir=$4
    
    message "===== TẢI DỮ LIỆU CHO GIAI ĐOẠN: $phase_name ====="
    message "Khoảng thời gian: $start_date đến $end_date"
    message "Lưu vào thư mục: $output_dir"
    
    # Tạo thư mục nếu chưa tồn tại
    mkdir -p $output_dir
    
    # Tải dữ liệu cho từng symbol và timeframe
    for symbol in $SYMBOLS; do
        for timeframe in $TIMEFRAMES; do
            message "Đang tải $symbol $timeframe..."
            python3 fetch_real_data.py --symbol $symbol --interval $timeframe \
                --start_date $start_date --end_date $end_date \
                --output_dir $output_dir --retry 5
                
            # Kiểm tra kết quả
            if [ $? -ne 0 ]; then
                warning "Có lỗi khi tải dữ liệu $symbol $timeframe"
            else
                success "Đã tải thành công $symbol $timeframe"
            fi
        done
    done
    
    success "Đã tải xong dữ liệu cho giai đoạn $phase_name"
}

# Hàm chính
main() {
    clear
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}          TẢI DỮ LIỆU CHO BACKTEST CRYPTO BOT                   ${NC}"
    echo -e "${BLUE}================================================================${NC}"
    
    # Kiểm tra dependencies
    check_dependencies
    
    # Đọc cấu hình
    parse_backtest_config
    
    # Xác nhận tải dữ liệu
    echo ""
    read -p "Bạn có muốn tải dữ liệu cho tất cả các giai đoạn? (y/n): " download_all
    
    if [ "$download_all" = "y" ]; then
        # Tải dữ liệu cho giai đoạn huấn luyện
        download_data_for_phase "HUẤN LUYỆN" $TRAINING_START $TRAINING_END "test_data/training_phase"
        
        # Tải dữ liệu cho giai đoạn tối ưu hóa
        download_data_for_phase "TỐI ƯU HÓA" $OPTIMIZATION_START $OPTIMIZATION_END "test_data/optimization_phase"
        
        # Tải dữ liệu cho giai đoạn kiểm thử
        download_data_for_phase "KIỂM THỬ" $TESTING_START $TESTING_END "test_data/testing_phase"
        
        success "Đã tải xong dữ liệu cho tất cả các giai đoạn!"
    else
        # Menu lựa chọn tải dữ liệu cho từng giai đoạn
        echo "Chọn giai đoạn để tải dữ liệu:"
        echo "1. Giai đoạn huấn luyện ban đầu"
        echo "2. Giai đoạn tối ưu hóa"
        echo "3. Giai đoạn kiểm thử mở rộng"
        echo "4. Thoát"
        
        read -p "Nhập lựa chọn của bạn (1-4): " choice
        
        case $choice in
            1) 
                download_data_for_phase "HUẤN LUYỆN" $TRAINING_START $TRAINING_END "test_data/training_phase"
                ;;
            2)
                download_data_for_phase "TỐI ƯU HÓA" $OPTIMIZATION_START $OPTIMIZATION_END "test_data/optimization_phase"
                ;;
            3)
                download_data_for_phase "KIỂM THỬ" $TESTING_START $TESTING_END "test_data/testing_phase"
                ;;
            4) 
                message "Thoát chương trình." 
                exit 0
                ;;
            *)
                error "Lựa chọn không hợp lệ."
                ;;
        esac
    fi
    
    echo ""
    message "Kiểm tra dữ liệu đã tải:"
    find test_data -name "*.csv" | sort
    
    echo ""
    success "Quá trình tải dữ liệu đã hoàn tất!"
    message "Bạn có thể bắt đầu backtest bằng lệnh: bash start_backtest.sh"
}

# Chạy hàm chính
main
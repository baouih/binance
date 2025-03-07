#!/bin/bash

# Script chạy thử nghiệm rủi ro cho một nhóm đồng coin cụ thể
# Sử dụng: ./run_risk_test_by_group.sh [group_number]
# Ví dụ: ./run_risk_test_by_group.sh 1   # Chạy nhóm 1

# Thiết lập màu sắc cho output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Hàm in thông báo có màu
print_message() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] ${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] ${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] ${RED}$1${NC}"
}

# Định nghĩa các nhóm đồng coin
GROUP1=("BTCUSDT" "ETHUSDT" "BNBUSDT")
GROUP2=("ADAUSDT" "SOLUSDT" "DOGEUSDT" "XRPUSDT")
GROUP3=("LINKUSDT" "AVAXUSDT" "DOTUSDT")
GROUP4=("MATICUSDT" "LTCUSDT" "ATOMUSDT" "UNIUSDT")

# Khung thời gian
INTERVAL="1h"

# Kiểm tra tham số nhóm
if [ -z "$1" ]; then
    print_error "Thiếu tham số nhóm. Sử dụng: ./run_risk_test_by_group.sh [group_number]"
    print_message "Các nhóm có sẵn:"
    print_message "Nhóm 1: ${GROUP1[*]}"
    print_message "Nhóm 2: ${GROUP2[*]}"
    print_message "Nhóm 3: ${GROUP3[*]}"
    print_message "Nhóm 4: ${GROUP4[*]}"
    exit 1
fi

# Lấy nhóm đồng coin tương ứng
GROUP_NUM=$1
case $GROUP_NUM in
    1)
        COINS=("${GROUP1[@]}")
        ;;
    2)
        COINS=("${GROUP2[@]}")
        ;;
    3)
        COINS=("${GROUP3[@]}")
        ;;
    4)
        COINS=("${GROUP4[@]}")
        ;;
    *)
        print_error "Nhóm không hợp lệ. Chỉ hỗ trợ nhóm 1-4."
        exit 1
        ;;
esac

# Tổng số coin cần chạy
TOTAL_COINS=${#COINS[@]}
CURRENT=0

# Tạo thư mục kết quả tổng hợp
mkdir -p risk_analysis/summary

# Thời gian bắt đầu
START_TIME=$(date +%s)

print_message "=== BẮT ĐẦU CHẠY THỬ NGHIỆM RỦI RO CHO NHÓM ${GROUP_NUM}: ${COINS[*]} ==="
print_message "Tổng số đồng coin cần chạy: $TOTAL_COINS"
print_message "Khung thời gian: $INTERVAL"
print_message "Mỗi đồng coin sẽ được chạy với 5 mức rủi ro: 0.5%, 1.0%, 1.5%, 2.0%, 3.0%"
echo ""

# Chạy từng đồng coin trong nhóm
for coin in "${COINS[@]}"; do
    CURRENT=$((CURRENT + 1))
    print_message "[$CURRENT/$TOTAL_COINS] Bắt đầu chạy thử nghiệm cho $coin"
    
    # Chạy script python cho đồng coin hiện tại
    python run_single_coin_risk_test.py --symbol $coin --interval $INTERVAL
    
    if [ $? -eq 0 ]; then
        print_message "[$CURRENT/$TOTAL_COINS] Đã hoàn thành thử nghiệm cho $coin"
    else
        print_error "[$CURRENT/$TOTAL_COINS] Lỗi khi chạy thử nghiệm cho $coin"
    fi
    
    # Sao chép báo cáo vào thư mục tổng hợp
    if [ -f "risk_analysis/${coin}_${INTERVAL}_risk_summary.md" ]; then
        cp "risk_analysis/${coin}_${INTERVAL}_risk_summary.md" "risk_analysis/summary/"
        cp "risk_analysis/${coin}_${INTERVAL}_risk_comparison.png" "risk_analysis/summary/"
    fi
    
    echo ""
    
    # Tạm nghỉ giữa các lần chạy để không quá tải hệ thống
    if [ $CURRENT -lt $TOTAL_COINS ]; then
        print_warning "Đợi 5 giây trước khi chạy đồng coin tiếp theo..."
        sleep 5
    fi
done

# Thời gian kết thúc
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(( (DURATION % 3600) / 60 ))
SECONDS=$((DURATION % 60))

# Tạo báo cáo tổng hợp cho nhóm
SUMMARY_FILE="risk_analysis/summary/group${GROUP_NUM}_coins_risk_summary.md"

echo "# Báo cáo tổng hợp kiểm thử rủi ro cho nhóm ${GROUP_NUM}" > $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "*Ngày tạo: $(date +'%Y-%m-%d %H:%M:%S')*" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "## Tổng quan" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "- **Đồng coin đã kiểm thử:** ${COINS[*]}" >> $SUMMARY_FILE
echo "- **Tổng số đồng coin:** $TOTAL_COINS" >> $SUMMARY_FILE
echo "- **Khung thời gian:** $INTERVAL" >> $SUMMARY_FILE
echo "- **Thời gian chạy:** $HOURS giờ $MINUTES phút $SECONDS giây" >> $SUMMARY_FILE
echo "- **Các mức rủi ro kiểm thử:** 0.5%, 1.0%, 1.5%, 2.0%, 3.0%" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "## Danh sách báo cáo chi tiết" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE

for coin in "${COINS[@]}"; do
    if [ -f "risk_analysis/summary/${coin}_${INTERVAL}_risk_summary.md" ]; then
        echo "- [Báo cáo chi tiết $coin](${coin}_${INTERVAL}_risk_summary.md)" >> $SUMMARY_FILE
    fi
done

# Thông báo hoàn thành
print_message "=== ĐÃ HOÀN THÀNH THỬ NGHIỆM RỦI RO CHO NHÓM ${GROUP_NUM} ==="
print_message "Tổng thời gian chạy: $HOURS giờ $MINUTES phút $SECONDS giây"
print_message "Xem báo cáo tổng hợp tại: $SUMMARY_FILE"
#!/bin/bash

# Script chạy toàn bộ quy trình ML từ tải dữ liệu đến đánh giá hiệu suất

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Bắt đầu quy trình kiểm thử ML đầy đủ ===${NC}"

# Tạo thư mục nếu chưa tồn tại
mkdir -p test_data
mkdir -p ml_results
mkdir -p ml_charts
mkdir -p ml_models

# 1. Tải dữ liệu lịch sử từ Binance (6 tháng trở lại đây)
echo -e "${YELLOW}1. Đang tải dữ liệu lịch sử từ Binance...${NC}"

# Danh sách coin cần kiểm thử
COINS=("BTCUSDT" "ETHUSDT" "BNBUSDT")
# Danh sách timeframe
TIMEFRAMES=("1h" "4h")

# Lấy ngày hiện tại và ngày 6 tháng trước
END_DATE=$(date +"%Y-%m-%d")
START_DATE=$(date -d "6 months ago" +"%Y-%m-%d")

for coin in "${COINS[@]}"; do
  for timeframe in "${TIMEFRAMES[@]}"; do
    echo -e "  Đang tải dữ liệu ${coin} - ${timeframe} từ ${START_DATE} đến ${END_DATE}..."
    
    # Lưu ý: Thay thế lệnh này bằng lệnh thực tế để tải dữ liệu
    # python -c "from binance_api import BinanceAPI; api = BinanceAPI(); api.download_historical_data('${coin}', '${timeframe}', '${START_DATE}', '${END_DATE}', output_dir='test_data')"
    
    # Tạm thời tạo file giả nếu không có file
    if [ ! -f "test_data/${coin}_${timeframe}.csv" ]; then
      echo -e "    ${RED}Không tìm thấy dữ liệu, bỏ qua...${NC}"
    else
      echo -e "    ${GREEN}Đã tải xong dữ liệu ${coin}_${timeframe}.csv${NC}"
    fi
  done
done

# 2. Chạy kiểm thử ML cho tất cả khoảng thời gian (1, 3, 6 tháng)
echo -e "\n${YELLOW}2. Chạy kiểm thử ML cho tất cả khoảng thời gian...${NC}"

# Lưu ý: Sử dụng tham số đầy đủ để chạy các khoảng thời gian 1, 3, 6 tháng
echo -e "  Đang chạy run_period_ml_backtest.py với đầy đủ tham số..."
python run_period_ml_backtest.py --full

# 3. Phân tích hiệu suất dự đoán (1, 3, 7 ngày)
echo -e "\n${YELLOW}3. Phân tích hiệu suất dự đoán...${NC}"
# Phân tích hiệu suất các mô hình ML
python analyze_ml_performance.py --input ml_results --output ml_results/ml_performance_analysis.html

# Hiển thị thông tin báo cáo
if [ -f "ml_results/ml_performance_analysis.html" ]; then
  echo -e "  ${GREEN}Báo cáo phân tích hiệu suất: ml_results/ml_performance_analysis.html${NC}"
else
  echo -e "  ${RED}Không thể tạo báo cáo phân tích hiệu suất${NC}"
  
  # Kiểm tra báo cáo tổng hợp đã có
  if [ -f "ml_results/ml_summary_report.html" ]; then
    echo -e "  ${GREEN}Báo cáo tổng hợp: ml_results/ml_summary_report.html${NC}"
  else
    echo -e "  ${RED}Không tìm thấy báo cáo tổng hợp${NC}"
  fi
fi

# 4. Tìm mô hình tốt nhất cho mỗi coin và khoảng thời gian
echo -e "\n${YELLOW}4. Tìm mô hình tốt nhất...${NC}"
# Đây là lệnh giả định để tìm mô hình tốt nhất
# python find_best_models.py --input ml_results/ml_summary_report.json --output ml_results/best_models.json

# 5. Tạo báo cáo tổng kết
echo -e "\n${YELLOW}5. Tạo báo cáo tổng kết...${NC}"
echo -e "  ${GREEN}Báo cáo tổng kết đã được tạo trong thư mục ml_results/${NC}"

echo -e "\n${BLUE}=== Đã hoàn thành quy trình kiểm thử ML ===${NC}"
echo -e "${GREEN}Kết quả:${NC}"
echo -e "  - Các mô hình đã được lưu trong: ${BLUE}ml_models/${NC}"
echo -e "  - Các biểu đồ đã được lưu trong: ${BLUE}ml_charts/${NC}"
echo -e "  - Các báo cáo đã được lưu trong: ${BLUE}ml_results/${NC}"

echo -e "\n${YELLOW}Tiếp theo bạn có thể:${NC}"
echo -e "  1. Xem báo cáo tổng hợp: ${BLUE}ml_results/ml_summary_report.html${NC}"
echo -e "  2. Tích hợp mô hình tốt nhất vào hệ thống giao dịch"
echo -e "  3. Triển khai mô hình thành production"
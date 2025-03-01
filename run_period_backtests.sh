#!/bin/bash

# Script to run backtest trên nhiều khoảng thời gian (3, 6, 9 tháng)
# Cú pháp: ./run_period_backtests.sh SYMBOL INTERVAL STRATEGY

# Kiểm tra đầu vào
if [ $# -lt 3 ]; then
    echo "Cách sử dụng: $0 <symbol> <interval> <strategy>"
    echo "Ví dụ: $0 BTCUSDT 1h macd"
    exit 1
fi

SYMBOL=$1
INTERVAL=$2
STRATEGY=$3

# Tạo thư mục kết quả nếu chưa tồn tại
mkdir -p backtest_results
mkdir -p backtest_charts

# Lấy ngày hiện tại
TODAY=$(date +%Y-%m-%d)

# Tính toán ngày bắt đầu cho các khoảng thời gian
# Lưu ý: date trong Ubuntu Linux có cú pháp khác với macOS
NINE_MONTHS_AGO=$(date -d "$TODAY - 9 months" +%Y-%m-%d)
SIX_MONTHS_AGO=$(date -d "$TODAY - 6 months" +%Y-%m-%d)
THREE_MONTHS_AGO=$(date -d "$TODAY - 3 months" +%Y-%m-%d)
ONE_MONTH_AGO=$(date -d "$TODAY - 1 month" +%Y-%m-%d)

echo "=== Bắt đầu chạy backtest cho các khoảng thời gian khác nhau ==="
echo "Symbol: $SYMBOL"
echo "Interval: $INTERVAL"
echo "Strategy: $STRATEGY"
echo "Ngày hôm nay: $TODAY"
echo "9 tháng trước: $NINE_MONTHS_AGO"
echo "6 tháng trước: $SIX_MONTHS_AGO"
echo "3 tháng trước: $THREE_MONTHS_AGO"
echo "1 tháng trước: $ONE_MONTH_AGO"

# Chạy backtest cho 9 tháng
echo -e "\n=== Chạy backtest cho 9 tháng gần nhất ==="
python enhanced_backtest.py --symbol $SYMBOL --interval $INTERVAL --strategy $STRATEGY \
    --start_date $NINE_MONTHS_AGO --end_date $TODAY \
    --output_prefix "9month_"

# Chạy backtest cho 6 tháng
echo -e "\n=== Chạy backtest cho 6 tháng gần nhất ==="
python enhanced_backtest.py --symbol $SYMBOL --interval $INTERVAL --strategy $STRATEGY \
    --start_date $SIX_MONTHS_AGO --end_date $TODAY \
    --output_prefix "6month_"

# Chạy backtest cho 3 tháng
echo -e "\n=== Chạy backtest cho 3 tháng gần nhất ==="
python enhanced_backtest.py --symbol $SYMBOL --interval $INTERVAL --strategy $STRATEGY \
    --start_date $THREE_MONTHS_AGO --end_date $TODAY \
    --output_prefix "3month_"

# Chạy backtest cho 1 tháng
echo -e "\n=== Chạy backtest cho 1 tháng gần nhất ==="
python enhanced_backtest.py --symbol $SYMBOL --interval $INTERVAL --strategy $STRATEGY \
    --start_date $ONE_MONTH_AGO --end_date $TODAY \
    --output_prefix "1month_"

echo -e "\n=== Đã hoàn thành các backtest cho $SYMBOL - $INTERVAL - $STRATEGY ==="
echo "Kết quả được lưu trong thư mục backtest_results/ với tiền tố tương ứng với khoảng thời gian"
#!/bin/bash

# Cài đặt các tham số
START_DATE=$(date -d "3 months ago" +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)
ACCOUNT_SIZES=(100 200 300)
TIMEFRAMES=("1h" "4h")

# Tạo thư mục
mkdir -p backtest_results
mkdir -p backtest_charts
mkdir -p backtest_summary
mkdir -p reports

echo "=== Bắt đầu phân tích giao dịch cho tài khoản nhỏ ==="
echo "Thời gian: $START_DATE đến $END_DATE"
echo "Các kích thước tài khoản: ${ACCOUNT_SIZES[@]}"
echo "Các khung thời gian: ${TIMEFRAMES[@]}"
echo "=============================================="

# 1. Chạy backtest cho từng tài khoản và timeframe riêng biệt
echo "1. Chạy backtest riêng cho từng cấu hình..."
for account_size in "${ACCOUNT_SIZES[@]}"; do
    for timeframe in "${TIMEFRAMES[@]}"; do
        echo "Chạy backtest cho tài khoản $account_size, timeframe $timeframe..."
        python backtest_small_account_strategy.py --account-size $account_size --start-date $START_DATE --end-date $END_DATE --timeframe $timeframe
    done
done

# 2. Chạy backtest tổng hợp cho các tài khoản
echo "2. Chạy phân tích tổng hợp cho tất cả tài khoản..."
python run_multi_account_backtest.py --account-sizes ${ACCOUNT_SIZES[@]} --start-date $START_DATE --end-date $END_DATE --timeframes ${TIMEFRAMES[@]}

# 3. Tạo báo cáo
echo "3. Tạo báo cáo tổng hợp..."
python generate_trading_report.py

echo "=== Hoàn thành phân tích! ==="
echo "Các file kết quả được lưu trong các thư mục:"
echo "- backtest_results: Kết quả chi tiết cho từng cấu hình"
echo "- backtest_charts: Biểu đồ phân tích"
echo "- backtest_summary: Báo cáo tổng hợp"
echo "- reports: Báo cáo HTML tổng hợp"
echo "=============================================="
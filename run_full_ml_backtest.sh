#!/bin/bash

# Script này thực hiện đầy đủ quá trình ML backtest 
# bao gồm nhiều đồng tiền, nhiều khung thời gian và nhiều độ dài dữ liệu

# Đảm bảo thư mục tồn tại
mkdir -p ml_results ml_charts ml_models

# Cấu hình
PERIODS=("1_month" "3_months" "6_months")
SYMBOLS=("BTCUSDT" "ETHUSDT" "BNBUSDT" "SOLUSDT" "XRPUSDT")
TIMEFRAMES=("1h" "4h" "1d")
PREDICTION_TARGETS=("1" "3" "7")

echo "=== Bắt đầu quá trình ML backtest đầy đủ ==="
date

# Chạy backtest cho từng cấu hình
for period in "${PERIODS[@]}"; do
    for symbol in "${SYMBOLS[@]}"; do
        for timeframe in "${TIMEFRAMES[@]}"; do
            for target in "${PREDICTION_TARGETS[@]}"; do
                echo "Đang chạy backtest cho $symbol $timeframe, khoảng thời gian $period, mục tiêu $target ngày..."
                
                # Tạo file log riêng cho mỗi lần chạy
                LOG_FILE="ml_results/${symbol}_${timeframe}_${period}_target${target}d.log"
                
                # Chạy quá trình backtest
                python run_period_ml_backtest.py \
                    --symbol $symbol \
                    --timeframe $timeframe \
                    --period $period \
                    --prediction_days $target \
                    --data_folder "real_data" \
                    --output_folder "ml_results" \
                    --charts_folder "ml_charts" \
                    --models_folder "ml_models" \
                    > $LOG_FILE 2>&1
                
                echo "  Đã hoàn thành và lưu log tại $LOG_FILE"
            done
        done
    done
done

# Phân tích kết quả
echo ""
echo "=== Phân tích kết quả ML ==="
python analyze_ml_performance.py \
    --results_dir "ml_results" \
    --charts_dir "ml_charts" \
    --output_report "ml_performance_report.html"

# Tạo báo cáo HTML
echo ""
echo "=== Tạo báo cáo HTML ==="
python create_html_report.py

echo ""
echo "=== Quá trình hoàn tất ==="
date
echo "Báo cáo hiệu suất có thể xem trong file ml_performance_report.html và ml_report.html"
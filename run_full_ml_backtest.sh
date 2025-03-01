#!/bin/bash

# Script để chạy ML backtest đầy đủ trên nhiều đồng tiền, khung thời gian, và khoảng thời gian

# Đảm bảo thư mục tồn tại
mkdir -p real_data
mkdir -p ml_results
mkdir -p ml_charts
mkdir -p ml_models
mkdir -p reports

# Danh sách các đồng tiền cần test
SYMBOLS=("BTCUSDT" "ETHUSDT" "BNBUSDT" "SOLUSDT" "XRPUSDT")

# Danh sách các khung thời gian
TIMEFRAMES=("1h" "4h" "1d")

# Danh sách các khoảng thời gian
PERIODS=("1_month" "3_months" "6_months")

# Danh sách các ngày dự đoán
PREDICTION_DAYS=(1 3 7)

# Danh sách các loại mô hình
MODEL_TYPES=("random_forest" "gradient_boosting")

# Tạo bộ dữ liệu nếu cần
if [ ! -f "real_data/fetch_results.json" ]; then
    echo "Đang tạo dữ liệu mẫu..."
    python generate_datasets.py --symbols=$(IFS=,; echo "${SYMBOLS[*]}") --timeframes=$(IFS=,; echo "${TIMEFRAMES[*]}") --periods=$(IFS=,; echo "${PERIODS[*]}")
    echo "Đã tạo dữ liệu mẫu."
fi

# Kiểm tra xem dữ liệu đã tồn tại chưa
if [ ! -f "real_data/fetch_results.json" ]; then
    echo "Không tìm thấy dữ liệu. Vui lòng chạy generate_datasets.py trước."
    exit 1
fi

echo "==============================================="
echo "Bắt đầu chạy ML backtest đầy đủ"
echo "==============================================="

# Chạy backtest cho từng kết hợp
for symbol in "${SYMBOLS[@]}"; do
    for timeframe in "${TIMEFRAMES[@]}"; do
        for period in "${PERIODS[@]}"; do
            for prediction_day in "${PREDICTION_DAYS[@]}"; do
                for model_type in "${MODEL_TYPES[@]}"; do
                    echo "Chạy ML backtest cho $symbol $timeframe ($period) với mục tiêu $prediction_day ngày, mô hình $model_type..."
                    
                    # Chạy backtest
                    python run_period_ml_backtest.py \
                        --symbol="$symbol" \
                        --timeframe="$timeframe" \
                        --period="$period" \
                        --prediction_days="$prediction_day" \
                        --model_type="$model_type" \
                        --data_folder="real_data" \
                        --output_folder="ml_results" \
                        --charts_folder="ml_charts" \
                        --models_folder="ml_models" \
                        --tune_hyperparams
                    
                    echo "Hoàn thành backtest cho $symbol $timeframe ($period) với mục tiêu $prediction_day ngày, mô hình $model_type."
                    echo "-----------------------------------------------"
                done
            done
        done
    done
done

echo "==============================================="
echo "Phân tích hiệu suất ML..."
echo "==============================================="

# Chạy phân tích hiệu suất
python analyze_ml_performance.py --results_dir="ml_results" --charts_dir="ml_charts" --output_report="reports/ml_performance_report.html"

echo "==============================================="
echo "Tạo báo cáo HTML..."
echo "==============================================="

# Tạo báo cáo HTML tổng quát
python create_html_report.py --report_dir="ml_results" --charts_dir="ml_charts" --output="reports/ml_report.html"

echo "==============================================="
echo "Hoàn thành ML backtest đầy đủ"
echo "Xem báo cáo tại:"
echo "1. Báo cáo hiệu suất: reports/ml_performance_report.html"
echo "2. Báo cáo tổng hợp: reports/ml_report.html"
echo "==============================================="
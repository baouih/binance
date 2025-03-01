#!/bin/bash

# Script để chạy backtest cho nhiều chiến lược và đối chiếu kết quả

# Kiểm tra đầu vào
if [ $# -lt 2 ]; then
    echo "Cách sử dụng: $0 <symbol> <interval>"
    echo "Ví dụ: $0 BTCUSDT 1h"
    exit 1
fi

SYMBOL=$1
INTERVAL=$2
OUTPUT_PREFIX="test_"

# Tạo thư mục kết quả nếu chưa tồn tại
mkdir -p backtest_results
mkdir -p backtest_charts

# Danh sách các chiến lược để chạy backtest
STRATEGIES=("rsi" "macd" "ema" "bbands" "auto" "combined")

echo "=== Bắt đầu so sánh các chiến lược giao dịch ==="
echo "Symbol: $SYMBOL"
echo "Interval: $INTERVAL"

# Lưu kết quả chính vào file để so sánh sau
RESULTS_FILE="backtest_results/strategies_comparison_${SYMBOL}_${INTERVAL}.csv"
echo "Strategy,Win Rate,Profit Factor,Expectancy,Profit Amount,Profit Percent,Sharpe Ratio,Max Drawdown" > $RESULTS_FILE

# Chạy backtest cho từng chiến lược
for STRATEGY in "${STRATEGIES[@]}"; do
    echo -e "\n=== Chạy backtest cho chiến lược: $STRATEGY ==="
    
    # Chạy backtest
    python enhanced_backtest.py --symbol $SYMBOL --interval $INTERVAL --strategy $STRATEGY \
        --output_prefix "${OUTPUT_PREFIX}${STRATEGY}_"
        
    # Trích xuất kết quả và thêm vào file so sánh
    RESULT_JSON="backtest_results/${OUTPUT_PREFIX}${STRATEGY}_${SYMBOL}_${INTERVAL}_${STRATEGY}_results.json"
    
    if [ -f "$RESULT_JSON" ]; then
        # Trích xuất các chỉ số hiệu suất từ file JSON
        WIN_RATE=$(cat $RESULT_JSON | grep -o '"win_rate": [0-9.]*' | cut -d' ' -f2)
        PROFIT_FACTOR=$(cat $RESULT_JSON | grep -o '"profit_factor": [0-9.]*' | cut -d' ' -f2)
        EXPECTANCY=$(cat $RESULT_JSON | grep -o '"expectancy": [0-9.]*' | cut -d' ' -f2)
        PROFIT_AMOUNT=$(cat $RESULT_JSON | grep -o '"profit_amount": [0-9.]*' | cut -d' ' -f2)
        PROFIT_PERCENT=$(cat $RESULT_JSON | grep -o '"profit_percent": [0-9.]*' | cut -d' ' -f2)
        SHARPE_RATIO=$(cat $RESULT_JSON | grep -o '"sharpe_ratio": [0-9.]*' | cut -d' ' -f2)
        MAX_DRAWDOWN=$(cat $RESULT_JSON | grep -o '"max_drawdown": [0-9.]*' | cut -d' ' -f2)
        
        # Thêm vào file CSV
        echo "$STRATEGY,$WIN_RATE,$PROFIT_FACTOR,$EXPECTANCY,$PROFIT_AMOUNT,$PROFIT_PERCENT,$SHARPE_RATIO,$MAX_DRAWDOWN" >> $RESULTS_FILE
        
        echo "Kết quả chiến lược $STRATEGY:"
        echo "- Win Rate: $WIN_RATE%"
        echo "- Profit Factor: $PROFIT_FACTOR"
        echo "- Expectancy: $EXPECTANCY"
        echo "- Profit: $PROFIT_AMOUNT ($PROFIT_PERCENT%)"
        echo "- Sharpe Ratio: $SHARPE_RATIO"
        echo "- Max Drawdown: $MAX_DRAWDOWN%"
    else
        echo "Không tìm thấy file kết quả cho chiến lược $STRATEGY"
    fi
done

echo -e "\n=== So sánh các chiến lược đã hoàn thành ==="
echo "Kết quả so sánh đã được lưu vào file: $RESULTS_FILE"

# Hiển thị bảng so sánh
echo -e "\nBảng so sánh chiến lược:"
cat $RESULTS_FILE | column -t -s ','
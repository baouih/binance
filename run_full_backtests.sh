#!/bin/bash

# Script điều khiển chạy tất cả các backtest trên nhiều đồng coin, chiến lược và khoảng thời gian

echo "=== BẮT ĐẦU CHẠY TOÀN BỘ BACKTEST ==="
echo "Script này sẽ chạy các backtest cho:"
echo "- 9 đồng coin (BTC, ETH, BNB, ADA, SOL, DOT, XRP, LTC, PI)"
echo "- 6 chiến lược (RSI, MACD, EMA, BBands, Auto, Combined)"
echo "- 4 khoảng thời gian (1 tháng, 3 tháng, 6 tháng, 9 tháng)"
echo "- Khung thời gian 1h"
echo

# Đảm bảo các thư mục tồn tại
mkdir -p backtest_results
mkdir -p backtest_charts
mkdir -p backtest_summary

# Chạy backtest cho từng khung thời gian
for INTERVAL in "1h"; do
    echo "Đang chạy backtest cho khung thời gian $INTERVAL"
    
    # Chạy script multi-coin và ghi log
    ./run_multi_coin_backtests.sh $INTERVAL 2>&1 | tee "backtest_logs_${INTERVAL}.log"
    
    echo "Đã hoàn thành backtest cho khung thời gian $INTERVAL"
    echo "Kết quả chi tiết được lưu trong backtest_summary/strategies_ranking_${INTERVAL}.html"
    echo
done

echo "=== ĐÃ HOÀN THÀNH TẤT CẢ BACKTEST ==="
echo "Các file báo cáo đã được lưu trong thư mục 'backtest_summary/'"
echo "Các biểu đồ đã được lưu trong thư mục 'backtest_charts/'"
echo "Các số liệu đã được lưu trong thư mục 'backtest_results/'"
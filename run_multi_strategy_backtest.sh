#!/bin/bash

# Script chạy backtest cho nhiều chiến lược
# Tự động tạo thư mục dữ liệu và kết quả nếu chưa tồn tại

# Tạo thư mục cần thiết
mkdir -p test_data test_results test_charts models

# Thiết lập môi trường
export PYTHONPATH="."

# Tải dữ liệu Binance nếu cần (đặt API key để sử dụng)
# python -c "from binance_api import BinanceAPI; api = BinanceAPI(); api.download_historical_data('BTCUSDT', '1h', '2024-01-01', output_dir='test_data')"

echo "=== Chạy kiểm thử toàn diện với nhiều chiến lược ==="
echo "Thời gian bắt đầu: $(date)"

# Chạy kiểm thử toàn diện
python run_comprehensive_test.py

echo "=== Kiểm thử hoàn tất ==="
echo "Thời gian kết thúc: $(date)"

# Mở báo cáo HTML nếu có trình duyệt
if command -v xdg-open &> /dev/null; then
    xdg-open test_results/comprehensive_report.html
elif command -v open &> /dev/null; then
    open test_results/comprehensive_report.html
else
    echo "Báo cáo đã được tạo tại: test_results/comprehensive_report.html"
fi
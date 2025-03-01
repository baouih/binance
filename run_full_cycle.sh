#!/bin/bash

# Script chạy chu trình đầy đủ: backtest, huấn luyện ML, và dự báo thị trường
# Script này sẽ thực hiện tất cả các bước để phân tích thị trường toàn diện

# Tạo thư mục cần thiết
mkdir -p test_data test_results test_charts models data forecast_data ml_reports ml_charts

# Thiết lập môi trường
export PYTHONPATH="."

# Thời gian bắt đầu
echo "===== BẮT ĐẦU CHU TRÌNH BACKTEST & ML TOÀN DIỆN ====="
echo "Thời gian bắt đầu: $(date)"
echo ""

# BƯỚC 1: Chạy backtest toàn diện
echo "===== BƯỚC 1: CHẠY BACKTEST TOÀN DIỆN ====="
python run_comprehensive_test.py

if [ $? -ne 0 ]; then
    echo "Lỗi khi chạy backtest toàn diện!"
    exit 1
fi

echo "Backtest toàn diện đã hoàn thành thành công."
echo ""

# BƯỚC 2: Huấn luyện và tối ưu hóa bằng ML
echo "===== BƯỚC 2: HUẤN LUYỆN VÀ TỐI ƯU HÓA ML ====="
python run_ml_optimization.py

if [ $? -ne 0 ]; then
    echo "Lỗi khi chạy tối ưu hóa ML!"
    exit 1
fi

echo "Tối ưu hóa ML đã hoàn thành thành công."
echo ""

# BƯỚC 3: Dự báo thị trường
echo "===== BƯỚC 3: DỰ BÁO THỊ TRƯỜNG ====="
python market_forecast.py

if [ $? -ne 0 ]; then
    echo "Lỗi khi dự báo thị trường!"
    exit 1
fi

echo "Dự báo thị trường đã hoàn thành thành công."
echo ""

# Hoàn thành
echo "===== CHU TRÌNH TOÀN DIỆN ĐÃ HOÀN THÀNH ====="
echo "Thời gian kết thúc: $(date)"

# Hiển thị đường dẫn đến các báo cáo
echo ""
echo "Các báo cáo và kết quả:"
echo "- Báo cáo backtest: test_results/comprehensive_report.html"
echo "- Báo cáo tối ưu hóa ML: ml_reports/optimization_sharpe_ratio.json"
echo "- Cấu hình chiến lược tối ưu: strategy_config.json"
echo "- Dự báo thị trường: forecast_charts/BTCUSDT_forecast.png"
echo ""

# Mở báo cáo HTML backtest nếu có trình duyệt
if command -v xdg-open &> /dev/null; then
    xdg-open test_results/comprehensive_report.html
elif command -v open &> /dev/null; then
    open test_results/comprehensive_report.html
else
    echo "Báo cáo đã được tạo tại: test_results/comprehensive_report.html"
fi
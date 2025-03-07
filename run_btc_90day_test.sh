#!/bin/bash

# Script chạy kiểm thử BTCUSDT với dữ liệu 90 ngày
# Sử dụng các mức rủi ro mới: 2.0%, 2.5%, 3.0%, 4.0%, 5.0%

echo "===================================================="
echo "  KIỂM THỬ 90 NGÀY CHO BTCUSDT VỚI 5 MỨC RỦI RO MỚI"
echo "===================================================="
echo ""
echo "Mức rủi ro: 2.0%, 2.5%, 3.0%, 4.0%, 5.0%"
echo "Khung thời gian: 1h"
echo "Giai đoạn: 90 ngày gần nhất"
echo ""
echo "Bắt đầu kiểm thử..."
echo ""

# Tạo các thư mục cần thiết
mkdir -p risk_analysis
mkdir -p logs
mkdir -p backtest_results

# Chạy kiểm thử
python run_90day_risk_test.py --symbol BTCUSDT --interval 1h

# Hiển thị kết quả
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Kiểm thử hoàn thành!"
    echo ""
    echo "Kết quả kiểm thử được lưu tại:"
    echo "- risk_analysis/BTCUSDT_1h_90day_risk_summary.md"
    echo "- risk_analysis/BTCUSDT_1h_90day_risk_comparison.png"
    echo ""
    echo "Xem báo cáo chi tiết để biết mức rủi ro tối ưu."
else
    echo ""
    echo "❌ Kiểm thử thất bại! Xem logs để biết chi tiết."
    echo ""
fi
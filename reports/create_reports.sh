#!/bin/bash

# Tạo thư mục reports nếu chưa tồn tại
mkdir -p reports

# Chạy công cụ trực quan hóa với các tùy chọn khác nhau
echo "Đang tạo báo cáo HTML đầy đủ..."
python enhanced_cli_visualizer.py --report -o reports/trading_report.html
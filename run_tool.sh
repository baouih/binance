#!/bin/bash

# Script chạy các công cụ giao dịch với tùy chọn khác nhau

# Kiểm tra tham số dòng lệnh
if [ "$#" -lt 1 ]; then
    echo "Cách sử dụng: $0 <lệnh> [tham_số]"
    echo ""
    echo "Các lệnh:"
    echo "  status           - Xem trạng thái bot"
    echo "  start            - Khởi động bot"
    echo "  stop             - Dừng bot"
    echo "  restart          - Khởi động lại bot"
    echo "  trades [n]       - Xem n giao dịch gần đây (mặc định 10)"
    echo "  positions        - Xem danh sách vị thế hiện tại"
    echo "  logs [n]         - Xem n dòng log gần đây (mặc định 20)"
    echo "  monitor          - Mở màn hình giám sát thời gian thực"
    echo "  backtest         - Chạy backtest"
    echo "  report           - Tạo báo cáo đầy đủ"
    echo "  equity           - Tạo biểu đồ đường cong vốn"
    echo "  performance      - Tạo biểu đồ hiệu suất"
    echo ""
    echo "Ví dụ:"
    echo "  $0 status        - Xem trạng thái bot"
    echo "  $0 trades 20     - Xem 20 giao dịch gần đây"
    echo "  $0 monitor       - Mở màn hình giám sát thời gian thực"
    exit 1
fi

# Xử lý lệnh
command="$1"
shift

case "$command" in
    status)
        python cli_controller.py -s
        ;;
    start)
        python cli_controller.py -b start
        ;;
    stop)
        python cli_controller.py -b stop
        ;;
    restart)
        python cli_controller.py -b restart
        ;;
    trades)
        count=${1:-10}
        python cli_controller.py -t "$count"
        ;;
    positions)
        python cli_controller.py -p
        ;;
    logs)
        count=${1:-20}
        python cli_controller.py -l "$count"
        ;;
    monitor)
        python cli_controller.py -m
        ;;
    backtest)
        python cli_controller.py -bt
        ;;
    report)
        ./reports/create_reports.sh
        ;;
    equity)
        python enhanced_cli_visualizer.py --equity
        ;;
    performance)
        python enhanced_cli_visualizer.py --performance
        ;;
    *)
        echo "Lệnh không hợp lệ: $command"
        echo "Chạy '$0' không có tham số để xem hướng dẫn."
        exit 1
        ;;
esac
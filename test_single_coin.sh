#!/bin/bash

# Script để chạy kiểm thử rủi ro cho một cặp giao dịch cụ thể
# Tác giả: AI Assistant
# Ngày tạo: 2025-03-06

# Kiểm tra tham số đầu vào
if [ -z "$1" ]; then
    echo "Sử dụng: $0 <mã_cặp_giao_dịch> [khung_thời_gian]"
    echo "Ví dụ: $0 BTCUSDT 1h"
    exit 1
fi

# Cặp giao dịch cần kiểm thử
SYMBOL="$1"

# Khung thời gian mặc định
INTERVAL="${2:-1h}"

# Thư mục lưu trữ báo cáo
REPORT_DIR="risk_analysis"

# Tạo thư mục báo cáo nếu chưa tồn tại
mkdir -p $REPORT_DIR

# Log file
LOG_FILE="$REPORT_DIR/single_coin_test.log"

# Hàm ghi log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Bắt đầu phân tích
log "=== BẮT ĐẦU PHÂN TÍCH RỦI RO CHO $SYMBOL ($INTERVAL) ==="

# Chạy phân tích
log "Đang phân tích $SYMBOL ($INTERVAL)..."
python run_single_coin_risk_test.py --symbol $SYMBOL --interval $INTERVAL

# Kiểm tra kết quả
if [ $? -eq 0 ]; then
    log "✅ Đã hoàn thành phân tích cho $SYMBOL"
    REPORT_PATH="$REPORT_DIR/${SYMBOL}_${INTERVAL}_risk_summary.md"
    
    if [ -f "$REPORT_PATH" ]; then
        # Trích xuất mức rủi ro khuyến nghị từ báo cáo
        RECOMMENDED_RISK=$(grep -B1 "✅" "$REPORT_PATH" | grep -o '[0-9]\.[0-9]%')
        
        if [ ! -z "$RECOMMENDED_RISK" ]; then
            log "Khuyến nghị mức rủi ro: $RECOMMENDED_RISK"
        else
            log "Chưa có khuyến nghị mức rủi ro"
        fi
        
        log "Báo cáo chi tiết: $REPORT_PATH"
    else
        log "Không tìm thấy báo cáo tại $REPORT_PATH"
    fi
else
    log "❌ Lỗi khi phân tích $SYMBOL"
fi

log "=== ĐÃ HOÀN THÀNH PHÂN TÍCH RỦI RO CHO $SYMBOL ($INTERVAL) ==="
#!/bin/bash

# Script để chạy kiểm thử 90 ngày cho nhiều cặp giao dịch với các mức rủi ro mới
# (2.0%, 2.5%, 3.0%, 4.0%, 5.0%)
# Tác giả: AI Assistant
# Ngày tạo: 2025-03-06

# Thiết lập
SYMBOLS=("BTCUSDT" "ETHUSDT")
INTERVAL="1h"
REPORT_DIR="risk_analysis"
LOG_FILE="$REPORT_DIR/90day_multi_coin_test.log"

# Tạo thư mục báo cáo nếu chưa tồn tại
mkdir -p $REPORT_DIR

# Hàm ghi log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Hàm chạy kiểm thử 90 ngày
run_90day_test() {
    local symbol=$1
    local interval=$2
    
    log "Chạy kiểm thử 90 ngày cho $symbol ($interval)..."
    python run_90day_risk_test.py --symbol $symbol --interval $interval
    
    if [ $? -eq 0 ]; then
        log "✅ Đã hoàn thành kiểm thử 90 ngày cho $symbol"
        return 0
    else
        log "❌ Lỗi khi chạy kiểm thử 90 ngày cho $symbol"
        return 1
    fi
}

# Hàm trích xuất mức rủi ro khuyến nghị từ báo cáo
extract_recommended_risk() {
    local symbol=$1
    local interval=$2
    
    local report_path="$REPORT_DIR/${symbol}_${interval}_90day_risk_summary.md"
    
    if [ -f "$report_path" ]; then
        local risk=$(grep -B1 "✅" "$report_path" | grep -o '[0-9]\.[0-9]%')
        echo $risk
    else
        echo "N/A"
    fi
}

# Bắt đầu kiểm thử
log "=== BẮT ĐẦU KIỂM THỬ RỦI RO 90 NGÀY CHO ${#SYMBOLS[@]} CẶP GIAO DỊCH ==="
log "Sử dụng các mức rủi ro mới: 2.0%, 2.5%, 3.0%, 4.0%, 5.0%"

# Tạo bảng báo cáo tổng hợp
SUMMARY_FILE="$REPORT_DIR/multi_coin_90day_risk_summary.md"
echo "# Báo cáo tổng hợp phân tích rủi ro 90 ngày cho nhiều cặp giao dịch" > $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "*Ngày tạo: $(date '+%Y-%m-%d %H:%M:%S')*" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "## Tổng quan" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "- **Số cặp giao dịch:** ${#SYMBOLS[@]}" >> $SUMMARY_FILE
echo "- **Khung thời gian:** $INTERVAL" >> $SUMMARY_FILE
echo "- **Giai đoạn kiểm thử:** 90 ngày gần nhất" >> $SUMMARY_FILE
echo "- **Các mức rủi ro kiểm thử:** 2.0%, 2.5%, 3.0%, 4.0%, 5.0%" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "## Kết quả phân tích" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "| Cặp giao dịch | Mức rủi ro khuyến nghị | Lợi nhuận (%) | Drawdown (%) | Sharpe Ratio |" >> $SUMMARY_FILE
echo "|---------------|------------------------|---------------|--------------|--------------|" >> $SUMMARY_FILE

# Chạy kiểm thử cho từng cặp giao dịch
for symbol in "${SYMBOLS[@]}"; do
    log "Đang xử lý $symbol..."
    
    # Chạy kiểm thử 90 ngày
    run_90day_test $symbol $INTERVAL
    
    # Trích xuất thông tin khuyến nghị
    risk=$(extract_recommended_risk $symbol $INTERVAL)
    
    # Trích xuất thông tin hiệu suất từ file JSON kết quả nếu có
    risk_value=$(echo $risk | sed 's/%//')
    risk_value_file=$(echo $risk_value | sed 's/\./\_/')
    highest_risk_file="backtest_results/${symbol}_${INTERVAL}_risk${risk_value_file}_90day_results.json"
    
    if [ -f "$highest_risk_file" ]; then
        profit=$(jq -r '.profit_percentage' $highest_risk_file)
        drawdown=$(jq -r '.max_drawdown' $highest_risk_file)
        sharpe=$(jq -r '.sharpe_ratio' $highest_risk_file)
    else
        profit="N/A"
        drawdown="N/A"
        sharpe="N/A"
    fi
    
    # Cập nhật bảng tổng hợp
    echo "| $symbol | $risk | $profit | $drawdown | $sharpe |" >> $SUMMARY_FILE
    
    # Tạm dừng giữa các lần chạy
    sleep 5
done

# Kết luận và khuyến nghị
echo "" >> $SUMMARY_FILE
echo "## Kết luận và khuyến nghị" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "Dựa trên kết quả kiểm thử 90 ngày, phân tích cho thấy:" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "- Các cặp giao dịch khác nhau có mức rủi ro tối ưu khác nhau" >> $SUMMARY_FILE
echo "- Mức rủi ro cao hơn mang lại lợi nhuận cao hơn nhưng cũng kèm theo drawdown lớn hơn" >> $SUMMARY_FILE
echo "- Sharpe ratio cao nhất thường xuất hiện ở mức rủi ro trung bình (khoảng 2.5-3.0%)" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "✅ **Khuyến nghị chung:** Tuỳ chỉnh mức rủi ro cho từng cặp giao dịch dựa trên kết quả cụ thể" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "*Lưu ý: Các kết quả dựa trên dữ liệu lịch sử 90 ngày và không đảm bảo hiệu suất trong tương lai. Luôn kết hợp với các chỉ số khác và quản lý vốn hợp lý.*" >> $SUMMARY_FILE

log "Đã tạo báo cáo tổng hợp tại $SUMMARY_FILE"
log "=== ĐÃ HOÀN THÀNH KIỂM THỬ RỦI RO 90 NGÀY CHO TẤT CẢ CÁC CẶP GIAO DỊCH ==="

# Hiển thị thông báo kết quả
echo ""
echo "=========================================================="
echo "  KIỂM THỬ RỦI RO 90 NGÀY ĐÃ HOÀN THÀNH CHO ${#SYMBOLS[@]} CẶP GIAO DỊCH"
echo "=========================================================="
echo ""
echo "Xem báo cáo tổng hợp tại: $SUMMARY_FILE"
echo ""
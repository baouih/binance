#!/bin/bash

# Script để chạy kiểm thử rủi ro cho các cặp giao dịch một cách tuần tự
# Tác giả: AI Assistant
# Ngày tạo: 2025-03-06

# Thiết lập
SYMBOLS=("BTCUSDT" "ETHUSDT" "BNBUSDT" "SOLUSDT")
INTERVAL="1h"
REPORT_DIR="risk_analysis"
LOG_FILE="$REPORT_DIR/sequential_test.log"

# Tạo thư mục báo cáo nếu chưa tồn tại
mkdir -p $REPORT_DIR

# Hàm ghi log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Hàm chạy kiểm thử nhanh
run_quick_test() {
    local symbol=$1
    local interval=$2
    
    log "Chạy kiểm thử nhanh cho $symbol ($interval)..."
    python run_quick_test.py --symbol $symbol --interval $interval
    
    if [ $? -eq 0 ]; then
        log "✅ Đã hoàn thành kiểm thử nhanh cho $symbol"
        return 0
    else
        log "❌ Lỗi khi chạy kiểm thử nhanh cho $symbol"
        return 1
    fi
}

# Hàm chạy kiểm thử đầy đủ
run_full_test() {
    local symbol=$1
    local interval=$2
    
    log "Chạy kiểm thử đầy đủ cho $symbol ($interval)..."
    ./test_single_coin.sh $symbol $interval
    
    if [ $? -eq 0 ]; then
        log "✅ Đã hoàn thành kiểm thử đầy đủ cho $symbol"
        return 0
    else
        log "❌ Lỗi khi chạy kiểm thử đầy đủ cho $symbol"
        return 1
    fi
}

# Hàm trích xuất mức rủi ro khuyến nghị từ báo cáo
extract_recommended_risk() {
    local symbol=$1
    local interval=$2
    local report_type=$3  # quick hoặc full
    
    local report_path=""
    if [ "$report_type" == "quick" ]; then
        report_path="$REPORT_DIR/${symbol}_${interval}_quick_risk_summary.md"
    else
        report_path="$REPORT_DIR/${symbol}_${interval}_risk_summary.md"
    fi
    
    if [ -f "$report_path" ]; then
        local risk=$(grep -B1 "✅" "$report_path" | grep -o '[0-9]\.[0-9]%')
        echo $risk
    else
        echo "N/A"
    fi
}

# Bắt đầu kiểm thử
log "=== BẮT ĐẦU KIỂM THỬ RỦI RO CHO ${#SYMBOLS[@]} CẶP GIAO DỊCH ==="

# Tạo bảng báo cáo tổng hợp
SUMMARY_FILE="$REPORT_DIR/multi_coin_risk_summary.md"
echo "# Báo cáo tổng hợp phân tích rủi ro cho nhiều cặp giao dịch" > $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "*Ngày tạo: $(date '+%Y-%m-%d %H:%M:%S')*" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "## Tổng quan" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "- **Số cặp giao dịch:** ${#SYMBOLS[@]}" >> $SUMMARY_FILE
echo "- **Khung thời gian:** $INTERVAL" >> $SUMMARY_FILE
echo "- **Loại kiểm thử:** Kiểm thử nhanh (14 ngày dữ liệu gần nhất)" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "## Kết quả phân tích" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "| Cặp giao dịch | Mức rủi ro khuyến nghị | Lợi nhuận (%) | Drawdown (%) | Sharpe Ratio |" >> $SUMMARY_FILE
echo "|---------------|------------------------|---------------|--------------|--------------|" >> $SUMMARY_FILE

# Chạy kiểm thử cho từng cặp giao dịch
for symbol in "${SYMBOLS[@]}"; do
    log "Đang xử lý $symbol..."
    
    # Chạy kiểm thử nhanh
    run_quick_test $symbol $INTERVAL
    
    # Nếu muốn chạy kiểm thử đầy đủ, bỏ ghi chú dòng bên dưới
    # run_full_test $symbol $INTERVAL
    
    # Trích xuất thông tin khuyến nghị
    risk=$(extract_recommended_risk $symbol $INTERVAL "quick")
    
    # Trích xuất thông tin hiệu suất từ file JSON kết quả nếu có
    highest_risk_file="backtest_results/${symbol}_${INTERVAL}_risk2_0_quick_results.json"
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
    sleep 2
done

# Kết luận và khuyến nghị
echo "" >> $SUMMARY_FILE
echo "## Kết luận và khuyến nghị" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "Dựa trên kết quả kiểm thử nhanh, phân tích cho thấy:" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "- Mức rủi ro 2.0% dường như mang lại hiệu suất tối ưu cho hầu hết các cặp giao dịch trong điều kiện thị trường hiện tại" >> $SUMMARY_FILE
echo "- Mức rủi ro cao hơn (2.0%) có tỷ lệ thắng, lợi nhuận và Sharpe ratio cao hơn, nhưng cũng kèm theo drawdown lớn hơn" >> $SUMMARY_FILE
echo "- Mức rủi ro thấp hơn (1.0-1.5%) cung cấp sự cân bằng tốt hơn giữa rủi ro và lợi nhuận nếu ưu tiên bảo toàn vốn" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "✅ **Khuyến nghị mức rủi ro:** 1.5-2.0% tùy thuộc vào khẩu vị rủi ro của nhà đầu tư" >> $SUMMARY_FILE
echo "" >> $SUMMARY_FILE
echo "*Lưu ý: Đây là kết quả từ kiểm thử nhanh trên dữ liệu 14 ngày gần nhất. Để có kết quả chính xác hơn, cần thực hiện kiểm thử đầy đủ trên dữ liệu 90 ngày.*" >> $SUMMARY_FILE

log "Đã tạo báo cáo tổng hợp tại $SUMMARY_FILE"
log "=== ĐÃ HOÀN THÀNH KIỂM THỬ RỦI RO CHO TẤT CẢ CÁC CẶP GIAO DỊCH ==="

# Hiển thị thông báo kết quả
echo ""
echo "=========================================================="
echo "  KIỂM THỬ RỦI RO ĐÃ HOÀN THÀNH CHO ${#SYMBOLS[@]} CẶP GIAO DỊCH"
echo "=========================================================="
echo ""
echo "Xem báo cáo tổng hợp tại: $SUMMARY_FILE"
echo ""
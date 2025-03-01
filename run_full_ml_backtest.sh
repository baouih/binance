#!/bin/bash

# Script tự động hóa toàn bộ quy trình ML backtest
# Script này tự động hóa các bước sau:
# 1. Tạo dữ liệu mẫu
# 2. Chạy ML backtest trên các khoảng thời gian khác nhau
# 3. Phân tích hiệu suất và tạo báo cáo

# Cài đặt
SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT"
TIMEFRAMES="1h,4h,1d"
DATA_DAYS=180
REAL_DATA_DIR="real_data"
ML_RESULTS_DIR="ml_results"
ML_CHARTS_DIR="ml_charts"
ML_MODELS_DIR="ml_models"
REPORT_DIR="reports"

# Các biến môi trường
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Tạo thư mục
mkdir -p $REAL_DATA_DIR $ML_RESULTS_DIR $ML_CHARTS_DIR $ML_MODELS_DIR $REPORT_DIR

# Hàm ghi log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Hàm kiểm tra kết quả
check_result() {
    if [ $? -eq 0 ]; then
        log "✅ $1 thành công"
    else
        log "❌ $1 thất bại"
        exit 1
    fi
}

# Bước 1: Tạo dữ liệu mẫu
log "==== Bắt đầu tạo dữ liệu mẫu ===="
python generate_datasets.py --symbols $SYMBOLS --timeframes $TIMEFRAMES --days $DATA_DAYS --output-dir $REAL_DATA_DIR
check_result "Tạo dữ liệu mẫu"

# Kiểm tra nếu dữ liệu đã được tạo
if [ ! -f "$REAL_DATA_DIR/fetch_results.json" ]; then
    log "❌ Không tìm thấy file kết quả fetch_results.json, dữ liệu mẫu có thể không được tạo đúng."
    exit 1
fi

# Lấy danh sách symbols và timeframes từ kết quả
IFS=',' read -r -a SYMBOL_ARRAY <<< "$SYMBOLS"
IFS=',' read -r -a TIMEFRAME_ARRAY <<< "$TIMEFRAMES"
PERIODS=("1_month" "3_months" "6_months")
DAYS_PREDICT=(1 3 5)
MODELS=("random_forest" "gradient_boosting")

# In thông tin
log "Symbols: ${SYMBOL_ARRAY[*]}"
log "Timeframes: ${TIMEFRAME_ARRAY[*]}"
log "Periods: ${PERIODS[*]}"
log "Prediction days: ${DAYS_PREDICT[*]}"
log "Models: ${MODELS[*]}"

# Bước 2: Chạy ML backtest
log "==== Bắt đầu chạy ML backtest ===="

# Đếm tổng số công việc
TOTAL_JOBS=$((${#SYMBOL_ARRAY[@]} * ${#TIMEFRAME_ARRAY[@]} * ${#PERIODS[@]} * ${#DAYS_PREDICT[@]} * ${#MODELS[@]}))
CURRENT_JOB=0

for symbol in "${SYMBOL_ARRAY[@]}"; do
    for timeframe in "${TIMEFRAME_ARRAY[@]}"; do
        for period in "${PERIODS[@]}"; do
            for days in "${DAYS_PREDICT[@]}"; do
                for model in "${MODELS[@]}"; do
                    CURRENT_JOB=$((CURRENT_JOB + 1))
                    log "[$CURRENT_JOB/$TOTAL_JOBS] Backtest $symbol $timeframe (period: $period, predict: ${days}d, model: $model)"
                    
                    # Chạy backtest
                    python run_period_ml_backtest.py \
                        --symbol $symbol \
                        --timeframe $timeframe \
                        --period $period \
                        --prediction_days $days \
                        --model_type $model \
                        --data_folder $REAL_DATA_DIR \
                        --output_folder $ML_RESULTS_DIR \
                        --charts_folder $ML_CHARTS_DIR \
                        --models_folder $ML_MODELS_DIR
                    
                    # Kiểm tra kết quả
                    if [ $? -eq 0 ]; then
                        log "  ✅ Backtest thành công"
                    else
                        log "  ⚠️ Backtest thất bại, tiếp tục với mô hình tiếp theo..."
                    fi
                done
            done
        done
    done
done

# Bước 3: Phân tích hiệu suất
log "==== Bắt đầu phân tích hiệu suất ML ===="
python analyze_ml_performance.py --results_dir $ML_RESULTS_DIR --charts_dir $ML_CHARTS_DIR --output_report $REPORT_DIR/ml_performance_report.html
check_result "Phân tích hiệu suất ML"

# Kết thúc
log "==== Toàn bộ quy trình ML backtest hoàn thành ===="
log "Kết quả được lưu tại:"
log "- Dữ liệu: $REAL_DATA_DIR"
log "- Kết quả ML: $ML_RESULTS_DIR"
log "- Biểu đồ: $ML_CHARTS_DIR"
log "- Mô hình: $ML_MODELS_DIR" 
log "- Báo cáo: $REPORT_DIR/ml_performance_report.html"

# Đặt quyền thực thi
chmod +x run_full_ml_backtest.sh
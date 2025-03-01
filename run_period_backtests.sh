#!/bin/bash
# Script để chạy backtest với các khoảng thời gian 3, 6 và 9 tháng

echo "===== BẮT ĐẦU BACKTEST THEO KHOẢNG THỜI GIAN ====="

# Cặp giao dịch để backtest
SYMBOL="BTCUSDT"

# Khung thời gian chính
INTERVAL="1h"

# Khung thời gian phụ
SECONDARY_INTERVALS="4h,1d"

# Chiến lược
STRATEGY="auto"

# Cấu hình tài khoản
BALANCE=10000
LEVERAGE=5
RISK=1.0

# Quản lý vốn và rủi ro
POSITION_SIZING="dynamic"
RISK_METHOD="adaptive"
STOP_LOSS=5.0
TAKE_PROFIT=15.0
TRAILING_STOP="true"

# Thư mục dữ liệu
DATA_DIR="test_data"

# Tính ngày bắt đầu và kết thúc
END_DATE=$(date +%Y-%m-%d)

# Backtest 3 tháng
START_DATE_3M=$(date -d "$END_DATE -3 months" +%Y-%m-%d)
echo "===== BACKTEST 3 THÁNG ($START_DATE_3M đến $END_DATE) ====="
python enhanced_backtest.py \
  --symbol $SYMBOL \
  --interval $INTERVAL \
  --secondary_intervals $SECONDARY_INTERVALS \
  --strategy $STRATEGY \
  --balance $BALANCE \
  --leverage $LEVERAGE \
  --risk $RISK \
  --position_sizing $POSITION_SIZING \
  --risk_method $RISK_METHOD \
  --stop_loss $STOP_LOSS \
  --take_profit $TAKE_PROFIT \
  --trailing_stop $TRAILING_STOP \
  --data_dir $DATA_DIR \
  --start_date $START_DATE_3M \
  --end_date $END_DATE \
  --output_prefix "3month"

# Backtest 6 tháng
START_DATE_6M=$(date -d "$END_DATE -6 months" +%Y-%m-%d)
echo "===== BACKTEST 6 THÁNG ($START_DATE_6M đến $END_DATE) ====="
python enhanced_backtest.py \
  --symbol $SYMBOL \
  --interval $INTERVAL \
  --secondary_intervals $SECONDARY_INTERVALS \
  --strategy $STRATEGY \
  --balance $BALANCE \
  --leverage $LEVERAGE \
  --risk $RISK \
  --position_sizing $POSITION_SIZING \
  --risk_method $RISK_METHOD \
  --stop_loss $STOP_LOSS \
  --take_profit $TAKE_PROFIT \
  --trailing_stop $TRAILING_STOP \
  --data_dir $DATA_DIR \
  --start_date $START_DATE_6M \
  --end_date $END_DATE \
  --output_prefix "6month"

# Backtest 9 tháng
START_DATE_9M=$(date -d "$END_DATE -9 months" +%Y-%m-%d)
echo "===== BACKTEST 9 THÁNG ($START_DATE_9M đến $END_DATE) ====="
python enhanced_backtest.py \
  --symbol $SYMBOL \
  --interval $INTERVAL \
  --secondary_intervals $SECONDARY_INTERVALS \
  --strategy $STRATEGY \
  --balance $BALANCE \
  --leverage $LEVERAGE \
  --risk $RISK \
  --position_sizing $POSITION_SIZING \
  --risk_method $RISK_METHOD \
  --stop_loss $STOP_LOSS \
  --take_profit $TAKE_PROFIT \
  --trailing_stop $TRAILING_STOP \
  --data_dir $DATA_DIR \
  --start_date $START_DATE_9M \
  --end_date $END_DATE \
  --output_prefix "9month"

echo "===== ĐÃ HOÀN THÀNH BACKTEST THEO KHOẢNG THỜI GIAN ====="
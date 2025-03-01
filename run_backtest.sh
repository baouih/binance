#!/bin/bash
# Script để chạy backtest nâng cao với dữ liệu thực từ Binance

echo "===== BẮT ĐẦU BACKTEST NÂNG CAO ====="

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

# Chạy backtest
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
  --data_dir $DATA_DIR

echo "===== ĐÃ HOÀN THÀNH BACKTEST ====="
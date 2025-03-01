#!/bin/bash
# Script để lấy dữ liệu từ Binance Testnet cho backtesting

echo "===== BẮT ĐẦU LẤY DỮ LIỆU BINANCE TESTNET ====="

# Cặp giao dịch phổ biến
SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,DOTUSDT,AVAXUSDT"

# Khung thời gian đa dạng
INTERVALS="1m,5m,15m,30m,1h,4h,1d"

# Số ngày dữ liệu
DAYS=90

# Chạy script python để lấy dữ liệu
python test_data_fetcher.py --symbols $SYMBOLS --intervals $INTERVALS --days $DAYS --testnet true

echo "===== ĐÃ HOÀN THÀNH LẤY DỮ LIỆU ====="
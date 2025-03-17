#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module tải dữ liệu lịch sử từ Binance API

Sử dụng:
python download_historical_data.py BTCUSDT 1h [start_date] [end_date]
"""

import os
import sys
import time
import json
import logging
import argparse
import datetime
import pandas as pd
from typing import List, Dict, Tuple, Any, Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('data_downloader')

def parse_arguments():
    """Xử lý tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Tải dữ liệu lịch sử Binance")
    parser.add_argument("symbol", help="Symbol cần tải (ví dụ: BTCUSDT)")
    parser.add_argument("timeframe", help="Khung thời gian (ví dụ: 1m, 5m, 15m, 1h, 4h, 1d)")
    parser.add_argument("--start", help="Ngày bắt đầu (YYYY-MM-DD)", default="2024-02-01")
    parser.add_argument("--end", help="Ngày kết thúc (YYYY-MM-DD)", default="2024-03-15")
    parser.add_argument("--testnet", help="Sử dụng testnet", action="store_true")
    
    return parser.parse_args()

def get_binance_client(testnet=False):
    """Khởi tạo Binance client"""
    try:
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        
        if not api_key or not api_secret:
            logger.warning("Không tìm thấy API key/secret, sử dụng phương thức không xác thực")
            return Client(None, None, testnet=testnet)
        
        logger.info(f"Khởi tạo Binance client với API key: {api_key[:4]}...{api_key[-4:]}")
        return Client(api_key, api_secret, testnet=testnet)
    
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Binance client: {e}")
        sys.exit(1)

def convert_timeframe_to_interval(timeframe):
    """Chuyển đổi định dạng timeframe sang interval cho Binance API"""
    # Kiểm tra timeframe hợp lệ
    valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    
    if timeframe not in valid_timeframes:
        logger.error(f"Timeframe không hợp lệ: {timeframe}. Các giá trị hợp lệ: {', '.join(valid_timeframes)}")
        sys.exit(1)
    
    return timeframe

def download_klines(client, symbol, interval, start_str, end_str):
    """Tải dữ liệu candlestick từ Binance API"""
    try:
        logger.info(f"Đang tải dữ liệu cho {symbol} ({interval}) từ {start_str} đến {end_str}")
        
        # Convert dates to milliseconds
        start_ts = int(datetime.datetime.strptime(start_str, "%Y-%m-%d").timestamp() * 1000)
        end_ts = int(datetime.datetime.strptime(end_str, "%Y-%m-%d").timestamp() * 1000)
        
        # Tải dữ liệu theo từng phần để tránh vượt quá giới hạn
        all_klines = []
        current_start_ts = start_ts
        
        while current_start_ts < end_ts:
            # Tính thời gian kết thúc cho chunk hiện tại (1000 candlesticks)
            temp_end_ts = min(end_ts, current_start_ts + (1000 * get_interval_ms(interval)))
            
            # Tải dữ liệu
            klines = client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=current_start_ts,
                end_str=temp_end_ts,
                limit=1000
            )
            
            all_klines.extend(klines)
            
            if not klines:
                logger.warning(f"Không có dữ liệu từ {current_start_ts} đến {temp_end_ts}")
                break
            
            # Cập nhật thời gian bắt đầu cho chunk tiếp theo
            current_start_ts = int(klines[-1][0]) + 1
            
            # Ghi log tiến trình
            progress = min(100, int((current_start_ts - start_ts) / (end_ts - start_ts) * 100))
            logger.info(f"Đã tải: {progress}% ({len(all_klines)} candlesticks)")
            
            # Tránh rate limit
            time.sleep(0.5)
        
        return all_klines
    
    except BinanceAPIException as e:
        logger.error(f"Lỗi Binance API: {e}")
        return []
    
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu: {e}", exc_info=True)
        return []

def get_interval_ms(interval):
    """Lấy khoảng thời gian của mỗi interval theo milliseconds"""
    interval_ms = {
        '1m': 60 * 1000,
        '3m': 3 * 60 * 1000,
        '5m': 5 * 60 * 1000,
        '15m': 15 * 60 * 1000,
        '30m': 30 * 60 * 1000,
        '1h': 60 * 60 * 1000,
        '2h': 2 * 60 * 60 * 1000,
        '4h': 4 * 60 * 60 * 1000,
        '6h': 6 * 60 * 60 * 1000,
        '8h': 8 * 60 * 60 * 1000,
        '12h': 12 * 60 * 60 * 1000,
        '1d': 24 * 60 * 60 * 1000,
        '3d': 3 * 24 * 60 * 60 * 1000,
        '1w': 7 * 24 * 60 * 60 * 1000,
        '1M': 30 * 24 * 60 * 60 * 1000
    }
    
    return interval_ms.get(interval, 60 * 60 * 1000)  # Default to 1h

def process_klines(klines):
    """Xử lý dữ liệu klines thành DataFrame"""
    if not klines:
        logger.error("Không có dữ liệu để xử lý")
        return None
    
    columns = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignored'
    ]
    
    # Chuyển đổi thành DataFrame
    df = pd.DataFrame(klines, columns=columns)
    
    # Chuyển đổi kiểu dữ liệu
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Đặt timestamp làm index
    df.set_index('timestamp', inplace=True)
    
    return df

def save_data(df, symbol, interval, start_date, end_date):
    """Lưu dữ liệu vào file"""
    if df is None or df.empty:
        logger.error("Không có dữ liệu để lưu")
        return False
    
    # Tạo thư mục data nếu chưa tồn tại
    data_dir = os.path.join("data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Tạo tên file
    filename = f"{symbol}_{interval}_{start_date}_to_{end_date}.csv"
    filepath = os.path.join(data_dir, filename)
    
    # Lưu vào CSV
    df.to_csv(filepath)
    logger.info(f"Đã lưu dữ liệu vào {filepath} ({len(df)} dòng)")
    
    return True

def main():
    """Hàm chính"""
    # Xử lý tham số
    args = parse_arguments()
    
    # Khởi tạo client
    client = get_binance_client(args.testnet)
    
    # Tải dữ liệu
    interval = convert_timeframe_to_interval(args.timeframe)
    klines = download_klines(client, args.symbol, interval, args.start, args.end)
    
    if not klines:
        logger.error("Không thể tải dữ liệu. Dừng.")
        return 1
    
    # Xử lý dữ liệu
    df = process_klines(klines)
    
    # Lưu dữ liệu
    success = save_data(df, args.symbol, interval, args.start, args.end)
    
    if success:
        logger.info("Đã tải thành công dữ liệu lịch sử")
        return 0
    else:
        logger.error("Lỗi khi lưu dữ liệu")
        return 1

if __name__ == "__main__":
    sys.exit(main())
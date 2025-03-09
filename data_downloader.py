#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tải dữ liệu lịch sử từ Binance API

Script này tải dữ liệu lịch sử giá của các coin từ Binance API
và lưu vào file CSV để sử dụng cho backtest.
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import ccxt

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_download.log')
    ]
)

logger = logging.getLogger('data_downloader')

# Danh sách coin mặc định để tải dữ liệu
DEFAULT_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "LINK/USDT", 
    "DOGE/USDT", "ADA/USDT", "MATIC/USDT", "LTC/USDT", "DOT/USDT", 
    "AVAX/USDT", "ATOM/USDT", "UNI/USDT"
]

# Danh sách khung thời gian để tải dữ liệu
DEFAULT_TIMEFRAMES = ["1d", "4h", "1h"]

def create_exchange(testnet: bool = False):
    """
    Tạo đối tượng exchange

    Args:
        testnet (bool): Sử dụng testnet hay không

    Returns:
        ccxt.Exchange: Đối tượng exchange
    """
    if testnet:
        exchange = ccxt.binance({
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
                'test': True
            }
        })
        exchange.urls['api'] = exchange.urls['test']
    else:
        exchange = ccxt.binance({
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True
            }
        })

    return exchange

def download_historical_data(symbol: str, timeframe: str, start_date: str, end_date: str, 
                            testnet: bool = False, save_dir: str = "data") -> pd.DataFrame:
    """
    Tải dữ liệu lịch sử từ Binance API

    Args:
        symbol (str): Tên cặp tiền (dạng BTC/USDT)
        timeframe (str): Khung thời gian (1d, 4h, 1h, ...)
        start_date (str): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str): Ngày kết thúc (YYYY-MM-DD)
        testnet (bool): Sử dụng testnet hay không
        save_dir (str): Thư mục lưu dữ liệu

    Returns:
        pd.DataFrame: Dữ liệu lịch sử
    """
    # Tạo đối tượng exchange
    exchange = create_exchange(testnet)
    
    # Chuyển đổi ngày thành timestamp (milliseconds)
    start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
    end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
    
    logger.info(f"Đang tải dữ liệu cho {symbol} - {timeframe} từ {start_date} đến {end_date}")
    
    # Binance có giới hạn 1000 candles mỗi lần, nên phải chia nhỏ
    all_candles = []
    current_timestamp = start_timestamp
    
    while current_timestamp < end_timestamp:
        try:
            # Tải dữ liệu
            candles = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=current_timestamp,
                limit=1000
            )
            
            if not candles:
                logger.warning(f"Không có dữ liệu cho {symbol} - {timeframe} từ {datetime.fromtimestamp(current_timestamp/1000)}")
                break
            
            all_candles.extend(candles)
            
            # Cập nhật timestamp cho lần lấy dữ liệu tiếp theo
            current_timestamp = candles[-1][0] + 1
            
            # Thêm khoảng dừng để tránh rate limit
            time.sleep(0.5)
            
            logger.info(f"Đã tải {len(candles)} nến, tổng cộng {len(all_candles)} nến")
            
            # Nếu đã đến ngày kết thúc, dừng lại
            if current_timestamp >= end_timestamp:
                break
        
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu cho {symbol} - {timeframe}: {e}")
            # Thử lại sau 3 giây
            time.sleep(3)
    
    if not all_candles:
        logger.error(f"Không tải được dữ liệu cho {symbol} - {timeframe}")
        return None
    
    # Chuyển đổi sang DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Chuyển đổi timestamp thành datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Loại bỏ các hàng trùng lặp
    df = df.drop_duplicates(subset=['timestamp'])
    
    # Sắp xếp theo timestamp
    df = df.sort_values('timestamp')
    
    # Loại bỏ dữ liệu ngoài phạm vi
    df = df[(df['timestamp'] >= pd.to_datetime(start_date)) & 
            (df['timestamp'] <= pd.to_datetime(end_date))]
    
    # Tạo thư mục lưu dữ liệu
    tf_dir = f"{save_dir}/{timeframe}"
    os.makedirs(tf_dir, exist_ok=True)
    
    # Lưu vào file CSV
    symbol_name = symbol.replace("/", "")
    file_path = f"{tf_dir}/{symbol_name}_{timeframe}.csv"
    df.to_csv(file_path, index=False)
    
    logger.info(f"Đã lưu dữ liệu vào {file_path}, tổng cộng {len(df)} nến")
    
    return df

def download_multiple_symbols(symbols: list, timeframes: list, start_date: str, end_date: str,
                            testnet: bool = False, save_dir: str = "data"):
    """
    Tải dữ liệu lịch sử cho nhiều coin và khung thời gian

    Args:
        symbols (list): Danh sách cặp tiền
        timeframes (list): Danh sách khung thời gian
        start_date (str): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str): Ngày kết thúc (YYYY-MM-DD)
        testnet (bool): Sử dụng testnet hay không
        save_dir (str): Thư mục lưu dữ liệu
    """
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                download_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    testnet=testnet,
                    save_dir=save_dir
                )
                
                # Tạm dừng để tránh rate limit
                time.sleep(1)
            
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu cho {symbol} - {timeframe}: {e}")

def generate_synthetic_data(symbols: list, timeframes: list, start_date: str, end_date: str,
                         save_dir: str = "data"):
    """
    Tạo dữ liệu giả cho các coin và khung thời gian.
    Hàm này được sử dụng khi không thể kết nối tới API Binance.

    Args:
        symbols (list): Danh sách cặp tiền
        timeframes (list): Danh sách khung thời gian
        start_date (str): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str): Ngày kết thúc (YYYY-MM-DD)
        save_dir (str): Thư mục lưu dữ liệu
    """
    # Tạo các thư mục cần thiết
    for timeframe in timeframes:
        tf_dir = f"{save_dir}/{timeframe}"
        os.makedirs(tf_dir, exist_ok=True)
    
    # Tạo dữ liệu giả cho mỗi coin và khung thời gian
    for symbol in symbols:
        symbol_name = symbol.replace("/", "")
        
        # Tạo giá ban đầu khác nhau cho mỗi coin
        if "BTC" in symbol:
            base_price = 50000.0
        elif "ETH" in symbol:
            base_price = 2000.0
        elif "BNB" in symbol:
            base_price = 500.0
        elif "SOL" in symbol:
            base_price = 150.0
        else:
            base_price = np.random.uniform(10.0, 100.0)
        
        for timeframe in timeframes:
            # Tạo các mốc thời gian dựa vào khung thời gian
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            if timeframe == '1d':
                dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
            elif timeframe == '4h':
                dates = pd.date_range(start=start_dt, end=end_dt, freq='4H')
            elif timeframe == '1h':
                dates = pd.date_range(start=start_dt, end=end_dt, freq='H')
            else:
                continue
            
            # Tạo DataFrame
            df = pd.DataFrame(index=dates, columns=['open', 'high', 'low', 'close', 'volume'])
            
            # Tạo dữ liệu giá giả
            price = base_price
            for i in range(len(df)):
                # Tạo biến động giá theo mô hình random walk
                daily_return = np.random.normal(0, 0.02)  # 2% độ lệch chuẩn
                price *= (1 + daily_return)
                
                # Tạo giá open, high, low, close
                daily_open = price * (1 + np.random.uniform(-0.005, 0.005))
                daily_high = max(daily_open, price) * (1 + np.random.uniform(0, 0.01))
                daily_low = min(daily_open, price) * (1 - np.random.uniform(0, 0.01))
                daily_close = price * (1 + np.random.uniform(-0.005, 0.005))
                
                # Tạo volume
                daily_volume = np.random.randint(10000, 100000)
                
                # Cập nhật DataFrame
                df.iloc[i, 0] = daily_open
                df.iloc[i, 1] = daily_high
                df.iloc[i, 2] = daily_low
                df.iloc[i, 3] = daily_close
                df.iloc[i, 4] = daily_volume
            
            # Reset index để timestamp thành cột
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'timestamp'}, inplace=True)
            
            # Lưu vào file CSV
            file_path = f"{save_dir}/{timeframe}/{symbol_name}_{timeframe}.csv"
            df.to_csv(file_path, index=False)
            
            logger.info(f"Đã tạo dữ liệu giả cho {symbol} - {timeframe}, tổng cộng {len(df)} nến")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Tải dữ liệu lịch sử từ Binance API')
    parser.add_argument('--symbols', type=str, nargs='+', default=DEFAULT_SYMBOLS, help='Danh sách cặp tiền')
    parser.add_argument('--timeframes', type=str, nargs='+', default=DEFAULT_TIMEFRAMES, help='Danh sách khung thời gian')
    parser.add_argument('--start', type=str, default='2023-01-01', help='Ngày bắt đầu (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2023-12-31', help='Ngày kết thúc (YYYY-MM-DD)')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng testnet')
    parser.add_argument('--output', type=str, default='data', help='Thư mục lưu dữ liệu')
    parser.add_argument('--synthetic', action='store_true', help='Tạo dữ liệu giả (không kết nối API)')
    args = parser.parse_args()
    
    # Tạo thư mục lưu dữ liệu
    os.makedirs(args.output, exist_ok=True)
    
    # Lưu cấu hình
    config = {
        "symbols": args.symbols,
        "timeframes": args.timeframes,
        "start_date": args.start,
        "end_date": args.end,
        "testnet": args.testnet,
        "output_dir": args.output,
        "synthetic": args.synthetic,
        "download_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(f"{args.output}/download_config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    if args.synthetic:
        logger.info("Đang tạo dữ liệu giả (không kết nối API Binance)")
        generate_synthetic_data(
            symbols=args.symbols,
            timeframes=args.timeframes,
            start_date=args.start,
            end_date=args.end,
            save_dir=args.output
        )
    else:
        logger.info("Đang tải dữ liệu từ Binance API")
        download_multiple_symbols(
            symbols=args.symbols,
            timeframes=args.timeframes,
            start_date=args.start,
            end_date=args.end,
            testnet=args.testnet,
            save_dir=args.output
        )
    
    logger.info(f"Hoàn tất quá trình tải dữ liệu. Dữ liệu được lưu trong thư mục: {args.output}")
    print(f"\nHoàn tất quá trình tải dữ liệu!")
    print(f"Dữ liệu được lưu trong thư mục: {args.output}")
    print(f"Đã tải dữ liệu cho {len(args.symbols)} coin và {len(args.timeframes)} khung thời gian")
    print(f"Giai đoạn: {args.start} đến {args.end}")

if __name__ == "__main__":
    main()
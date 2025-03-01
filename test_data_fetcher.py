#!/usr/bin/env python3
"""
Script để lấy dữ liệu từ Binance Testnet và lưu trữ cho backtesting

Script này giúp lấy dữ liệu thực tế từ Binance Testnet (hoặc Binance thực) trong nhiều khung thời gian 
và lưu trữ để sử dụng cho backtesting với độ chính xác cao hơn.
"""

import os
import sys
import json
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("testnet_data_fetcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("testnet_data_fetcher")

# Tạo thư mục data nếu chưa tồn tại
os.makedirs("test_data", exist_ok=True)

try:
    # Thử import binance_api từ app
    sys.path.append('.')
    from app.binance_api import BinanceAPI
except ImportError:
    try:
        # Thử import từ thư mục gốc
        from binance_api import BinanceAPI
    except ImportError as e:
        logger.error(f"Không thể import BinanceAPI: {str(e)}")
        logger.error("Vui lòng đảm bảo file binance_api.py có trong thư mục app hoặc thư mục gốc")
        sys.exit(1)

def get_testnet_data(symbols: List[str], intervals: List[str], days: int = 90, use_testnet: bool = True) -> Dict:
    """
    Lấy dữ liệu từ Binance Testnet và lưu trữ
    
    Args:
        symbols (List[str]): Danh sách các cặp giao dịch (BTCUSDT, ETHUSDT, ...)
        intervals (List[str]): Danh sách các khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)
        days (int): Số ngày dữ liệu cần lấy
        use_testnet (bool): Có sử dụng Testnet không
        
    Returns:
        Dict: Thống kê về dữ liệu đã lấy
    """
    logger.info(f"Bắt đầu lấy dữ liệu từ {'Binance Testnet' if use_testnet else 'Binance'}")
    logger.info(f"Cặp giao dịch: {symbols}")
    logger.info(f"Khung thời gian: {intervals}")
    logger.info(f"Số ngày dữ liệu: {days}")
    
    # Kết nối API Binance
    binance_api = BinanceAPI(testnet=use_testnet)
    
    # Kiểm tra kết nối
    try:
        server_time = binance_api.get_server_time()
        server_time_str = datetime.fromtimestamp(server_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Kết nối thành công! Server time: {server_time_str}")
    except Exception as e:
        logger.error(f"Lỗi kết nối: {str(e)}")
        return {"error": str(e)}
    
    # Thống kê kết quả
    results = {
        "symbols": {},
        "total_candles": 0,
        "start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "end_time": None
    }
    
    # Lấy dữ liệu
    for symbol in symbols:
        symbol_results = {}
        symbol_dir = os.path.join("test_data", symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        
        for interval in intervals:
            try:
                logger.info(f"Đang lấy dữ liệu {symbol} - {interval}...")
                
                # Tính thời gian bắt đầu
                if interval.endswith('m'):
                    minutes = int(interval[:-1])
                    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                elif interval.endswith('h'):
                    hours = int(interval[:-1])
                    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                elif interval.endswith('d'):
                    days_interval = int(interval[:-1])
                    start_time = int((datetime.now() - timedelta(days=days * 2)).timestamp() * 1000)
                else:
                    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                
                # Lấy dữ liệu
                klines = binance_api.get_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time=start_time,
                    limit=1000  # Maximum
                )
                
                if not klines:
                    logger.warning(f"Không có dữ liệu cho {symbol} - {interval}")
                    symbol_results[interval] = {"status": "error", "count": 0, "message": "No data"}
                    continue
                
                # Tạo DataFrame
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 
                    'volume', 'close_time', 'quote_asset_volume', 
                    'number_of_trades', 'taker_buy_base_asset_volume',
                    'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                # Chuyển đổi dữ liệu
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                # Đặt timestamp làm index
                df.set_index('timestamp', inplace=True)
                
                # Lưu dữ liệu
                file_path = os.path.join(symbol_dir, f"{symbol}_{interval}.csv")
                df.to_csv(file_path)
                
                # Thống kê
                symbol_results[interval] = {
                    "status": "success",
                    "count": len(df),
                    "start_date": df.index[0].strftime('%Y-%m-%d %H:%M:%S'),
                    "end_date": df.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
                    "file_path": file_path
                }
                
                results["total_candles"] += len(df)
                
                logger.info(f"Đã lấy {len(df)} candles cho {symbol} - {interval} từ {df.index[0]} đến {df.index[-1]}")
                
                # Đợi để tránh rate limit
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu {symbol} - {interval}: {str(e)}")
                symbol_results[interval] = {"status": "error", "count": 0, "message": str(e)}
        
        results["symbols"][symbol] = symbol_results
    
    # Lưu kết quả
    results["end_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open("test_data/fetch_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Hoàn thành! Đã lấy tổng cộng {results['total_candles']} candles.")
    logger.info(f"Kết quả đã được lưu vào test_data/fetch_results.json")
    
    return results

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Công cụ lấy dữ liệu từ Binance Testnet')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT',
                        help='Danh sách cặp giao dịch, phân cách bằng dấu phẩy (mặc định: BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT)')
    parser.add_argument('--intervals', type=str, default='1h,4h,1d',
                        help='Danh sách khung thời gian, phân cách bằng dấu phẩy (mặc định: 1h,4h,1d)')
    parser.add_argument('--days', type=int, default=90,
                        help='Số ngày dữ liệu cần lấy (mặc định: 90)')
    parser.add_argument('--testnet', type=str, default='true',
                        choices=['true', 'false'],
                        help='Có sử dụng Testnet không (mặc định: true)')
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(',')
    intervals = args.intervals.split(',')
    days = args.days
    use_testnet = args.testnet.lower() == 'true'
    
    get_testnet_data(symbols, intervals, days, use_testnet)

if __name__ == "__main__":
    main()
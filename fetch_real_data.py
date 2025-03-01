#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tải dữ liệu thực tế từ Binance cho 9 đồng coin và 3 khung thời gian
"""

import os
import json
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from binance.client import Client
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fetch_real_data')

# Tải biến môi trường
load_dotenv()
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

def get_binance_client():
    """Tạo và trả về một client Binance"""
    try:
        client = Client(API_KEY, API_SECRET)
        # Kiểm tra kết nối
        server_time = client.get_server_time()
        logger.info(f"Đã kết nối đến Binance. Server time: {datetime.fromtimestamp(server_time['serverTime']/1000)}")
        return client
    except Exception as e:
        logger.error(f"Lỗi kết nối đến Binance: {str(e)}")
        return None

def get_historical_klines(client, symbol, interval, start_str, end_str=None):
    """Lấy dữ liệu lịch sử từ Binance"""
    try:
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_str,
            end_str=end_str
        )
        return klines
    except Exception as e:
        logger.error(f"Lỗi lấy dữ liệu lịch sử cho {symbol} {interval}: {str(e)}")
        return []

def klines_to_dataframe(klines):
    """Chuyển đổi dữ liệu klines sang DataFrame"""
    columns = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ]
    df = pd.DataFrame(klines, columns=columns)
    
    # Chuyển đổi kiểu dữ liệu
    numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                      'quote_asset_volume', 'number_of_trades',
                      'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
    
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col])
    
    # Chuyển đổi timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    return df

def save_to_csv(df, symbol, interval, output_dir='data'):
    """Lưu DataFrame vào file CSV"""
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = f"{output_dir}/{symbol}_{interval}.csv"
    df.to_csv(file_path, index=False)
    logger.info(f"Đã lưu {len(df)} dòng dữ liệu vào {file_path}")
    return file_path

def main():
    # Danh sách 9 đồng coin cần lấy dữ liệu
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT',
        'SOLUSDT', 'DOGEUSDT', 'XRPUSDT',
        'ADAUSDT', 'DOTUSDT', 'LINKUSDT'
    ]
    
    # Danh sách khung thời gian
    intervals = ['1h', '4h', '1d']
    
    # Thời gian bắt đầu cho các khoảng thời gian khác nhau
    now = datetime.now()
    time_ranges = {
        '1 month': (now - timedelta(days=30)).strftime('%Y-%m-%d'),
        '3 months': (now - timedelta(days=90)).strftime('%Y-%m-%d'),
        '6 months': (now - timedelta(days=180)).strftime('%Y-%m-%d')
    }
    
    # Lấy client Binance
    client = get_binance_client()
    if not client:
        logger.error("Không thể tạo client Binance. Thoát chương trình.")
        return
    
    # Tạo thư mục dữ liệu
    data_dir = 'real_data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    results = {
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "symbols": {},
        "total_files": 0,
        "total_candles": 0
    }
    
    # Lấy dữ liệu cho từng đồng coin, khung thời gian và khoảng thời gian
    for symbol in symbols:
        results["symbols"][symbol] = {}
        
        for interval in intervals:
            results["symbols"][symbol][interval] = {}
            
            for time_label, start_time in time_ranges.items():
                time_key = time_label.replace(' ', '_')
                range_dir = f"{data_dir}/{time_key}"
                
                if not os.path.exists(range_dir):
                    os.makedirs(range_dir)
                
                logger.info(f"Đang lấy dữ liệu {symbol} {interval} cho {time_label}...")
                
                klines = get_historical_klines(
                    client=client,
                    symbol=symbol,
                    interval=interval,
                    start_str=start_time
                )
                
                if klines:
                    df = klines_to_dataframe(klines)
                    file_path = save_to_csv(df, symbol, interval, range_dir)
                    
                    results["symbols"][symbol][interval][time_key] = {
                        "file_path": file_path,
                        "candles": len(df),
                        "start_date": df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
                        "end_date": df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    results["total_files"] += 1
                    results["total_candles"] += len(df)
                    
                    # Tránh rate limit
                    time.sleep(1)
                else:
                    logger.warning(f"Không thể lấy dữ liệu cho {symbol} {interval} {time_label}")
                    results["symbols"][symbol][interval][time_key] = {
                        "file_path": None,
                        "candles": 0,
                        "error": "Failed to retrieve data"
                    }
    
    # Lưu báo cáo kết quả
    with open(f"{data_dir}/fetch_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Hoàn tất! Đã tải {results['total_files']} file với tổng cộng {results['total_candles']} nến.")
    logger.info(f"Báo cáo chi tiết được lưu tại {data_dir}/fetch_results.json")

if __name__ == "__main__":
    main()
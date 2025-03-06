#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script tải dữ liệu lịch sử cho tất cả các cặp tiền từ Binance

Script này sẽ tải dữ liệu lịch sử 3 tháng gần nhất cho tất cả các cặp tiền 
được cấu hình, lưu vào định dạng CSV cho việc backtest.
"""

import os
import json
import time
import logging
import sys
from datetime import datetime, timedelta
from binance_api import BinanceAPI
import pandas as pd

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fetch_data.log')
    ]
)

logger = logging.getLogger('data_fetcher')

# Thư mục lưu dữ liệu
DATA_DIR = 'test_data'
ACCOUNT_CONFIG_PATH = 'account_config.json'

def load_account_config():
    """
    Tải cấu hình tài khoản và danh sách cặp tiền
    
    Returns:
        dict: Cấu hình tài khoản
    """
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình tài khoản: {str(e)}")
        return None

def get_symbols_to_fetch():
    """
    Lấy danh sách cặp tiền cần tải dữ liệu
    
    Returns:
        list: Danh sách các cặp tiền
    """
    config = load_account_config()
    if not config:
        # Danh sách mặc định nếu không tải được cấu hình
        return ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
                'DOGEUSDT', 'DOTUSDT', 'LINKUSDT', 'XRPUSDT', 'LTCUSDT',
                'AVAXUSDT', 'MATICUSDT', 'TRXUSDT', 'NEARUSDT']
    
    return config.get('symbols', [])

def get_timeframes():
    """
    Lấy danh sách khung thời gian cần tải
    
    Returns:
        list: Danh sách các khung thời gian
    """
    config = load_account_config()
    if not config:
        # Danh sách mặc định nếu không tải được cấu hình
        return ['1m', '5m', '15m', '1h', '4h', '1d']
    
    return config.get('timeframes', [])

def calculate_date_ranges():
    """
    Tính toán phạm vi ngày cho 3 tháng gần nhất
    
    Returns:
        list: Danh sách các phạm vi ngày (tháng hiện tại và 2 tháng trước)
    """
    today = datetime.now()
    
    # Tháng hiện tại
    current_month_start = datetime(today.year, today.month, 1)
    current_month_end = today
    
    # Tháng trước
    if today.month == 1:
        prev_month_start = datetime(today.year - 1, 12, 1)
        prev_month_end = datetime(today.year, today.month, 1) - timedelta(days=1)
    else:
        prev_month_start = datetime(today.year, today.month - 1, 1)
        prev_month_end = current_month_start - timedelta(days=1)
    
    # 2 tháng trước
    if today.month == 1:
        prev2_month_start = datetime(today.year - 1, 11, 1)
        prev2_month_end = datetime(today.year - 1, 12, 1) - timedelta(days=1)
    elif today.month == 2:
        prev2_month_start = datetime(today.year - 1, 12, 1)
        prev2_month_end = datetime(today.year, 1, 1) - timedelta(days=1)
    else:
        prev2_month_start = datetime(today.year, today.month - 2, 1)
        prev2_month_end = prev_month_start - timedelta(days=1)
    
    return [
        {
            'name': f"{today.year}_{today.month:02d}",
            'start': current_month_start.strftime('%Y-%m-%d'),
            'end': current_month_end.strftime('%Y-%m-%d')
        },
        {
            'name': f"{prev_month_start.year}_{prev_month_start.month:02d}",
            'start': prev_month_start.strftime('%Y-%m-%d'),
            'end': prev_month_end.strftime('%Y-%m-%d')
        },
        {
            'name': f"{prev2_month_start.year}_{prev2_month_start.month:02d}",
            'start': prev2_month_start.strftime('%Y-%m-%d'),
            'end': prev2_month_end.strftime('%Y-%m-%d')
        }
    ]

def ensure_data_directory(symbol):
    """
    Đảm bảo thư mục lưu dữ liệu tồn tại
    
    Args:
        symbol (str): Mã cặp tiền
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, symbol), exist_ok=True)

def format_klines_data(klines_data):
    """
    Định dạng dữ liệu candles thành DataFrame
    
    Args:
        klines_data (list): Dữ liệu candles từ API
        
    Returns:
        pd.DataFrame: Dữ liệu đã định dạng
    """
    # Định nghĩa cấu trúc cột
    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
               'close_time', 'quote_asset_volume', 'number_of_trades',
               'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
    
    # Tạo DataFrame
    df = pd.DataFrame(klines_data, columns=columns)
    
    # Chuyển đổi kiểu dữ liệu
    numeric_columns = ['open', 'high', 'low', 'close', 'volume',
                      'quote_asset_volume', 'taker_buy_base_asset_volume', 
                      'taker_buy_quote_asset_volume']
    
    df[numeric_columns] = df[numeric_columns].astype(float)
    df['number_of_trades'] = df['number_of_trades'].astype(int)
    
    # Chuyển đổi timestamp thành datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    # Đặt timestamp làm index
    df.set_index('timestamp', inplace=True)
    
    return df

def fetch_and_save_data(binance_api, symbol, timeframe, start_date, end_date, file_path):
    """
    Tải và lưu dữ liệu lịch sử cho một cặp tiền và khung thời gian
    
    Args:
        binance_api (BinanceAPI): Đối tượng BinanceAPI
        symbol (str): Mã cặp tiền
        timeframe (str): Khung thời gian
        start_date (str): Ngày bắt đầu (định dạng 'YYYY-MM-DD')
        end_date (str): Ngày kết thúc (định dạng 'YYYY-MM-DD')
        file_path (str): Đường dẫn file lưu dữ liệu
        
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    try:
        # Chuyển đổi định dạng ngày
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Chuyển đổi sang timestamp (ms)
        start_timestamp = int(start_datetime.timestamp() * 1000)
        end_timestamp = int(end_datetime.timestamp() * 1000)
        
        # Tải dữ liệu
        logger.info(f"Đang tải dữ liệu {symbol} {timeframe} từ {start_date} đến {end_date}")
        klines_data = binance_api.get_historical_klines(
            symbol=symbol,
            interval=timeframe,
            start_time=start_timestamp,
            end_time=end_timestamp
        )
        
        if not klines_data:
            logger.warning(f"Không có dữ liệu cho {symbol} {timeframe} từ {start_date} đến {end_date}")
            return False
        
        # Định dạng dữ liệu
        df = format_klines_data(klines_data)
        
        # Lưu vào file CSV
        df.to_csv(file_path)
        logger.info(f"Đã lưu {len(df)} candles vào {file_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu {symbol} {timeframe}: {str(e)}")
        return False

def merge_or_append_csv(new_file_path, target_path):
    """
    Gộp hoặc nối dữ liệu mới vào file đích
    
    Args:
        new_file_path (str): Đường dẫn file dữ liệu mới
        target_path (str): Đường dẫn file đích
        
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    try:
        # Đọc dữ liệu mới
        df_new = pd.read_csv(new_file_path, index_col='timestamp', parse_dates=True)
        
        # Kiểm tra xem file đích đã tồn tại chưa
        if os.path.exists(target_path):
            # Đọc dữ liệu cũ
            df_old = pd.read_csv(target_path, index_col='timestamp', parse_dates=True)
            
            # Gộp dữ liệu
            df_merged = pd.concat([df_old, df_new])
            
            # Loại bỏ dữ liệu trùng lặp
            df_merged = df_merged[~df_merged.index.duplicated(keep='last')]
            
            # Sắp xếp theo thời gian
            df_merged.sort_index(inplace=True)
            
            # Lưu lại vào file đích
            df_merged.to_csv(target_path)
            logger.info(f"Đã cập nhật {len(df_merged)} candles vào {target_path}")
        else:
            # Nếu file chưa tồn tại, copy luôn file mới
            df_new.to_csv(target_path)
            logger.info(f"Đã tạo mới {len(df_new)} candles vào {target_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi gộp dữ liệu vào {target_path}: {str(e)}")
        return False

def fetch_all_data():
    """
    Tải dữ liệu cho tất cả các cặp tiền và khung thời gian
    """
    # Khởi tạo Binance API
    binance_api = BinanceAPI()
    
    # Lấy danh sách cặp tiền và khung thời gian
    symbols = get_symbols_to_fetch()
    timeframes = get_timeframes()
    date_ranges = calculate_date_ranges()
    
    logger.info(f"Chuẩn bị tải dữ liệu cho {len(symbols)} cặp tiền và {len(timeframes)} khung thời gian")
    logger.info(f"Cặp tiền: {symbols}")
    logger.info(f"Khung thời gian: {timeframes}")
    logger.info(f"Phạm vi ngày: {date_ranges}")
    
    # Đếm số lượng đã tải thành công
    success_count = 0
    total_count = len(symbols) * len(timeframes) * len(date_ranges)
    
    # Kết quả tải dữ liệu
    results = {}
    
    # Tải dữ liệu cho từng cặp tiền và khung thời gian
    for symbol in symbols:
        # Tạo thư mục lưu dữ liệu
        ensure_data_directory(symbol)
        
        # Tải dữ liệu cho từng khung thời gian
        for timeframe in timeframes:
            # Tải dữ liệu cho từng phạm vi ngày
            monthly_files = []
            
            for date_range in date_ranges:
                # Tạo tên file dữ liệu tạm thời
                tmp_file_path = os.path.join(DATA_DIR, symbol, f"{symbol}_{timeframe}_{date_range['name']}_tmp.csv")
                
                # Tải và lưu dữ liệu
                success = fetch_and_save_data(
                    binance_api=binance_api,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=date_range['start'],
                    end_date=date_range['end'],
                    file_path=tmp_file_path
                )
                
                if success:
                    monthly_files.append(tmp_file_path)
                    success_count += 1
                
                # Tạm dừng để tránh vượt quá giới hạn API
                time.sleep(1)
            
            # Gộp dữ liệu từ các tháng thành một file
            if monthly_files:
                target_file = os.path.join(DATA_DIR, f"{symbol}_{timeframe}.csv")
                
                # Gộp từng file theo thứ tự
                for monthly_file in monthly_files:
                    merge_or_append_csv(monthly_file, target_file)
                    
                    # Xóa file tạm
                    try:
                        os.remove(monthly_file)
                    except:
                        pass
                
                # Lưu kết quả
                results[f"{symbol}_{timeframe}"] = {
                    'status': 'success',
                    'file_path': target_file
                }
            else:
                results[f"{symbol}_{timeframe}"] = {
                    'status': 'failed',
                    'reason': 'Không tải được dữ liệu cho bất kỳ tháng nào'
                }
    
    # Lưu kết quả tải dữ liệu
    with open(os.path.join(DATA_DIR, 'fetch_results.json'), 'w') as f:
        json.dump(results, f, indent=4)
    
    logger.info(f"Đã hoàn thành tải dữ liệu: {success_count}/{total_count} thành công")

if __name__ == "__main__":
    logger.info("Bắt đầu tải dữ liệu lịch sử...")
    fetch_all_data()
    logger.info("Hoàn thành tải dữ liệu lịch sử!")
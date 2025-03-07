"""
Download dữ liệu lịch sử cho tất cả các cặp tiền

Script này sẽ download dữ liệu 3 tháng gần nhất cho tất cả các cặp tiền
được liệt kê trong account_config.json
"""

import os
import sys
import time
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('download_data')

def load_symbols_from_config() -> List[str]:
    """
    Đọc danh sách cặp tiền từ file cấu hình
    
    Returns:
        List[str]: Danh sách các cặp tiền
    """
    try:
        with open('account_config.json', 'r') as f:
            config = json.load(f)
            return config.get('symbols', [])
    except Exception as e:
        logger.error(f"Lỗi khi đọc file cấu hình: {str(e)}")
        return ["BTCUSDT", "ETHUSDT"]  # Mặc định nếu không đọc được config

def download_klines(symbol: str, interval: str = '1h', 
                  start_time: Optional[int] = None, 
                  limit: int = 1000) -> pd.DataFrame:
    """
    Download dữ liệu klines từ Binance API
    
    Args:
        symbol (str): Cặp tiền (ví dụ: BTCUSDT)
        interval (str): Khung thời gian (ví dụ: 1h, 4h, 1d)
        start_time (int, optional): Thời gian bắt đầu tính bằng milliseconds
        limit (int): Số lượng nến tối đa (tối đa 1000)
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu klines
    """
    base_url = "https://api.binance.com/api/v3/klines"
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    if start_time:
        params["startTime"] = start_time
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if isinstance(data, dict) and 'code' in data:
            logger.error(f"Lỗi API: {data}")
            return pd.DataFrame()
        
        # Tạo DataFrame từ dữ liệu
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Chuyển đổi kiểu dữ liệu
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                          'quote_asset_volume', 'taker_buy_base_asset_volume', 
                          'taker_buy_quote_asset_volume']
        
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col])
        
        # Chuyển đổi timestamp sang datetime
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
        
        return df
        
    except Exception as e:
        logger.error(f"Lỗi khi download dữ liệu {symbol} {interval}: {str(e)}")
        return pd.DataFrame()

def download_historical_data(symbol: str, interval: str = '1h', months: int = 3) -> pd.DataFrame:
    """
    Download dữ liệu lịch sử trong khoảng thời gian xác định
    
    Args:
        symbol (str): Cặp tiền
        interval (str): Khung thời gian
        months (int): Số tháng dữ liệu cần lấy
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu lịch sử
    """
    logger.info(f"Đang download dữ liệu {months} tháng cho {symbol} {interval}")
    
    # Tính thời gian bắt đầu (X tháng trước)
    end_time = datetime.now()
    start_time = end_time - timedelta(days=30 * months)
    start_timestamp = int(start_time.timestamp() * 1000)
    
    all_data = []
    current_start = start_timestamp
    
    while True:
        # Download 1000 nến mỗi lần (maximum limit)
        df_chunk = download_klines(symbol, interval, current_start, 1000)
        
        if df_chunk.empty:
            break
        
        all_data.append(df_chunk)
        logger.info(f"Đã download {len(df_chunk)} nến cho {symbol} {interval} từ {df_chunk['timestamp'].min()}")
        
        # Kiểm tra xem đã đến thời gian hiện tại chưa
        last_timestamp = df_chunk['open_time'].max()
        if last_timestamp >= end_time.timestamp() * 1000:
            break
        
        # Cập nhật thời gian bắt đầu cho lần tiếp theo
        current_start = last_timestamp + 1
        
        # Giới hạn tần suất request API
        time.sleep(1)
    
    if not all_data:
        logger.error(f"Không có dữ liệu cho {symbol} {interval}")
        return pd.DataFrame()
    
    # Ghép các chunk lại với nhau
    df = pd.concat(all_data, ignore_index=True)
    
    # Loại bỏ các bản ghi trùng lặp
    df = df.drop_duplicates(subset=['open_time'])
    
    # Sắp xếp theo thời gian
    df = df.sort_values('timestamp')
    
    return df

def save_data(df: pd.DataFrame, symbol: str, interval: str = '1h') -> str:
    """
    Lưu dữ liệu vào file CSV
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu
        symbol (str): Cặp tiền
        interval (str): Khung thời gian
        
    Returns:
        str: Đường dẫn file
    """
    # Tạo thư mục data nếu chưa tồn tại
    os.makedirs('data', exist_ok=True)
    
    # Đường dẫn file
    file_path = f'data/{symbol}_{interval}.csv'
    
    try:
        # Lưu dữ liệu
        df.to_csv(file_path, index=False)
        logger.info(f"Đã lưu dữ liệu {symbol} {interval} vào {file_path} ({len(df)} dòng)")
        return file_path
    except Exception as e:
        logger.error(f"Lỗi khi lưu dữ liệu {symbol} {interval}: {str(e)}")
        return ""

def main():
    """
    Hàm chính
    """
    logger.info("Bắt đầu download dữ liệu lịch sử")
    
    # Đọc danh sách cặp tiền từ config
    symbols = load_symbols_from_config()
    logger.info(f"Danh sách cặp tiền: {symbols}")
    
    # Khung thời gian cần download
    intervals = ['1h']
    
    # Số tháng dữ liệu
    months = 3
    
    # Danh sách các cặp tiền đã có dữ liệu
    existing_files = [os.path.basename(f).split('_')[0] for f in os.listdir('data') if f.endswith('_1h.csv')]
    logger.info(f"Các cặp tiền đã có dữ liệu: {existing_files}")
    
    # Download dữ liệu cho các cặp tiền chưa có
    for symbol in symbols:
        if symbol in existing_files:
            logger.info(f"Đã có dữ liệu cho {symbol}, bỏ qua")
            continue
            
        for interval in intervals:
            df = download_historical_data(symbol, interval, months)
            
            if not df.empty:
                save_data(df, symbol, interval)
            
            # Giới hạn tần suất request API
            time.sleep(2)
    
    logger.info("Đã hoàn thành download dữ liệu lịch sử")

if __name__ == "__main__":
    main()
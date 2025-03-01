#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo bộ dữ liệu mẫu cho ML backtest

Script này tạo dữ liệu giá từ Binance (hoặc mô phỏng nếu không có kết nối),
chia thành các giai đoạn (1 tháng, 3 tháng, 6 tháng) để sử dụng cho ML backtest.
"""

import os
import json
import argparse
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def try_load_binance_data(symbol: str, interval: str, 
                         start_date: str, end_date: str) -> pd.DataFrame:
    """
    Cố gắng tải dữ liệu từ Binance API
    
    Args:
        symbol (str): Mã cặp giao dịch (ví dụ: BTCUSDT)
        interval (str): Khung thời gian (ví dụ: 1h, 4h, 1d)
        start_date (str): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str): Ngày kết thúc (YYYY-MM-DD)
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu giá, None nếu có lỗi
    """
    try:
        # Thử import cả python-binance và tự xử lý HTTP request
        try:
            # Thử sử dụng thư viện python-binance
            from binance.client import Client
            
            # Lấy API key từ biến môi trường hoặc file .env
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.environ.get('BINANCE_API_KEY')
            api_secret = os.environ.get('BINANCE_API_SECRET')
            
            # Tạo client
            client = Client(api_key, api_secret)
            
            # Chuyển đổi định dạng ngày
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
            
            # Lấy dữ liệu
            klines = client.get_historical_klines(
                symbol, interval, start_ts, end_ts
            )
            
            # Chuyển đổi sang DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
                
            logger.info(f"Đã tải dữ liệu từ Binance thành công: {len(df)} dòng")
            return df
            
        except (ImportError, Exception) as e:
            # Thử sử dụng requests trực tiếp
            import requests
            
            # URL API
            base_url = 'https://api.binance.com/api/v3/klines'
            
            # Chuyển đổi định dạng ngày
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
            
            # Tham số
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_ts,
                'endTime': end_ts,
                'limit': 1000
            }
            
            # Lấy dữ liệu
            all_klines = []
            while start_ts < end_ts:
                params['startTime'] = start_ts
                response = requests.get(base_url, params=params)
                klines = response.json()
                
                if not klines:
                    break
                    
                all_klines.extend(klines)
                start_ts = klines[-1][0] + 1
                
            # Chuyển đổi sang DataFrame
            df = pd.DataFrame(all_klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
                
            logger.info(f"Đã tải dữ liệu từ Binance thành công (requests): {len(df)} dòng")
            return df
            
    except Exception as e:
        logger.warning(f"Không thể tải dữ liệu từ Binance: {e}")
        return None

def generate_sample_data(symbol: str, interval: str, 
                       start_date: str, end_date: str) -> pd.DataFrame:
    """
    Tạo dữ liệu mẫu mô phỏng
    
    Args:
        symbol (str): Mã cặp giao dịch (ví dụ: BTCUSDT)
        interval (str): Khung thời gian (ví dụ: 1h, 4h, 1d)
        start_date (str): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str): Ngày kết thúc (YYYY-MM-DD)
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu giá mô phỏng
    """
    # Xác định các tham số ban đầu dựa trên symbol
    if 'BTC' in symbol:
        initial_price = 60000
        volatility = 0.02
    elif 'ETH' in symbol:
        initial_price = 3000
        volatility = 0.025
    elif 'BNB' in symbol:
        initial_price = 500
        volatility = 0.022
    elif 'SOL' in symbol:
        initial_price = 100
        volatility = 0.03
    elif 'XRP' in symbol:
        initial_price = 0.8
        volatility = 0.025
    else:
        initial_price = 100
        volatility = 0.02
    
    # Tính toán số lượng bước thời gian
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    days = (end_dt - start_dt).days
    
    if interval == '1h':
        num_steps = days * 24
        freq = 'H'
    elif interval == '4h':
        num_steps = days * 6
        freq = '4H'
    elif interval == '1d':
        num_steps = days
        freq = 'D'
    else:
        num_steps = days * 24
        freq = 'H'
    
    # Tạo timestamp
    timestamps = pd.date_range(start=start_dt, periods=num_steps, freq=freq)
    
    # Tạo giá
    np.random.seed(42)  # Đặt seed cho tính tái tạo
    
    # Thêm một vài xu hướng thị trường
    trend_change_points = np.random.choice(range(1, num_steps), size=5, replace=False)
    trends = np.zeros(num_steps)
    
    current_trend = np.random.choice([-1, 1]) * 0.0005  # Xu hướng ban đầu
    for i in range(num_steps):
        if i in trend_change_points:
            current_trend = np.random.choice([-1, 1]) * 0.0005  # Thay đổi xu hướng
        trends[i] = current_trend
    
    # Tạo nhiễu ngẫu nhiên
    price_changes = np.random.normal(0, volatility, num_steps) + trends
    
    # Tạo giá từ nhiễu
    prices = np.zeros(num_steps)
    prices[0] = initial_price
    for i in range(1, num_steps):
        prices[i] = prices[i-1] * (1 + price_changes[i])
    
    # Tạo dữ liệu OHLCV
    opens = prices.copy()
    highs = prices * (1 + np.random.uniform(0, 0.02, num_steps))
    lows = prices * (1 - np.random.uniform(0, 0.02, num_steps))
    closes = prices * (1 + np.random.normal(0, 0.003, num_steps))
    volumes = np.random.lognormal(12, 1, num_steps) * (1 + 0.1 * np.abs(price_changes))
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes,
        'close_time': timestamps + pd.Timedelta(hours=1),
        'quote_asset_volume': volumes * closes,
        'number_of_trades': np.random.randint(100, 10000, num_steps),
        'taker_buy_base_asset_volume': volumes * 0.4 * np.random.uniform(0.3, 0.7, num_steps),
        'taker_buy_quote_asset_volume': volumes * closes * 0.4 * np.random.uniform(0.3, 0.7, num_steps),
        'ignore': np.zeros(num_steps)
    })
    
    logger.info(f"Đã tạo dữ liệu mẫu: {len(df)} dòng từ {start_date} đến {end_date}")
    return df

def split_data_into_periods(df: pd.DataFrame, output_dir: str, 
                           symbol: str, interval: str) -> Dict[str, str]:
    """
    Chia dữ liệu thành các giai đoạn khác nhau
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá
        output_dir (str): Thư mục đầu ra
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        
    Returns:
        Dict[str, str]: Ánh xạ tên giai đoạn -> đường dẫn file
    """
    # Đảm bảo thư mục đầu ra tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Xác định thời điểm cuối
    end_date = df['timestamp'].max()
    
    # Chia thành các giai đoạn
    periods = {
        '1_month': end_date - pd.Timedelta(days=30),
        '3_months': end_date - pd.Timedelta(days=90),
        '6_months': end_date - pd.Timedelta(days=180),
    }
    
    # Tạo thư mục cho từng giai đoạn và lưu dữ liệu
    period_files = {}
    for period_name, start_date in periods.items():
        # Tạo thư mục
        period_dir = os.path.join(output_dir, period_name)
        os.makedirs(period_dir, exist_ok=True)
        
        # Lọc dữ liệu
        period_df = df[df['timestamp'] >= start_date].copy()
        
        # Lưu file
        file_name = f"{symbol}_{interval}.csv"
        file_path = os.path.join(period_dir, file_name)
        period_df.to_csv(file_path, index=False)
        
        # Thêm vào danh sách
        period_files[period_name] = file_path
        
        logger.info(f"Đã lưu dữ liệu {period_name} ({len(period_df)} dòng) tại {file_path}")
    
    return period_files

def process_symbol(symbol: str, timeframes: List[str], 
                 start_date: str, end_date: str, output_dir: str) -> Dict:
    """
    Xử lý một cặp giao dịch
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframes (List[str]): Danh sách khung thời gian
        start_date (str): Ngày bắt đầu
        end_date (str): Ngày kết thúc
        output_dir (str): Thư mục đầu ra
        
    Returns:
        Dict: Thông tin về dữ liệu đã tạo
    """
    # Kết quả
    result = {
        'symbol': symbol,
        'timeframes': {},
        'start_date': start_date,
        'end_date': end_date
    }
    
    # Xử lý từng khung thời gian
    for timeframe in timeframes:
        logger.info(f"Đang xử lý {symbol} {timeframe}...")
        
        # Thử tải dữ liệu từ Binance
        df = try_load_binance_data(symbol, timeframe, start_date, end_date)
        
        # Nếu không thành công, tạo dữ liệu mẫu
        if df is None or len(df) < 100:
            logger.info(f"Tạo dữ liệu mẫu cho {symbol} {timeframe}...")
            df = generate_sample_data(symbol, timeframe, start_date, end_date)
        
        # Chia thành các giai đoạn
        period_files = split_data_into_periods(df, output_dir, symbol, timeframe)
        
        # Thêm vào kết quả
        result['timeframes'][timeframe] = {
            'rows': len(df),
            'period_files': period_files
        }
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Tạo bộ dữ liệu mẫu cho ML backtest')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT', help='Danh sách cặp giao dịch (phân cách bằng dấu phẩy)')
    parser.add_argument('--timeframes', type=str, default='1h,4h,1d', help='Danh sách khung thời gian (phân cách bằng dấu phẩy)')
    parser.add_argument('--periods', type=str, default='1_month,3_months,6_months', help='Danh sách khoảng thời gian cần tạo (phân cách bằng dấu phẩy)')
    parser.add_argument('--days', type=int, default=180, help='Số ngày dữ liệu')
    parser.add_argument('--output-dir', type=str, default='real_data', help='Thư mục lưu dữ liệu')
    
    args = parser.parse_args()
    
    # Tạo thư mục đầu ra
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Phân tích tham số
    symbols = args.symbols.split(',')
    timeframes = args.timeframes.split(',')
    
    # Tính toán ngày bắt đầu và kết thúc
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    
    # Xử lý từng cặp giao dịch
    results = {}
    for symbol in symbols:
        results[symbol] = process_symbol(symbol, timeframes, start_date, end_date, args.output_dir)
    
    # Lưu thông tin kết quả
    result_file = os.path.join(args.output_dir, 'fetch_results.json')
    with open(result_file, 'w') as f:
        json.dump({
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbols': symbols,
            'timeframes': timeframes,
            'start_date': start_date,
            'end_date': end_date,
            'results': results
        }, f, indent=2)
    
    logger.info(f"Đã hoàn thành tạo dữ liệu, thông tin được lưu tại {result_file}")
    print(f"Đã tạo dữ liệu thành công cho {len(symbols)} cặp giao dịch, {len(timeframes)} khung thời gian.")

if __name__ == "__main__":
    main()
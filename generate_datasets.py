#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo và chuẩn bị bộ dữ liệu cho việc huấn luyện và kiểm thử mô hình ML
"""

import os
import json
import argparse
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def generate_price_series(days: int = 180, initial_price: float = 50000.0, 
                         volatility: float = 0.02, timeframe: str = '1h',
                         with_trends: bool = True) -> pd.DataFrame:
    """
    Tạo dữ liệu giá mẫu với xu hướng ngẫu nhiên
    
    Args:
        days (int): Số ngày dữ liệu
        initial_price (float): Giá ban đầu
        volatility (float): Độ biến động (0.01 = 1%)
        timeframe (str): Khung thời gian ('1h', '4h', '1d')
        with_trends (bool): Có tạo xu hướng không
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLCV
    """
    # Xác định số điểm dữ liệu dựa trên timeframe
    points_per_day = {
        '1h': 24,
        '4h': 6,
        '1d': 1
    }
    num_points = days * points_per_day.get(timeframe, 24)
    
    # Tạo chuỗi thời gian
    end_date = datetime.now()
    if timeframe == '1h':
        start_date = end_date - timedelta(hours=num_points)
        date_range = pd.date_range(start=start_date, end=end_date, periods=num_points)
    elif timeframe == '4h':
        start_date = end_date - timedelta(hours=num_points * 4)
        date_range = pd.date_range(start=start_date, end=end_date, periods=num_points)
    elif timeframe == '1d':
        start_date = end_date - timedelta(days=num_points)
        date_range = pd.date_range(start=start_date, end=end_date, periods=num_points)
    
    # Tạo các xu hướng
    if with_trends:
        # Tạo xu hướng cơ bản
        trend_changes = np.random.randint(5, 20, size=days // 30 + 1)  # Thay đổi xu hướng mỗi 5-20 ngày
        trends = []
        current_trend = np.random.choice([-1, 1])  # Bắt đầu với xu hướng ngẫu nhiên
        
        for duration in trend_changes:
            trends.extend([current_trend] * duration * points_per_day.get(timeframe, 24))
            current_trend *= -1  # Đảo ngược xu hướng
        
        trends = trends[:num_points]  # Cắt về đúng kích thước
        trend_factor = np.array(trends) * volatility * 0.5  # Điều chỉnh xu hướng thành % thay đổi
    else:
        trend_factor = np.zeros(num_points)
    
    # Tạo nhiễu ngẫu nhiên
    returns = np.random.normal(0, volatility, num_points) + trend_factor
    
    # Tạo chuỗi giá
    price_series = initial_price * (1 + returns).cumprod()
    
    # Tạo dữ liệu OHLCV
    df = pd.DataFrame({
        'timestamp': date_range,
        'open': price_series,
        'close': price_series,
        'high': price_series,
        'low': price_series,
        'volume': np.zeros(num_points)
    })
    
    # Thêm biến động ngẫu nhiên cho giá open/high/low
    for i in range(len(df)):
        intrabar_volatility = volatility * price_series[i] * 0.5
        df.at[i, 'open'] = price_series[i] * (1 + np.random.normal(0, 0.2) * intrabar_volatility / price_series[i])
        df.at[i, 'high'] = max(df.at[i, 'open'], df.at[i, 'close']) + abs(np.random.normal(0, 1)) * intrabar_volatility
        df.at[i, 'low'] = min(df.at[i, 'open'], df.at[i, 'close']) - abs(np.random.normal(0, 1)) * intrabar_volatility
        df.at[i, 'volume'] = abs(np.random.normal(1, 0.5)) * 1000 * (1 + abs(returns[i]) * 10)  # Khối lượng tỷ lệ với độ biến động
    
    # Đảm bảo high luôn cao nhất và low luôn thấp nhất
    df['high'] = df[['high', 'open', 'close']].max(axis=1)
    df['low'] = df[['low', 'open', 'close']].min(axis=1)
    
    # Thêm các cột bổ sung cần thiết cho dữ liệu Binance
    df['close_time'] = df['timestamp'] + pd.Timedelta(hours=1)
    df['quote_asset_volume'] = df['volume'] * df['close']
    df['number_of_trades'] = (df['volume'] / 10).astype(int) + 100
    df['taker_buy_base_asset_volume'] = df['volume'] * np.random.uniform(0.4, 0.6, len(df))
    df['taker_buy_quote_asset_volume'] = df['taker_buy_base_asset_volume'] * df['close']
    df['ignore'] = 0
    
    logger.info(f"Đã tạo {len(df)} điểm dữ liệu từ {df['timestamp'].min()} đến {df['timestamp'].max()}")
    
    return df

def prepare_datasets(symbols: List[str], timeframes: List[str], 
                    periods: List[str], output_dir: str = 'real_data'):
    """
    Chuẩn bị bộ dữ liệu cho nhiều đồng tiền, khung thời gian và khoảng thời gian
    
    Args:
        symbols (List[str]): Danh sách các đồng tiền
        timeframes (List[str]): Danh sách các khung thời gian
        periods (List[str]): Danh sách các khoảng thời gian ('1_month', '3_months', '6_months')
        output_dir (str): Thư mục đầu ra
    """
    # Ánh xạ khoảng thời gian thành số ngày
    period_days = {
        '1_month': 30,
        '3_months': 90,
        '6_months': 180
    }
    
    # Tạo thư mục đầu ra
    os.makedirs(output_dir, exist_ok=True)
    for period in periods:
        os.makedirs(os.path.join(output_dir, period), exist_ok=True)
    
    # Tạo các bộ dữ liệu
    fetch_results = []
    
    for symbol in symbols:
        # Thiết lập giá ban đầu và độ biến động dựa trên đồng tiền
        if symbol == 'BTCUSDT':
            initial_price = 50000.0
            volatility = 0.02
        elif symbol == 'ETHUSDT':
            initial_price = 3000.0
            volatility = 0.025
        elif symbol == 'BNBUSDT':
            initial_price = 500.0
            volatility = 0.03
        elif symbol == 'SOLUSDT':
            initial_price = 100.0
            volatility = 0.035
        elif symbol == 'XRPUSDT':
            initial_price = 0.5
            volatility = 0.03
        elif symbol == 'DOGEUSDT':
            initial_price = 0.1
            volatility = 0.04
        elif symbol == 'ADAUSDT':
            initial_price = 0.5
            volatility = 0.03
        elif symbol == 'DOTUSDT':
            initial_price = 15.0
            volatility = 0.035
        elif symbol == 'MATICUSDT':
            initial_price = 1.0
            volatility = 0.04
        else:
            initial_price = 100.0
            volatility = 0.03
        
        # Tạo dữ liệu cho mỗi khung thời gian
        for timeframe in timeframes:
            # Tạo dữ liệu dài nhất (6 tháng)
            max_days = period_days.get('6_months', 180)
            df_full = generate_price_series(
                days=max_days,
                initial_price=initial_price,
                volatility=volatility,
                timeframe=timeframe,
                with_trends=True
            )
            
            # Lưu dữ liệu cho từng khoảng thời gian
            for period in periods:
                days = period_days.get(period, 30)
                
                # Lấy phần dữ liệu tương ứng với khoảng thời gian
                df = df_full.tail(days * 24 if timeframe == '1h' else days * 6 if timeframe == '4h' else days)
                
                # Lưu file
                output_file = os.path.join(output_dir, period, f"{symbol}_{timeframe}.csv")
                df.to_csv(output_file, index=False)
                
                logger.info(f"Đã lưu dữ liệu {symbol} {timeframe} ({period}) tại: {output_file}")
                fetch_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'period': period,
                    'file_path': output_file,
                    'num_records': len(df),
                    'start_date': df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
                    'end_date': df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S'),
                })
    
    # Lưu kết quả tạo dữ liệu
    with open(os.path.join(output_dir, 'fetch_results.json'), 'w') as f:
        json.dump(fetch_results, f, indent=2)
    
    logger.info(f"Đã tạo tổng cộng {len(fetch_results)} bộ dữ liệu")

def main():
    parser = argparse.ArgumentParser(description='Tạo bộ dữ liệu cho huấn luyện ML')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT',
                        help='Danh sách các đồng tiền, phân tách bằng dấu phẩy')
    parser.add_argument('--timeframes', type=str, default='1h,4h,1d',
                        help='Danh sách các khung thời gian, phân tách bằng dấu phẩy')
    parser.add_argument('--periods', type=str, default='1_month,3_months,6_months',
                        help='Danh sách các khoảng thời gian, phân tách bằng dấu phẩy')
    parser.add_argument('--output_dir', type=str, default='real_data',
                        help='Thư mục đầu ra cho dữ liệu')
    
    args = parser.parse_args()
    
    # Chuyển đổi các danh sách từ chuỗi
    symbols = args.symbols.split(',')
    timeframes = args.timeframes.split(',')
    periods = args.periods.split(',')
    
    logger.info(f"Bắt đầu tạo dữ liệu cho {len(symbols)} đồng tiền, {len(timeframes)} khung thời gian, {len(periods)} khoảng thời gian")
    
    # Tạo bộ dữ liệu
    prepare_datasets(symbols, timeframes, periods, args.output_dir)
    
    logger.info("Hoàn thành tạo dữ liệu")

if __name__ == "__main__":
    main()
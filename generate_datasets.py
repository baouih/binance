#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo dữ liệu mẫu cho 9 đồng coin với 3 khung thời gian (1, 3, và 6 tháng)
"""

import os
import json
import time
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('generate_datasets')

def generate_price_data(symbol, days, interval, initial_price, volatility):
    """
    Tạo dữ liệu giá mẫu với biến động ngẫu nhiên và xu hướng
    
    Args:
        symbol (str): Mã cặp giao dịch
        days (int): Số ngày dữ liệu cần tạo
        interval (str): Khung thời gian (1h, 4h, 1d)
        initial_price (float): Giá bắt đầu
        volatility (float): Độ biến động giá
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu OHLCV
    """
    # Xác định số lượng khoảng thời gian
    if interval == '1h':
        periods = days * 24
        freq = 'H'
    elif interval == '4h':
        periods = days * 6
        freq = '4H'
    elif interval == '1d':
        periods = days
        freq = 'D'
    else:
        periods = days * 24
        freq = 'H'
    
    # Tạo dữ liệu thời gian
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    # Chỉ dùng start_time và periods (không dùng end_time và freq cùng lúc)
    timestamps = pd.date_range(start=start_time, periods=periods, freq=freq)
    
    # Tạo mảng giá
    np.random.seed(42)  # Để kết quả có thể tái tạo
    
    # Tạo chuỗi giá theo xu hướng thực tế
    price = initial_price
    prices = []
    
    # Thêm một số xu hướng và chu kỳ để mô phỏng thị trường thực tế
    # Giai đoạn: xu hướng tăng -> sideway -> điều chỉnh -> xu hướng tăng mạnh -> điều chỉnh mạnh
    trend_phases = [
        (0.0005, int(periods * 0.15)),  # Xu hướng tăng nhẹ
        (0.0, int(periods * 0.2)),  # Sideway
        (-0.0003, int(periods * 0.15)),  # Điều chỉnh nhẹ
        (0.0015, int(periods * 0.3)),  # Xu hướng tăng mạnh
        (-0.0010, int(periods * 0.2))  # Điều chỉnh mạnh
    ]
    
    # Vị trí trong chu kỳ
    phase_start = 0
    
    for phase, length in trend_phases:
        phase_end = phase_start + length
        if phase_end > periods:
            phase_end = periods
            
        for i in range(phase_start, phase_end):
            # Thành phần ngẫu nhiên
            random_change = np.random.normal(0, volatility)
            
            # Thành phần xu hướng
            trend_change = phase
            
            # Thành phần chu kỳ (sin wave)
            cycle_change = 0.0002 * np.sin(i / 20)
            
            # Tổng thay đổi
            total_change = random_change + trend_change + cycle_change
            
            # Cập nhật giá
            price = price * (1 + total_change)
            
            # Bảo đảm giá không âm
            price = max(price, 0.00001)
            
            prices.append(price)
            
        phase_start = phase_end
        
    # Điền thêm nếu thiếu
    while len(prices) < periods:
        prices.append(prices[-1])
    
    # Tạo giá high, low và volume
    high_prices = [p * (1 + abs(np.random.normal(0, volatility * 0.5))) for p in prices]
    low_prices = [p * (1 - abs(np.random.normal(0, volatility * 0.5))) for p in prices]
    
    # Có thể thêm biến động volume theo giá
    volumes = []
    for i in range(len(prices)):
        if i > 0:
            price_change = abs(prices[i] / prices[i-1] - 1)
            # Volume tăng khi giá biến động mạnh
            vol_boost = 1 + 5 * price_change
        else:
            vol_boost = 1
            
        base_volume = np.random.lognormal(0, 0.5) * initial_price / 10000
        volumes.append(base_volume * vol_boost)
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': high_prices,
        'low': low_prices,
        'close': prices,
        'volume': volumes
    })
    
    # Thêm các cột khác để tương thích với dữ liệu Binance
    df['close_time'] = df['timestamp'] + pd.Timedelta(seconds=3600-1)
    df['quote_asset_volume'] = df['volume'] * df['close']
    df['number_of_trades'] = (df['volume'] * 100).astype(int)
    df['taker_buy_base_asset_volume'] = df['volume'] * 0.5
    df['taker_buy_quote_asset_volume'] = df['taker_buy_base_asset_volume'] * df['close']
    df['ignore'] = 0
    
    return df

def main():
    """Hàm chính để tạo dữ liệu"""
    # Danh sách 9 đồng coin cần tạo dữ liệu
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT',
        'SOLUSDT', 'DOGEUSDT', 'XRPUSDT',
        'ADAUSDT', 'DOTUSDT', 'LINKUSDT'
    ]
    
    # Danh sách khung thời gian
    intervals = ['1h', '4h', '1d']
    
    # Giá tham khảo cho mỗi đồng coin
    initial_prices = {
        'BTCUSDT': 60000,
        'ETHUSDT': 3500,
        'BNBUSDT': 600,
        'SOLUSDT': 130,
        'DOGEUSDT': 0.15,
        'XRPUSDT': 0.60,
        'ADAUSDT': 0.50,
        'DOTUSDT': 8.0,
        'LINKUSDT': 18.0
    }
    
    # Độ biến động cho mỗi đồng coin
    volatilities = {
        'BTCUSDT': 0.02,
        'ETHUSDT': 0.025,
        'BNBUSDT': 0.03,
        'SOLUSDT': 0.04,
        'DOGEUSDT': 0.05,
        'XRPUSDT': 0.035,
        'ADAUSDT': 0.03,
        'DOTUSDT': 0.035,
        'LINKUSDT': 0.03
    }
    
    # Khung thời gian
    time_ranges = {
        '1_month': 30,
        '3_months': 90,
        '6_months': 180
    }
    
    # Thư mục gốc
    root_dir = 'real_data'
    os.makedirs(root_dir, exist_ok=True)
    
    # Kết quả tổng hợp
    results = {
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "symbols": {},
        "total_files": 0,
        "total_candles": 0
    }
    
    # Tạo dữ liệu cho từng đồng coin, khung thời gian và khoảng thời gian
    for symbol in symbols:
        results["symbols"][symbol] = {}
        
        for interval in intervals:
            results["symbols"][symbol][interval] = {}
            
            for time_label, days in time_ranges.items():
                # Tạo thư mục nếu chưa tồn tại
                range_dir = f"{root_dir}/{time_label}"
                os.makedirs(range_dir, exist_ok=True)
                
                print(f"Đang tạo dữ liệu {symbol} {interval} cho {time_label}...")
                
                # Tạo dữ liệu
                df = generate_price_data(
                    symbol=symbol,
                    days=days,
                    interval=interval,
                    initial_price=initial_prices[symbol],
                    volatility=volatilities[symbol]
                )
                
                # Lưu dữ liệu
                file_path = f"{range_dir}/{symbol}_{interval}.csv"
                df.to_csv(file_path, index=False)
                
                results["symbols"][symbol][interval][time_label] = {
                    "file_path": file_path,
                    "candles": len(df),
                    "start_date": df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
                    "end_date": df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                results["total_files"] += 1
                results["total_candles"] += len(df)
                
                print(f"Đã lưu {len(df)} dòng dữ liệu vào {file_path}")
    
    # Lưu kết quả
    with open(f"{root_dir}/fetch_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nHoàn tất! Đã tạo {results['total_files']} file với tổng cộng {results['total_candles']} nến.")
    print(f"Báo cáo chi tiết được lưu tại {root_dir}/fetch_results.json")

if __name__ == "__main__":
    main()
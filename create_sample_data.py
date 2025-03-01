#!/usr/bin/env python3
"""
Script tạo dữ liệu mẫu cho backtesting

Script này tạo dữ liệu giá mẫu chân thực để sử dụng cho backtesting khi không có
dữ liệu thực từ Binance.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Tạo thư mục dữ liệu nếu chưa tồn tại
os.makedirs("test_data/BTCUSDT", exist_ok=True)
os.makedirs("test_data/ETHUSDT", exist_ok=True)
os.makedirs("test_data/BNBUSDT", exist_ok=True)
os.makedirs("test_data/SOLUSDT", exist_ok=True)

def generate_price_series(days=90, initial_price=60000, volatility=0.02, interval='1h'):
    """
    Tạo chuỗi giá mẫu với biến động ngẫu nhiên và xu hướng
    
    Args:
        days (int): Số ngày dữ liệu cần tạo
        initial_price (float): Giá bắt đầu
        volatility (float): Độ biến động giá
        interval (str): Khung thời gian
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu OHLCV
    """
    # Xác định số lượng candles dựa trên khung thời gian
    if interval == '1h':
        candles_per_day = 24
    elif interval == '4h':
        candles_per_day = 6
    elif interval == '1d':
        candles_per_day = 1
    elif interval == '15m':
        candles_per_day = 24 * 4
    else:  # Mặc định 1h
        candles_per_day = 24
    
    num_candles = days * candles_per_day
    
    # Tạo dữ liệu thời gian
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    if interval == '1h':
        date_range = pd.date_range(start=start_date, end=end_date, freq='H', inclusive='left')
    elif interval == '4h':
        date_range = pd.date_range(start=start_date, end=end_date, freq='4H', inclusive='left')
    elif interval == '1d':
        date_range = pd.date_range(start=start_date, end=end_date, freq='D', inclusive='left')
    elif interval == '15m':
        date_range = pd.date_range(start=start_date, end=end_date, freq='15min', inclusive='left')
    else:
        date_range = pd.date_range(start=start_date, end=end_date, freq='H', inclusive='left')
    
    # Đảm bảo có đúng số lượng candles
    date_range = date_range[:num_candles]
    
    # Tạo xu hướng cơ bản
    # Chia thành 3 giai đoạn: tăng, giảm, dao động ngang
    trend_period = num_candles // 3
    
    # Tạo nhiễu Gaussian
    noise = np.random.normal(0, volatility, num_candles)
    
    # Tạo xu hướng
    trend = np.zeros(num_candles)
    
    # Giai đoạn 1: xu hướng tăng
    trend[:trend_period] = np.linspace(0, 0.05, trend_period)
    
    # Giai đoạn 2: xu hướng giảm
    trend[trend_period:2*trend_period] = np.linspace(0.05, -0.05, trend_period)
    
    # Giai đoạn 3: dao động ngang
    trend[2*trend_period:] = np.linspace(-0.05, 0.02, num_candles - 2*trend_period)
    
    # Tính giá đóng cửa
    close_prices = [initial_price]
    for i in range(1, num_candles):
        # Thêm một chút ngẫu nhiên vào xu hướng để tạo biến động
        drift = trend[i] + noise[i]
        prev_price = close_prices[-1]
        new_price = prev_price * (1 + drift)
        close_prices.append(new_price)
    
    close_prices = np.array(close_prices)
    
    # Tạo giá mở cửa dựa trên giá đóng cửa trước đó với một chút ngẫu nhiên
    open_prices = np.zeros(num_candles)
    open_prices[0] = initial_price * (1 + np.random.normal(0, volatility/2))
    open_prices[1:] = close_prices[:-1] * (1 + np.random.normal(0, volatility/3, num_candles-1))
    
    # Tạo giá cao và thấp
    high_prices = np.maximum(open_prices, close_prices) * (1 + np.abs(np.random.normal(0, volatility/2, num_candles)))
    low_prices = np.minimum(open_prices, close_prices) * (1 - np.abs(np.random.normal(0, volatility/2, num_candles)))
    
    # Tạo khối lượng giao dịch
    volume = np.random.normal(1000, 500, num_candles)
    # Tăng khối lượng vào những ngày có giá biến động mạnh
    close_with_initial = np.append(initial_price, close_prices)
    price_diff = np.diff(close_with_initial)
    # Đảm bảo kích thước phù hợp
    volume_multiplier = np.ones(num_candles)
    volume_multiplier[0:len(price_diff)] = 1 + 5 * np.abs(price_diff / close_with_initial[:-1])
    volume = volume * volume_multiplier
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'timestamp': date_range,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    })
    
    # Thêm các cột bổ sung để mô phỏng dữ liệu từ Binance
    df['close_time'] = df['timestamp'] + pd.Timedelta(minutes=59) if interval == '1h' else df['timestamp'] + pd.Timedelta(hours=3) if interval == '4h' else df['timestamp'] + pd.Timedelta(days=1)
    df['quote_asset_volume'] = df['volume'] * df['close']
    df['number_of_trades'] = (df['volume'] / 10).astype(int)
    df['taker_buy_base_asset_volume'] = df['volume'] * np.random.uniform(0.4, 0.6, num_candles)
    df['taker_buy_quote_asset_volume'] = df['taker_buy_base_asset_volume'] * df['close']
    df['ignore'] = 0
    
    # Đặt timestamp làm index
    df.set_index('timestamp', inplace=True)
    
    return df

def main():
    """Hàm chính để tạo dữ liệu"""
    # Các cặp tiền và khung thời gian cần tạo dữ liệu
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
    intervals = ['1h', '4h', '1d', '15m']
    
    # Giá bắt đầu cho mỗi loại tiền
    initial_prices = {
        'BTCUSDT': 60000,
        'ETHUSDT': 3000,
        'BNBUSDT': 450,
        'SOLUSDT': 100
    }
    
    # Tạo và lưu dữ liệu
    for symbol in symbols:
        for interval in intervals:
            print(f"Đang tạo dữ liệu cho {symbol} - {interval}")
            
            # Tạo dữ liệu với độ biến động khác nhau cho mỗi cặp tiền
            volatility = 0.02 if symbol == 'BTCUSDT' else 0.025 if symbol == 'ETHUSDT' else 0.03
            
            df = generate_price_series(
                days=90,
                initial_price=initial_prices[symbol],
                volatility=volatility,
                interval=interval
            )
            
            # Lưu dữ liệu
            file_path = f"test_data/{symbol}/{symbol}_{interval}.csv"
            df.to_csv(file_path)
            
            print(f"Đã lưu {len(df)} candles vào {file_path}")
    
    # Tạo file kết quả
    results = {
        "symbols": {},
        "total_candles": 0
    }
    
    for symbol in symbols:
        results["symbols"][symbol] = {}
        for interval in intervals:
            file_path = f"test_data/{symbol}/{symbol}_{interval}.csv"
            df = pd.read_csv(file_path)
            
            results["symbols"][symbol][interval] = {
                "status": "success",
                "count": len(df),
                "file_path": file_path
            }
            
            results["total_candles"] += len(df)
    
    # Lưu kết quả
    import json
    with open("test_data/fetch_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Đã tạo tổng cộng {results['total_candles']} candles cho {len(symbols)} cặp tiền và {len(intervals)} khung thời gian")

if __name__ == "__main__":
    main()
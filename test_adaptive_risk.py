#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from adaptive_risk_manager import AdaptiveRiskManager

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_adaptive_risk')

def load_historical_data(symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    """
    Tải dữ liệu lịch sử từ file CSV hoặc từ API
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        limit (int): Số lượng nến tối đa
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu giá
    """
    # Kiểm tra nếu có file dữ liệu cục bộ
    data_path = f"data/{symbol}_{timeframe}.csv"
    if os.path.exists(data_path):
        try:
            df = pd.read_csv(data_path)
            logger.info(f"Đã tải dữ liệu từ file: {data_path}")
            
            # Đảm bảo có các cột cần thiết
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    logger.error(f"Thiếu cột {col} trong dữ liệu")
                    return None
            
            # Sắp xếp theo thời gian và giới hạn số lượng nến
            df = df.sort_values('timestamp').tail(limit)
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi đọc file dữ liệu: {str(e)}")
    
    # Nếu không có file cục bộ, tạo dữ liệu mẫu để thử nghiệm
    logger.warning(f"Không tìm thấy file dữ liệu cho {symbol}_{timeframe}, tạo dữ liệu mẫu")
    
    # Tạo DataFrame mẫu
    np.random.seed(42)  # Để có kết quả nhất quán
    
    # Tạo giá mẫu với xu hướng ngẫu nhiên
    start_price = 100.0
    daily_volatility = 0.02
    
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(limit, 0, -1)]
    close_prices = [start_price]
    
    for i in range(1, limit):
        # Thêm một xu hướng nhỏ và nhiễu ngẫu nhiên
        close_prices.append(close_prices[-1] * (1 + np.random.normal(0.0001, daily_volatility)))
    
    # Tạo các giá trị OHLCV
    high_prices = [price * (1 + np.random.uniform(0, 0.01)) for price in close_prices]
    low_prices = [price * (1 - np.random.uniform(0, 0.01)) for price in close_prices]
    open_prices = [low + np.random.uniform(0, high - low) for high, low in zip(high_prices, low_prices)]
    volumes = [np.random.uniform(1000, 10000) for _ in range(limit)]
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })
    
    # Tạo thư mục data nếu chưa tồn tại
    os.makedirs("data", exist_ok=True)
    
    # Lưu dữ liệu mẫu
    df.to_csv(data_path, index=False)
    logger.info(f"Đã tạo dữ liệu mẫu và lưu vào {data_path}")
    
    return df

def test_atr_calculation():
    """
    Kiểm tra tính toán ATR
    """
    symbol = "BTCUSDT"
    timeframe = "1h"
    
    # Tải dữ liệu
    df = load_historical_data(symbol, timeframe)
    if df is None:
        logger.error("Không thể tải dữ liệu để kiểm tra ATR")
        return
    
    # Khởi tạo risk manager
    risk_manager = AdaptiveRiskManager()
    
    # Tính toán ATR
    atr_period = 14
    atr = risk_manager.calculate_atr(df, atr_period)
    volatility = risk_manager.calculate_volatility_percentage(df, atr_period)
    volatility_level = risk_manager.get_volatility_level(volatility)
    
    logger.info(f"ATR của {symbol} ({timeframe}): {atr:.4f}")
    logger.info(f"Biến động (Volatility): {volatility:.2f}%")
    logger.info(f"Mức độ biến động: {volatility_level}")

def test_risk_parameters():
    """
    Kiểm tra tham số rủi ro dựa trên ATR và biến động
    """
    symbol = "BTCUSDT"
    timeframe = "1h"
    
    # Tải dữ liệu
    df = load_historical_data(symbol, timeframe)
    if df is None:
        logger.error("Không thể tải dữ liệu để kiểm tra tham số rủi ro")
        return
    
    # Khởi tạo risk manager
    risk_manager = AdaptiveRiskManager()
    
    # Liệt kê các mức rủi ro để kiểm tra
    risk_levels = ['very_low', 'low', 'medium', 'high', 'very_high']
    
    results = []
    
    for level in risk_levels:
        # Thiết lập mức rủi ro
        risk_manager.set_risk_level(level)
        
        # Tính toán tham số giao dịch cho lệnh BUY
        trade_params_buy = risk_manager.get_trade_parameters(df, symbol, 'BUY')
        
        # Tính toán tham số giao dịch cho lệnh SELL
        trade_params_sell = risk_manager.get_trade_parameters(df, symbol, 'SELL')
        
        # Lưu kết quả
        results.append({
            'risk_level': level,
            'buy_params': trade_params_buy,
            'sell_params': trade_params_sell
        })
    
    # Hiển thị kết quả
    for result in results:
        level = result['risk_level']
        buy = result['buy_params']
        sell = result['sell_params']
        
        print(f"\n=== Mức rủi ro: {level.upper()} ===")
        print(f"ATR: {buy['atr']:.4f} | Volatility: {buy['volatility_percentage']:.2f}% | Level: {buy['volatility_level']}")
        print(f"Vị thế tối đa: {buy['max_positions']}")
        print(f"Leverage: {buy['leverage']}x")
        
        print("\nLệnh BUY:")
        print(f"Kích thước vị thế: {buy['position_size_percentage']:.2f}%")
        print(f"Stop Loss: {buy['stop_loss']:.2f} ({buy['stop_loss_percentage']:.2f}%)")
        print(f"Take Profit: {buy['take_profit']:.2f} ({buy['take_profit_percentage']:.2f}%)")
        
        print("\nLệnh SELL:")
        print(f"Kích thước vị thế: {sell['position_size_percentage']:.2f}%")
        print(f"Stop Loss: {sell['stop_loss']:.2f} ({sell['stop_loss_percentage']:.2f}%)")
        print(f"Take Profit: {sell['take_profit']:.2f} ({sell['take_profit_percentage']:.2f}%)")
        
        # Hiển thị thông tin về trailing stop và partial take profit
        if buy.get('use_trailing_stop'):
            print("\nTrailing Stop:")
            print(f"Kích hoạt khi lợi nhuận đạt: {buy['trailing_activation_threshold']:.1f} x ATR")
            print(f"Khoảng cách trailing: {buy.get('trailing_distance', 0):.4f}")
        
        if buy.get('use_partial_tp'):
            print("\nPartial Take Profit:")
            for i, level in enumerate(buy.get('partial_take_profit_levels', []), 1):
                print(f"Mức {i}: {level['percentage']}% khi đạt {level['target_price']:.2f} "
                      f"({level['atr_multiplier']:.1f} x ATR)")

def plot_volatility_levels():
    """
    Vẽ biểu đồ biến động và mức rủi ro
    """
    symbol = "BTCUSDT"
    timeframe = "1h"
    
    # Tải dữ liệu
    df = load_historical_data(symbol, timeframe)
    if df is None:
        logger.error("Không thể tải dữ liệu để vẽ biểu đồ")
        return
    
    # Khởi tạo risk manager
    risk_manager = AdaptiveRiskManager()
    
    # Tính toán ATR và volatility cho toàn bộ dữ liệu
    df = df.copy()
    
    # Tính True Range
    df['tr0'] = df['high'] - df['low']
    df['tr1'] = abs(df['high'] - df['close'].shift())
    df['tr2'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
    
    # Tính ATR
    atr_period = 14
    df['atr'] = df['tr'].rolling(window=atr_period).mean()
    
    # Tính volatility
    df['volatility'] = (df['atr'] / df['close']) * 100
    
    # Xác định mức volatility
    vol_settings = risk_manager.config.get('volatility_adjustment', {})
    vlow_threshold = vol_settings.get('low_volatility_threshold', 1.5)
    medium_threshold = vol_settings.get('medium_volatility_threshold', 3.0)
    high_threshold = vol_settings.get('high_volatility_threshold', 5.0)
    extreme_threshold = vol_settings.get('extreme_volatility_threshold', 7.0)
    
    # Vẽ biểu đồ
    plt.figure(figsize=(12, 8))
    
    # Vẽ giá đóng cửa
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(df.index, df['close'], label='Giá')
    ax1.set_title(f'Giá đóng cửa {symbol} ({timeframe})')
    ax1.set_ylabel('Giá')
    ax1.legend()
    ax1.grid(True)
    
    # Vẽ biến động
    ax2 = plt.subplot(2, 1, 2, sharex=ax1)
    ax2.plot(df.index, df['volatility'], label='Biến động (%)', color='purple')
    ax2.axhline(y=vlow_threshold, color='green', linestyle='--', label=f'Rất thấp (<{vlow_threshold}%)')
    ax2.axhline(y=medium_threshold, color='blue', linestyle='--', label=f'Thấp ({vlow_threshold}-{medium_threshold}%)')
    ax2.axhline(y=high_threshold, color='orange', linestyle='--', label=f'Trung bình ({medium_threshold}-{high_threshold}%)')
    ax2.axhline(y=extreme_threshold, color='red', linestyle='--', label=f'Cao ({high_threshold}-{extreme_threshold}%)')
    ax2.set_title('Biến động thị trường (ATR/Price %)')
    ax2.set_ylabel('Biến động (%)')
    ax2.set_xlabel('Thời gian')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    
    # Tạo thư mục output nếu chưa tồn tại
    os.makedirs("output", exist_ok=True)
    plt.savefig("output/volatility_levels.png")
    
    plt.close()
    logger.info("Đã lưu biểu đồ biến động vào output/volatility_levels.png")

def plot_atr_based_sl_tp():
    """
    Vẽ biểu đồ stop loss và take profit dựa trên ATR
    """
    symbol = "BTCUSDT"
    timeframe = "1h"
    
    # Tải dữ liệu
    df = load_historical_data(symbol, timeframe)
    if df is None:
        logger.error("Không thể tải dữ liệu để vẽ biểu đồ")
        return
    
    # Khởi tạo risk manager
    risk_manager = AdaptiveRiskManager()
    
    # Chọn mức rủi ro medium để minh họa
    risk_manager.set_risk_level('medium')
    
    # Lấy phần dữ liệu gần đây để dễ quan sát
    recent_df = df.tail(50).copy().reset_index()
    
    # Tính toán ATR và các giá trị liên quan
    atr_period = risk_manager.config.get('atr_settings', {}).get('atr_period', 14)
    atr_values = []
    buy_sl_values = []
    buy_tp_values = []
    sell_sl_values = []
    sell_tp_values = []
    
    # Tính giá trị ATR, SL, TP tại mỗi điểm
    for i in range(atr_period, len(recent_df)):
        data_slice = recent_df.iloc[:i+1]
        
        # Tính ATR
        atr = risk_manager.calculate_atr(data_slice, atr_period)
        if atr is None:
            atr_values.append(np.nan)
            buy_sl_values.append(np.nan)
            buy_tp_values.append(np.nan)
            sell_sl_values.append(np.nan)
            sell_tp_values.append(np.nan)
            continue
        
        # Tính SL và TP
        buy_sl = risk_manager.calculate_atr_based_stop_loss(data_slice, 'BUY')
        buy_tp = risk_manager.calculate_atr_based_take_profit(data_slice, 'BUY')
        sell_sl = risk_manager.calculate_atr_based_stop_loss(data_slice, 'SELL')
        sell_tp = risk_manager.calculate_atr_based_take_profit(data_slice, 'SELL')
        
        atr_values.append(atr)
        buy_sl_values.append(buy_sl)
        buy_tp_values.append(buy_tp)
        sell_sl_values.append(sell_sl)
        sell_tp_values.append(sell_tp)
    
    # Tạo DataFrame mới với các giá trị đã tính
    plot_df = recent_df.iloc[atr_period:].copy()
    plot_df['atr'] = atr_values
    plot_df['buy_sl'] = buy_sl_values
    plot_df['buy_tp'] = buy_tp_values
    plot_df['sell_sl'] = sell_sl_values
    plot_df['sell_tp'] = sell_tp_values
    
    # Vẽ biểu đồ
    plt.figure(figsize=(12, 8))
    
    # Vẽ giá đóng cửa, SL và TP
    plt.plot(plot_df.index, plot_df['close'], label='Giá', color='black', linewidth=2)
    
    # Vẽ SL và TP cho lệnh BUY
    plt.plot(plot_df.index, plot_df['buy_sl'], label='BUY Stop Loss', color='red', linestyle='--')
    plt.plot(plot_df.index, plot_df['buy_tp'], label='BUY Take Profit', color='green', linestyle='--')
    
    # Vẽ SL và TP cho lệnh SELL
    plt.plot(plot_df.index, plot_df['sell_sl'], label='SELL Stop Loss', color='orange', linestyle=':')
    plt.plot(plot_df.index, plot_df['sell_tp'], label='SELL Take Profit', color='blue', linestyle=':')
    
    plt.title(f'ATR-based Stop Loss & Take Profit - {symbol} ({timeframe}) - Mức rủi ro: Medium')
    plt.ylabel('Giá')
    plt.xlabel('Thời gian')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # Tạo thư mục output nếu chưa tồn tại
    os.makedirs("output", exist_ok=True)
    plt.savefig("output/atr_based_sl_tp.png")
    
    plt.close()
    logger.info("Đã lưu biểu đồ SL/TP dựa trên ATR vào output/atr_based_sl_tp.png")

def main():
    """
    Hàm chính để chạy các bài kiểm tra
    """
    logger.info("Bắt đầu kiểm tra Adaptive Risk Manager")
    
    # Kiểm tra tính toán ATR
    test_atr_calculation()
    
    # Kiểm tra các tham số rủi ro
    test_risk_parameters()
    
    # Vẽ biểu đồ biến động
    plot_volatility_levels()
    
    # Vẽ biểu đồ SL/TP dựa trên ATR
    plot_atr_based_sl_tp()
    
    logger.info("Đã hoàn thành kiểm tra Adaptive Risk Manager")

if __name__ == "__main__":
    main()
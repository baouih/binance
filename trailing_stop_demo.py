#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo cho Enhanced Adaptive Trailing Stop

Script này minh họa cách hoạt động của Enhanced Adaptive Trailing Stop
qua các tình huống thị trường khác nhau bằng dữ liệu mô phỏng.
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from enhanced_adaptive_trailing_stop import EnhancedAdaptiveTrailingStop

# Thiết lập các hằng số
CONFIGS_DIR = 'configs'
CONFIG_FILE = os.path.join(CONFIGS_DIR, 'trailing_stop_config.json')
CHARTS_DIR = 'backtest_charts'

# Đảm bảo thư mục tồn tại
os.makedirs(CHARTS_DIR, exist_ok=True)

def generate_price_data(trend_type='trending', volatility='medium', points=100):
    """
    Tạo dữ liệu giá mô phỏng với các kiểu xu hướng và biến động khác nhau
    
    Args:
        trend_type (str): Kiểu xu hướng ('trending', 'ranging', 'reversal')
        volatility (str): Mức độ biến động ('low', 'medium', 'high')
        points (int): Số điểm dữ liệu
        
    Returns:
        np.array: Dữ liệu giá mô phỏng
    """
    # Thiết lập tham số biến động
    if volatility == 'low':
        vol_factor = 0.005
    elif volatility == 'medium':
        vol_factor = 0.01
    else:  # high
        vol_factor = 0.02
    
    # Giá ban đầu
    initial_price = 50000.0
    prices = [initial_price]
    
    # Tạo xu hướng theo loại
    if trend_type == 'trending':
        # Xu hướng tăng
        for i in range(points):
            drift = 0.001 + 0.0005 * i/points  # Tăng dần
            price_change = prices[-1] * (drift + vol_factor * np.random.normal())
            prices.append(max(prices[-1] + price_change, prices[-1] * 0.98))  # Không giảm quá 2%
    
    elif trend_type == 'ranging':
        # Dao động trong range
        mid_price = initial_price
        range_width = initial_price * 0.05  # Range 5%
        
        for i in range(points):
            # Xu hướng về giá trung tâm
            mean_reversion = (mid_price - prices[-1]) * 0.1
            price_change = mean_reversion + prices[-1] * vol_factor * np.random.normal()
            new_price = prices[-1] + price_change
            
            # Đảm bảo giá nằm trong khoảng cho phép
            if new_price > mid_price + range_width:
                new_price = mid_price + range_width
            elif new_price < mid_price - range_width:
                new_price = mid_price - range_width
                
            prices.append(new_price)
    
    elif trend_type == 'reversal':
        # Xu hướng đảo chiều (tăng rồi giảm)
        reversal_point = points // 2
        
        for i in range(points):
            if i < reversal_point:
                # Giai đoạn tăng
                drift = 0.001 + 0.0005 * i/reversal_point
                price_change = prices[-1] * (drift + vol_factor * np.random.normal())
                prices.append(max(prices[-1] + price_change, prices[-1] * 0.98))
            else:
                # Giai đoạn giảm
                drift = -0.001 - 0.0005 * (i - reversal_point)/(points - reversal_point)
                price_change = prices[-1] * (drift + vol_factor * np.random.normal())
                prices.append(min(prices[-1] + price_change, prices[-1] * 1.02))
    
    return np.array(prices)

def visualize_backtest_results(price_data, result, title='Trailing Stop Demo', 
                            filename='trailing_stop_demo.png'):
    """
    Tạo biểu đồ minh họa kết quả backtest
    
    Args:
        price_data (np.array): Dữ liệu giá
        result (dict): Kết quả backtest
        title (str): Tiêu đề biểu đồ
        filename (str): Tên file lưu biểu đồ
    """
    # Tạo DataFrame để dễ vẽ biểu đồ
    df = pd.DataFrame({
        'price': price_data,
        'index': range(len(price_data))
    })
    
    # Tạo hình vẽ
    plt.figure(figsize=(12, 8))
    
    # Vẽ đường giá
    plt.plot(df['index'], df['price'], label='Giá', color='blue', linewidth=1.5)
    
    # Lấy thông tin từ kết quả
    entry_index = 0  # Luôn vào ở điểm đầu tiên trong demo này
    entry_price = result['entry_price']
    exit_index = result.get('exit_index', len(price_data) - 1)
    exit_price = result.get('exit_price', price_data[-1])
    stop_price = result.get('stop_price')
    trailing_activated = result.get('trailing_activated', False)
    partial_exits = result.get('partial_exits', [])
    
    # Đánh dấu điểm vào lệnh
    plt.scatter(entry_index, entry_price, color='green', s=100, marker='^', 
               label=f'Vào lệnh: {entry_price:.2f}')
    
    # Đánh dấu điểm thoát lệnh
    plt.scatter(exit_index, exit_price, color='red', s=100, marker='v', 
               label=f'Thoát lệnh: {exit_price:.2f}')
    
    # Vẽ đường stop loss
    if 'stop_history' in result and result['stop_history']:
        stops = result['stop_history']
        stop_indices = [item[0] for item in stops]
        stop_values = [item[1] for item in stops]
        plt.plot(stop_indices, stop_values, color='red', linestyle='--', 
                label='Trailing Stop', linewidth=1.5)
    else:
        # Nếu không có lịch sử stop, vẽ stop cuối cùng
        if stop_price:
            plt.axhline(y=stop_price, color='red', linestyle='--', 
                      label=f'Stop Price: {stop_price:.2f}')
    
    # Đánh dấu các điểm thoát một phần
    for i, exit_info in enumerate(partial_exits):
        exit_price = exit_info.get('price')
        exit_time = exit_info.get('time')
        exit_pct = exit_info.get('percentage', 0) * 100
        
        # Tìm chỉ số gần nhất với thời gian thoát
        if isinstance(exit_time, str):
            exit_time = datetime.fromisoformat(exit_time)
        
        # Tìm chỉ số tương ứng
        estimated_index = min(int(entry_index + (exit_index - entry_index) * 
                               (exit_price - entry_price) / (price_data[exit_index] - entry_price)), 
                             exit_index)
        
        plt.scatter(estimated_index, exit_price, color='purple', s=80, marker='*', 
                  label=f'Thoát {exit_pct:.0f}%: {exit_price:.2f}')
    
    # Thêm tiêu đề và nhãn
    plt.title(title, fontsize=15)
    plt.xlabel('Chỉ số thời gian')
    plt.ylabel('Giá')
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    
    # Thêm thông tin thống kê
    profit_pct = result.get('profit_pct', 0)
    max_profit_pct = result.get('max_profit_pct', 0)
    efficiency = result.get('efficiency', 0)
    
    info_text = (
        f"Lợi nhuận: {profit_pct:.2f}%\n"
        f"Lợi nhuận cao nhất: {max_profit_pct:.2f}%\n"
        f"Hiệu quả: {efficiency:.2f}%\n"
        f"Trailing đã kích hoạt: {'Có' if trailing_activated else 'Không'}\n"
        f"Số lần thoát một phần: {len(partial_exits)}"
    )
    
    plt.figtext(0.02, 0.02, info_text, fontsize=12, 
               bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))
    
    # Lưu biểu đồ
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, filename))
    plt.close()
    
def run_demo():
    """Hàm chạy demo với các tình huống khác nhau"""
    # Tạo đối tượng Trailing Stop
    trailing_stop = EnhancedAdaptiveTrailingStop(CONFIG_FILE)
    
    # Các kịch bản thị trường để demo
    scenarios = [
        {'name': 'trending_long', 'side': 'LONG', 'trend': 'trending', 'volatility': 'medium', 
         'strategy': 'percentage', 'regime': 'trending'},
        {'name': 'trending_short', 'side': 'SHORT', 'trend': 'reversal', 'volatility': 'medium', 
         'strategy': 'percentage', 'regime': 'trending'},
        {'name': 'ranging_long', 'side': 'LONG', 'trend': 'ranging', 'volatility': 'low', 
         'strategy': 'percentage', 'regime': 'ranging'},
        {'name': 'volatile_long', 'side': 'LONG', 'trend': 'trending', 'volatility': 'high', 
         'strategy': 'percentage', 'regime': 'volatile'},
        {'name': 'step_trending_long', 'side': 'LONG', 'trend': 'trending', 'volatility': 'medium', 
         'strategy': 'step', 'regime': 'trending'},
    ]
    
    print("Enhanced Adaptive Trailing Stop Demo")
    print("-" * 50)
    
    for scenario in scenarios:
        name = scenario['name']
        side = scenario['side']
        trend = scenario['trend']
        volatility = scenario['volatility']
        strategy = scenario['strategy']
        regime = scenario['regime']
        
        print(f"\nRunning scenario: {name}")
        print(f"Side: {side}, Trend: {trend}, Volatility: {volatility}")
        print(f"Strategy: {strategy}, Market Regime: {regime}")
        
        # Tạo dữ liệu giá mô phỏng
        price_data = generate_price_data(trend, volatility)
        
        # Thực hiện backtest
        result = trailing_stop.backtest_trailing_stop(
            price_data[0], side, price_data, strategy, regime)
        
        # Thêm lịch sử stop để vẽ biểu đồ đẹp hơn
        # Trong thực tế, trailing_stop sẽ lưu lịch sử này
        result['stop_history'] = []
        
        # Tạo biểu đồ kết quả
        title = f"{strategy.capitalize()} Strategy - {regime.capitalize()} Market - {side}"
        filename = f"{strategy}_{regime}_{side.lower()}_demo.png"
        visualize_backtest_results(price_data, result, title, filename)
        
        # In kết quả
        print(f"Profit: {result['profit_pct']:.2f}%")
        print(f"Max Profit: {result['max_profit_pct']:.2f}%")
        print(f"Efficiency: {result['efficiency']:.2f}%")
        
    print("\nDemo hoàn thành. Biểu đồ kết quả được lưu trong thư mục:", CHARTS_DIR)

if __name__ == "__main__":
    run_demo()
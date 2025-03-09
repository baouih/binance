"""
Chạy kiểm tra VolumeProfileAnalyzer với dữ liệu mẫu
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

# Import module cần kiểm tra
from volume_profile_analyzer_extended import VolumeProfileAnalyzer

def create_sample_data(periods=200, volatility=0.02):
    """
    Tạo dữ liệu OHLCV mẫu để kiểm tra
    """
    # Tạo thời gian
    dates = [datetime.now() - timedelta(hours=i) for i in range(periods, 0, -1)]
    
    # Tạo giá theo mô hình random walk
    np.random.seed(42)  # Đảm bảo kết quả có thể tái tạo
    returns = np.random.normal(0, volatility, periods)
    
    # Tạo các vùng thị trường khác nhau
    # 0-50: Xu hướng tăng
    # 50-100: Tích lũy hẹp
    # 100-150: Tích lũy rộng
    # 150-200: Xu hướng giảm
    
    returns[0:50] = np.abs(returns[0:50]) * 1.2  # Xu hướng tăng
    returns[50:100] = returns[50:100] * 0.3  # Tích lũy hẹp
    returns[100:150] = returns[100:150] * 0.8  # Tích lũy rộng
    returns[150:200] = -np.abs(returns[150:200]) * 1.1  # Xu hướng giảm
    
    # Tạo giá
    price = 50000  # Giá ban đầu
    prices = [price]
    
    for ret in returns:
        price *= (1 + ret)
        prices.append(price)
    
    close_prices = prices[1:]  # Bỏ giá đầu tiên
    
    # Tạo OHLC từ giá đóng cửa
    open_prices = [close_prices[0]] + close_prices[:-1]
    high_prices = [c + abs(o-c) * np.random.uniform(1.0, 1.5) for o, c in zip(open_prices, close_prices)]
    low_prices = [c - abs(o-c) * np.random.uniform(1.0, 1.5) for o, c in zip(open_prices, close_prices)]
    
    # Tạo khối lượng - tăng cao ở vùng xu hướng và biến động
    volumes = np.random.normal(1000, 200, periods)
    volumes[0:50] *= 1.5  # Khối lượng cao ở xu hướng tăng
    volumes[150:200] *= 2.0  # Khối lượng cao ở xu hướng giảm
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=dates)
    
    return df

def main():
    """
    Hàm chính để chạy kiểm tra
    """
    print("Đang tạo dữ liệu mẫu...")
    df = create_sample_data()
    
    print("Đang kiểm tra VolumeProfileAnalyzer...")
    
    # Khởi tạo Volume Profile Analyzer
    vp_analyzer = VolumeProfileAnalyzer()
    
    # Tính Volume Profile
    print("1. Kiểm tra calculate_volume_profile...")
    profile = vp_analyzer.calculate_volume_profile(df, "BTCUSDT", "session")
    
    print(f"- POC: {profile.get('poc')}")
    print(f"- Value Area: {profile.get('value_area', {})}")
    print(f"- Volume Nodes: {len(profile.get('volume_nodes', []))}")
    
    # Tìm vùng hỗ trợ/kháng cự
    print("\n2. Kiểm tra identify_support_resistance...")
    sr_zones = vp_analyzer.identify_support_resistance(df, "BTCUSDT")
    
    print(f"- Support Levels: {len(sr_zones.get('support_levels', []))}")
    print(f"- Resistance Levels: {len(sr_zones.get('resistance_levels', []))}")
    
    # Phân tích vùng giao dịch
    print("\n3. Kiểm tra analyze_trading_range...")
    trading_range = vp_analyzer.analyze_trading_range(df, "BTCUSDT")
    
    print(f"- Position: {trading_range.get('position', 'unknown')}")
    print(f"- Nearest Support: {trading_range.get('nearest_support')}")
    print(f"- Nearest Resistance: {trading_range.get('nearest_resistance')}")
    print(f"- Breakout Potential Up: {trading_range.get('breakout_potential', {}).get('up', False)}")
    print(f"- Breakout Potential Down: {trading_range.get('breakout_potential', {}).get('down', False)}")
    
    # Tính VWAP
    print("\n4. Kiểm tra identify_vwap_zones...")
    vwap_zones = vp_analyzer.identify_vwap_zones(df, period='day')
    
    print(f"- VWAP: {vwap_zones.get('vwap')}")
    print(f"- VWAP Upper Band (1SD): {vwap_zones.get('bands', {}).get('upper_1sd')}")
    print(f"- VWAP Lower Band (1SD): {vwap_zones.get('bands', {}).get('lower_1sd')}")
    
    # Tạo biểu đồ
    print("\n5. Tạo biểu đồ...")
    chart_path = vp_analyzer.visualize_volume_profile(df, lookback_periods=100)
    print(f"- Volume Profile Chart: {chart_path}")
    
    vwap_chart = vp_analyzer.visualize_vwap_zones(df)
    print(f"- VWAP Chart: {vwap_chart}")
    
    print("\nKiểm tra hoàn tất!")

if __name__ == "__main__":
    main()
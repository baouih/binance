#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script để kiểm tra chức năng custom_path trong volume_profile_analyzer_extended.py
"""

import os
import pandas as pd
from datetime import datetime
from volume_profile_analyzer_extended import VolumeProfileAnalyzer

def load_test_data(symbol="BTCUSDT"):
    """Tải dữ liệu kiểm tra từ file csv."""
    data_path = f"data/{symbol}_1h.csv"
    if not os.path.exists(data_path):
        print(f"Không tìm thấy file dữ liệu: {data_path}")
        return None
    
    data = pd.read_csv(data_path)
    # Chuyển đổi cột time thành datetime và đặt làm index
    if 'time' in data.columns:
        data['time'] = pd.to_datetime(data['time'], unit='ms')
        data.set_index('time', inplace=True)
    
    print(f"Đã tải {len(data)} bản ghi dữ liệu cho {symbol}")
    return data

def test_custom_path_functionality():
    """Kiểm tra chức năng custom_path."""
    # Tạo thư mục tùy chỉnh để lưu biểu đồ
    custom_dir = "test_charts/custom_output"
    os.makedirs(custom_dir, exist_ok=True)
    
    print(f"Đã tạo thư mục tùy chỉnh: {custom_dir}")
    
    # Tải dữ liệu kiểm tra
    data = load_test_data("BTCUSDT")
    if data is None:
        return
    
    # Khởi tạo VolumeProfileAnalyzer
    analyzer = VolumeProfileAnalyzer()
    
    # Test chức năng visualize_volume_profile với custom_path
    vp_path = analyzer.visualize_volume_profile(
        df=data, 
        lookback_periods=100,
        custom_path=custom_dir
    )
    
    # Test chức năng visualize_vwap_zones với custom_path
    vwap_path = analyzer.visualize_vwap_zones(
        df=data,
        symbol="BTCUSDT", 
        period="day",
        custom_path=custom_dir
    )
    
    print("\nKết quả kiểm tra:")
    print(f"- Đường dẫn biểu đồ volume profile: {vp_path}")
    print(f"- Đường dẫn biểu đồ VWAP: {vwap_path}")
    
    # Kiểm tra xem các file đã được tạo ra chưa
    if os.path.exists(vp_path):
        print(f"✅ File biểu đồ volume profile đã được tạo thành công")
    else:
        print(f"❌ Không tạo được file biểu đồ volume profile")
        
    if os.path.exists(vwap_path):
        print(f"✅ File biểu đồ VWAP đã được tạo thành công")
    else:
        print(f"❌ Không tạo được file biểu đồ VWAP")

if __name__ == "__main__":
    print("Bắt đầu kiểm tra chức năng custom_path...")
    test_custom_path_functionality()
    print("Hoàn thành kiểm tra!")
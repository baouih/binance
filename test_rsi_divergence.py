#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script thử nghiệm cho phân tích RSI Divergence và tích hợp với Sideways Market Optimizer
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
import os
import logging
from datetime import datetime

# Import các module đã phát triển
from rsi_divergence_detector import RSIDivergenceDetector
from sideways_market_optimizer import SidewaysMarketOptimizer

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_divergence_detection():
    """
    Thử nghiệm phát hiện RSI Divergence độc lập
    """
    print("\n=== Thử Nghiệm Phát Hiện RSI Divergence ===")
    
    # Tải dữ liệu
    try:
        btc = yf.download("BTC-USD", period="3mo", interval="1d")
        eth = yf.download("ETH-USD", period="3mo", interval="1d")
        
        # Đổi tên cột
        for df in [btc, eth]:
            df.columns = [c.lower() for c in df.columns]
            
        # Khởi tạo detector
        detector = RSIDivergenceDetector()
        
        # Phân tích Bitcoin
        print("\n== Bitcoin ==")
        
        # Kiểm tra bullish divergence
        bullish = detector.detect_divergence(btc, is_bullish=True)
        print(f"Bullish Divergence: {bullish['detected']} (Độ tin cậy: {bullish['confidence']:.2f})")
        
        if bullish["detected"]:
            chart_path = detector.visualize_divergence(btc, bullish, "BTC-USD")
            print(f"Đã lưu biểu đồ tại: {chart_path}")
        
        # Kiểm tra bearish divergence
        bearish = detector.detect_divergence(btc, is_bullish=False)
        print(f"Bearish Divergence: {bearish['detected']} (Độ tin cậy: {bearish['confidence']:.2f})")
        
        if bearish["detected"]:
            chart_path = detector.visualize_divergence(btc, bearish, "BTC-USD")
            print(f"Đã lưu biểu đồ tại: {chart_path}")
        
        # Tín hiệu giao dịch từ divergence
        signal = detector.get_trading_signal(btc)
        print(f"Tín hiệu giao dịch: {signal['signal']} (Độ tin cậy: {signal['confidence']:.2f})")
        
        # Phân tích Ethereum
        print("\n== Ethereum ==")
        
        # Kiểm tra bullish divergence
        eth_bullish = detector.detect_divergence(eth, is_bullish=True)
        print(f"Bullish Divergence: {eth_bullish['detected']} (Độ tin cậy: {eth_bullish['confidence']:.2f})")
        
        if eth_bullish["detected"]:
            chart_path = detector.visualize_divergence(eth, eth_bullish, "ETH-USD")
            print(f"Đã lưu biểu đồ tại: {chart_path}")
        
        # Kiểm tra bearish divergence
        eth_bearish = detector.detect_divergence(eth, is_bullish=False)
        print(f"Bearish Divergence: {eth_bearish['detected']} (Độ tin cậy: {eth_bearish['confidence']:.2f})")
        
        if eth_bearish["detected"]:
            chart_path = detector.visualize_divergence(eth, eth_bearish, "ETH-USD")
            print(f"Đã lưu biểu đồ tại: {chart_path}")
        
        # Tín hiệu giao dịch từ divergence
        eth_signal = detector.get_trading_signal(eth)
        print(f"Tín hiệu giao dịch: {eth_signal['signal']} (Độ tin cậy: {eth_signal['confidence']:.2f})")
        
    except Exception as e:
        logger.error(f"Lỗi khi thử nghiệm detector: {str(e)}")

def test_integrated_analysis():
    """
    Thử nghiệm phân tích tích hợp Sideways Market và RSI Divergence
    """
    print("\n=== Thử Nghiệm Phân Tích Tích Hợp ===")
    
    try:
        # Tải dữ liệu
        btc = yf.download("BTC-USD", period="3mo", interval="1d")
        
        # Đổi tên cột
        btc.columns = [c.lower() for c in btc.columns]
        
        # Khởi tạo optimizer
        optimizer = SidewaysMarketOptimizer()
        
        # Phát hiện thị trường đi ngang
        is_sideways = optimizer.detect_sideways_market(btc)
        print(f"Thị trường đi ngang: {is_sideways} (Score: {optimizer.sideways_score:.2f})")
        
        # Phát hiện divergence
        divergence_result = optimizer.detect_rsi_divergence(btc)
        print("\n== Kết quả phát hiện RSI Divergence ==")
        print(f"Tín hiệu: {divergence_result['signal']}")
        print(f"Loại divergence: {divergence_result['divergence_type']}")
        print(f"Độ tin cậy: {divergence_result['confidence']:.2f}")
        print(f"Giá hiện tại: ${divergence_result['price']:.2f}")
        
        if divergence_result['chart_path']:
            print(f"Biểu đồ divergence: {divergence_result['chart_path']}")
        
        # Phân tích đầy đủ thị trường
        market_analysis = optimizer.analyze_market_with_divergence(btc, "BTC-USD")
        
        print("\n== Phân tích thị trường tích hợp ==")
        print(f"Thị trường đi ngang: {market_analysis['is_sideways_market']} (Score: {market_analysis['sideways_score']:.2f})")
        print(f"Bullish Divergence: {market_analysis['divergence']['bullish']['detected']} (Độ tin cậy: {market_analysis['divergence']['bullish']['confidence']:.2f})")
        print(f"Bearish Divergence: {market_analysis['divergence']['bearish']['detected']} (Độ tin cậy: {market_analysis['divergence']['bearish']['confidence']:.2f})")
        print(f"Tín hiệu divergence: {market_analysis['divergence']['signal']} (Độ tin cậy: {market_analysis['divergence']['signal_confidence']:.2f})")
        
        print("\n== Chiến lược giao dịch ==")
        print(f"Kích thước vị thế: {market_analysis['position_sizing']['adjusted']:.2f}x (Giảm {market_analysis['position_sizing']['reduction_pct']:.1f}%)")
        print(f"Sử dụng mean reversion: {market_analysis['strategy']['use_mean_reversion']}")
        print(f"Dự đoán breakout: {market_analysis['strategy']['breakout_prediction']}")
        print(f"Tỷ lệ TP/SL: {market_analysis['strategy']['tp_sl_ratio']:.1f}:1")
        
        # Hiển thị mục tiêu giá nếu có
        if 'price_targets' in market_analysis:
            print("\n== Mục tiêu giá ==")
            print(f"Take Profit: ${market_analysis['price_targets']['tp_price']:.0f} (+{market_analysis['price_targets']['tp_distance_pct']:.1f}%)")
            print(f"Stop Loss: ${market_analysis['price_targets']['sl_price']:.0f} (-{market_analysis['price_targets']['sl_distance_pct']:.1f}%)")
        
        # Tạo báo cáo
        report = optimizer.generate_market_report(btc, "BTC-USD")
        print(f"\nĐã tạo báo cáo phân tích thị trường")
        
    except Exception as e:
        logger.error(f"Lỗi khi thử nghiệm phân tích tích hợp: {str(e)}")

if __name__ == "__main__":
    # Chạy thử nghiệm divergence
    test_divergence_detection()
    
    # Chạy thử nghiệm tích hợp
    test_integrated_analysis()
    
    print("\nHoàn thành thử nghiệm tích hợp RSI Divergence và Sideways Market Optimizer")